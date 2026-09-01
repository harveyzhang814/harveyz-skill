"""Unit tests for store_config.py — the shared knowledgeRoot resolver
copied identically into clip-url / learn-video / sync-xtimeline /
sync-ytchannel. Pure filesystem I/O against a fake config.json, never the
real ~/.hskill/config.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import store_config  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "store_config.py"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    # Distinct filename from tests/conftest.py's own HSKILL_CONFIG fixture
    # (also autouse, also under this same tmp_path) — sharing "config.json"
    # would make conftest's real file satisfy this file's "config missing"
    # checks.
    config_path = tmp_path / "store-config-under-test.json"
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return config_path


def _write(config_path: Path, **fields) -> None:
    config_path.write_text(json.dumps(fields), encoding="utf-8")


def test_get_root_raises_when_config_missing(isolated_config):
    with pytest.raises(FileNotFoundError):
        store_config.get_root()


def test_get_root_raises_when_knowledge_root_key_missing(isolated_config):
    _write(isolated_config, skillDir="/some/other/path")
    with pytest.raises(KeyError):
        store_config.get_root()


def test_get_root_reads_configured_value(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.get_root() == Path("/fake/knowledge")


def test_get_root_expands_tilde(isolated_config):
    _write(isolated_config, knowledgeRoot="~/Documents/knowledge")
    assert store_config.get_root() == Path.home() / "Documents" / "knowledge"


def test_articles_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.articles_dir() == Path("/fake/knowledge/articles")


def test_videos_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.videos_dir() == Path("/fake/knowledge/videos")


def test_feeds_dir(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    assert store_config.feeds_dir("tweets") == Path("/fake/knowledge/feeds/tweets")
    assert store_config.feeds_dir("youtube") == Path("/fake/knowledge/feeds/youtube")


def test_hskill_config_env_overrides_default_path(tmp_path, monkeypatch):
    other_path = tmp_path / "other-config.json"
    other_path.write_text(json.dumps({"knowledgeRoot": "/other/root"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_CONFIG", str(other_path))
    assert store_config.get_root() == Path("/other/root")


def test_cli_check_prints_ok_and_exits_zero_when_configured(isolated_config):
    _write(isolated_config, knowledgeRoot="/fake/knowledge")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        env={**os.environ, "HSKILL_CONFIG": str(isolated_config)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "OK: /fake/knowledge"


def test_cli_check_prints_missing_and_exits_one_when_config_absent(tmp_path):
    missing_path = tmp_path / "does-not-exist.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "check"],
        env={**os.environ, "HSKILL_CONFIG": str(missing_path)},
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 1
    assert result.stderr.strip().startswith("MISSING:")

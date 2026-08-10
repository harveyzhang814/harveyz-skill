"""Unit tests for dedup_check.py's meta.json-based dedup detection —
pure filesystem I/O against a fake config.json, never the real vault."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dedup_check import is_already_fetched  # noqa: E402
from vault_config import get_article_paths  # noqa: E402


@pytest.fixture(autouse=True)
def valid_vault_config(isolated_vault_config):
    vault_path = isolated_vault_config.parent / "vault"
    isolated_vault_config.write_text(json.dumps({"VAULT_PATH": str(vault_path)}), encoding="utf-8")


def test_returns_false_when_no_meta_json():
    assert is_already_fetched("https://example.com/article") is False


def test_returns_true_when_meta_json_matches_url():
    url = "https://example.com/article"
    meta_path = get_article_paths(url)["meta_path"]
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps({"source_url": url}), encoding="utf-8")
    assert is_already_fetched(url) is True


def test_returns_false_when_meta_json_source_url_differs():
    url = "https://example.com/article"
    meta_path = get_article_paths(url)["meta_path"]
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(
        json.dumps({"source_url": "https://example.com/other-article"}), encoding="utf-8"
    )
    assert is_already_fetched(url) is False


def test_returns_false_when_meta_json_is_malformed():
    url = "https://example.com/article"
    meta_path = get_article_paths(url)["meta_path"]
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text("not valid json{{{", encoding="utf-8")
    assert is_already_fetched(url) is False


def test_main_prints_meta_path_when_already_fetched(monkeypatch, capsys):
    url = "https://example.com/article"
    meta_path = get_article_paths(url)["meta_path"]
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps({"source_url": url}), encoding="utf-8")
    monkeypatch.setenv("CHECK_URL", url)

    from dedup_check import main
    main()

    captured = capsys.readouterr()
    assert "ALREADY_FETCHED" in captured.out
    assert f"META_PATH: {meta_path}" in captured.out

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json
import os
import subprocess

import pytest

import config

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"


def test_get_config_raises_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(tmp_path / "nonexistent.json"))
    with pytest.raises(FileNotFoundError, match="配置文件不存在"):
        config.get_config()


def test_get_data_dir_returns_path(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"DATA_DIR": "/my/data"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(cfg))
    assert config.get_data_dir() == Path("/my/data")


def test_get_data_dir_expands_tilde(tmp_path, monkeypatch):
    """DATA_DIR is typed by a human, so "~/Vault/YouTube" has to work."""
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"DATA_DIR": "~/Vault/YouTube"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(cfg))
    assert config.get_data_dir() == Path.home() / "Vault" / "YouTube"


def test_get_data_dir_raises_when_key_missing(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(cfg))
    with pytest.raises(KeyError, match="DATA_DIR"):
        config.get_data_dir()


def test_set_config_creates_file_and_parent_dir(tmp_path, monkeypatch):
    cfg = tmp_path / "sub" / "config.json"
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(cfg))
    config.set_config("DATA_DIR", "/d")
    assert json.loads(cfg.read_text(encoding="utf-8"))["DATA_DIR"] == "/d"


def test_set_config_preserves_existing_keys(tmp_path, monkeypatch):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"OTHER_KEY": "x"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(cfg))
    config.set_config("DATA_DIR", "/d")
    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert data["OTHER_KEY"] == "x"
    assert data["DATA_DIR"] == "/d"


def test_config_path_env_override_applies_in_subprocess(tmp_path):
    cfg = tmp_path / "custom.json"
    cfg.write_text(json.dumps({"DATA_DIR": "/env/data"}), encoding="utf-8")
    result = subprocess.run(
        ["python3", "-c", "import config; print(config.get_data_dir())"],
        env={**os.environ, "HSKILL_SYNC_YTCHANNEL_CONFIG": str(cfg)},
        capture_output=True,
        text=True,
        cwd=str(_SCRIPTS_DIR),
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "/env/data"

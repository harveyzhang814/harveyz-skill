import json

import pytest

from roster import SCHEMA_VERSION, config


def test_schema_version_is_one():
    assert SCHEMA_VERSION == 1


def test_get_data_dir_reads_configured_path(data_dir):
    assert config.get_data_dir() == data_dir


def test_get_config_path_follows_env_var_changed_after_import(tmp_path, monkeypatch):
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"DATA_DIR": "/tmp/elsewhere"}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(other))
    assert config.get_config_path() == other


def test_missing_config_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(tmp_path / "nope.json"))
    with pytest.raises(FileNotFoundError):
        config.get_data_dir()


def test_config_without_data_dir_raises(tmp_path, monkeypatch):
    cfg = tmp_path / "empty.json"
    cfg.write_text("{}", encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    with pytest.raises(KeyError):
        config.get_data_dir()


def test_set_config_creates_parent_dirs(tmp_path, monkeypatch):
    cfg = tmp_path / "deep" / "nested" / "config.json"
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    config.set_config("DATA_DIR", "/tmp/x")
    assert json.loads(cfg.read_text(encoding="utf-8"))["DATA_DIR"] == "/tmp/x"

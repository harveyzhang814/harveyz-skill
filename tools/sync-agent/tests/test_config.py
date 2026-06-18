import json
from pathlib import Path
import pytest
from sync_agent.config import (
    Config, State,
    load_config, save_config,
    load_state, save_state,
    default_base_dir,
)


@pytest.fixture
def base(tmp_path):
    return tmp_path


def test_load_config_missing_returns_empty(base):
    cfg = load_config(base)
    assert cfg.folders == []
    assert cfg.devices == []


def test_save_and_load_config(base):
    cfg = Config(
        folders=[{"id": "f1", "path": "~/docs", "label": "Docs"}],
        devices=[{"id": "ABC-DEF", "name": "laptop"}],
    )
    save_config(cfg, base)
    loaded = load_config(base)
    assert loaded.folders == cfg.folders
    assert loaded.devices == cfg.devices


def test_config_file_created_at_expected_path(base):
    cfg = Config(folders=[], devices=[])
    save_config(cfg, base)
    assert (base / "config.json").exists()


def test_load_state_missing_raises(base):
    with pytest.raises(FileNotFoundError):
        load_state(base)


def test_save_and_load_state(base):
    state = State(api_key="secret123", device_id="XX-YY", api_url="http://127.0.0.1:8384")
    save_state(state, base)
    loaded = load_state(base)
    assert loaded.api_key == "secret123"
    assert loaded.device_id == "XX-YY"
    assert loaded.api_url == "http://127.0.0.1:8384"


def test_default_base_dir_is_under_home():
    d = default_base_dir()
    assert d == Path.home() / ".hskill" / "sync-agent"

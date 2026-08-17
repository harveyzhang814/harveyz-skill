"""Shared test isolation for sync-xtimeline: points every test at a fake
config.json (via HSKILL_SYNC_XTIMELINE_CONFIG) with DATA_DIR under tmp_path,
so no test can read or write the real ~/.hskill/sync-xtimeline/ directory."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import config


def write_config(config_path: Path, data_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"DATA_DIR": str(data_dir)}), encoding="utf-8")


def set_config_path(monkeypatch, config_path: Path) -> None:
    """Point in-process config lookups (config.CONFIG_PATH) and any spawned
    subprocess (HSKILL_SYNC_XTIMELINE_CONFIG) at config_path. config.CONFIG_PATH
    is a module-level constant read once at import time, so the env var alone
    only takes effect for freshly-spawned subprocesses, not in-process calls."""
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)
    monkeypatch.setenv("HSKILL_SYNC_XTIMELINE_CONFIG", str(config_path))


@pytest.fixture(autouse=True)
def isolated_sync_xtimeline_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "sync-xtimeline-data"
    config_path = tmp_path / "sync-xtimeline-config.json"
    write_config(config_path, data_dir)
    set_config_path(monkeypatch, config_path)
    return data_dir

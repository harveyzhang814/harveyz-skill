"""Shared test isolation for sync-ytchannel: points every test at a config
file under tmp_path (via HSKILL_SYNC_YTCHANNEL_CONFIG) whose DATA_DIR also
sits under tmp_path, so no test can read or write the real config or the
user's actual data directory."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


def write_config(config_path: Path, data_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"DATA_DIR": str(data_dir)}), encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """config.get_config_path() reads the env var on every call (not at import
    time), so setting it here covers both in-process calls and subprocesses."""
    data_dir = tmp_path / "sync-ytchannel-data"
    config_path = tmp_path / "sync-ytchannel-config.json"
    write_config(config_path, data_dir)
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_CONFIG", str(config_path))
    return data_dir

"""Shared test isolation for sync-ytchannel: points every test at a data
directory under tmp_path (via HSKILL_SYNC_YTCHANNEL_DIR), so no test can read
or write the real ~/.hskill/sync-ytchannel/ directory."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    """config.get_data_dir() reads the env var on every call (not at import
    time), so setting it here covers both in-process calls and subprocesses."""
    data_dir = tmp_path / "sync-ytchannel-data"
    monkeypatch.setenv("HSKILL_SYNC_YTCHANNEL_DIR", str(data_dir))
    return data_dir

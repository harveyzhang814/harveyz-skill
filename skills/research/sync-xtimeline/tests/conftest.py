"""Shared test isolation for sync-xtimeline: points every test at a fake
HSKILL_SYNC_XTIMELINE_DATA_DIR under tmp_path, so no test can read or write the
real ~/.hskill/sync-xtimeline/ directory."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_sync_xtimeline_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "sync-xtimeline-data"
    monkeypatch.setenv("HSKILL_SYNC_XTIMELINE_DATA_DIR", str(data_dir))
    return data_dir

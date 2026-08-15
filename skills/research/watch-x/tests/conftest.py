"""Shared test isolation for watch-x: points every test at a fake
HSKILL_WATCH_X_DATA_DIR under tmp_path, so no test can read or write the
real ~/.hskill/watch-x/ directory."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_watch_x_data_dir(tmp_path, monkeypatch):
    data_dir = tmp_path / "watch-x-data"
    monkeypatch.setenv("HSKILL_WATCH_X_DATA_DIR", str(data_dir))
    return data_dir

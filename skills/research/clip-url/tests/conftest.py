"""Shared test isolation for clip-url: points store_config at a fake
config.json under tmp_path for every test in this directory (autouse),
so a test file that forgets to declare its own isolation still can't read
or write the real ~/.hskill/config.json. Does not write config content —
tests that need a valid knowledgeRoot write it themselves (building on
isolated_store_config); tests exercising a missing/invalid config leave
it absent."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_store_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return config_path

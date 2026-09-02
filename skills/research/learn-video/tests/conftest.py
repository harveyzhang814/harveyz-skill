"""Shared test isolation for learn-video: points store_config at a fake
config.json under tmp_path for every test in this directory (autouse),
so a test file that forgets to declare its own isolation still can't
read or write the real ~/.hskill/config.json."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def isolated_store_config(tmp_path, monkeypatch) -> Path:
    config_path = tmp_path / "config.json"
    root = tmp_path / "knowledge"
    config_path.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return root

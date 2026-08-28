"""Test isolation for roster:每个测试拿到 tmp_path 下的独立配置与数据目录，
绝不触碰真实的 ~/.hskill/roster/。config.get_config_path() 每次调用都读环境
变量（不在 import 时固化），所以设一次 env 同时覆盖进程内调用和子进程。"""
import json
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "roster-data"
    cfg = tmp_path / "roster-config.json"
    cfg.write_text(json.dumps({"DATA_DIR": str(d)}), encoding="utf-8")
    monkeypatch.setenv("HSKILL_ROSTER_CONFIG", str(cfg))
    return d

"""sync-xtimeline 的测试隔离：config.get_data_dir() 通过 store_config 向
统一存储根要 tweets 渠道目录（<ROOT>/feeds/tweets）。用 HSKILL_CONFIG 指向
一份临时 config.json 完成隔离——进程内、子进程两种场景都靠这一个环境变量，
不需要再对 roster_client 打 monkeypatch（config.py 不再经它取路径）。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

HSKILL_CONFIG_ENV = "HSKILL_CONFIG"


def write_config(config_path: Path, root: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"knowledgeRoot": str(root)}), encoding="utf-8")


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch) -> Path:
    config_path = tmp_path / "config.json"
    root = tmp_path / "knowledge-root"
    write_config(config_path, root)
    monkeypatch.setenv(HSKILL_CONFIG_ENV, str(config_path))
    return root / "feeds" / "tweets"

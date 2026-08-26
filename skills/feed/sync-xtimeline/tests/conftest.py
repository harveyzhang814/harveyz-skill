"""sync-xtimeline 的测试隔离。名册化之后本 skill 不再持有自己的 DATA_DIR
（改为向 roster 要），隔离点因此分成两处：

- 进程内：patch roster_client.data_dir。只需要这一个点，因为
  config.get_data_dir() 在调用时才向它取值，所以那些在 import 时就绑定了
  get_data_dir 的模块也一并跟着走。
- 跨进程（subprocess 起脚本）：patch 不过去，改设 HSKILL_ROSTER_CONFIG
  指向一份真的 roster 配置，由真的 roster CLI 读。那份配置的形状跟旧的
  sync-xtimeline config.json 一模一样（只有一个 DATA_DIR 键）。
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import roster_client

ROSTER_CONFIG_ENV = "HSKILL_ROSTER_CONFIG"


def write_config(config_path: Path, data_dir: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"DATA_DIR": str(data_dir)}), encoding="utf-8")


def set_config_path(monkeypatch, config_path: Path) -> None:
    """进程内版本：让 roster_client.data_dir 返回这份配置指向的目录，
    同时设好环境变量，供这个测试再 spawn 子进程时使用。"""
    monkeypatch.setenv(ROSTER_CONFIG_ENV, str(config_path))
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(roster_client, "data_dir", lambda: Path(cfg["DATA_DIR"]))


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch) -> Path:
    data_dir = tmp_path / "sync-xtimeline-data"
    monkeypatch.setattr(roster_client, "data_dir", lambda: data_dir)
    return data_dir

"""roster 的数据目录位置。

路径由用户提供，不给默认值：名册里的画像是要跟用户笔记同等对待的资产，
猜一个目录会把它悄悄埋在别处。配置文件自身的位置是固定的
（~/.hskill/roster/config.json），只有它指向的数据目录可配。

HSKILL_ROSTER_CONFIG 覆盖配置路径，且在每次调用时读取——测试要能在
进程内重定向，不能只对子进程生效。
"""
import json
import os
from pathlib import Path


def get_config_path() -> Path:
    override = os.environ.get("HSKILL_ROSTER_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".hskill" / "roster" / "config.json"


def get_config() -> dict:
    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"roster 配置文件不存在：{path}\n首次使用请先完成初始化，设置 DATA_DIR。"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def get_data_dir() -> Path:
    cfg = get_config()
    if "DATA_DIR" not in cfg:
        raise KeyError("config.json 缺少 DATA_DIR，请重新初始化。")
    return Path(cfg["DATA_DIR"]).expanduser()


def set_config(key: str, value: str) -> None:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if path.exists():
        cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg[key] = value
    path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

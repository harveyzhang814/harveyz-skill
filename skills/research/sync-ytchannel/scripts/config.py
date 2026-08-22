#!/usr/bin/env python3
"""Where sync-ytchannel keeps its state (watchlist.json + digests/).

The location is user-supplied, not defaulted: the update logs are meant to
live wherever the user keeps their notes, so guessing a directory would
quietly bury them somewhere else. `DATA_DIR` is read from
~/.hskill/sync-ytchannel/config.json — the config file's own location is
fixed, only the data it points at is configurable.

HSKILL_SYNC_YTCHANNEL_CONFIG overrides the config path, and is read on every
call so tests can redirect it in-process as well as in subprocesses.
"""
import json
import os
from pathlib import Path


def get_config_path() -> Path:
    override = os.environ.get("HSKILL_SYNC_YTCHANNEL_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".hskill" / "sync-ytchannel" / "config.json"


def get_config() -> dict:
    path = get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"sync-ytchannel 配置文件不存在：{path}\n"
            "首次使用请先完成初始化，设置 DATA_DIR。"
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

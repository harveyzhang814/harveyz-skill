#!/usr/bin/env python3
"""
Shared config reader/writer for sync-xtimeline skill.
Config file: ~/.hskill/sync-xtimeline/config.json
"""
import json
import os
from pathlib import Path

_env_cfg = os.environ.get('HSKILL_SYNC_XTIMELINE_CONFIG')
CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path.home() / '.hskill' / 'sync-xtimeline' / 'config.json'


def get_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"sync-xtimeline 配置文件不存在：{CONFIG_PATH}\n"
            "首次使用请先完成初始化，设置 DATA_DIR。"
        )
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def get_data_dir() -> str:
    cfg = get_config()
    if 'DATA_DIR' not in cfg:
        raise KeyError("config.json 缺少 DATA_DIR，请重新初始化。")
    return cfg['DATA_DIR']


def set_config(key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    cfg[key] = value
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8'
    )

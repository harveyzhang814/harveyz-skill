#!/usr/bin/env python3
"""
Shared config reader/writer for url-extract skill.
Config file: ~/.hskill/url-extract/config.json
"""
import json
from pathlib import Path

CONFIG_PATH = Path.home() / '.hskill' / 'url-extract' / 'config.json'


def get_config() -> dict:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"url-extract 配置文件不存在：{CONFIG_PATH}\n"
            "首次使用请运行 extract-url skill，完成初始化流程。"
        )
    return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))


def get_vault_path() -> str:
    cfg = get_config()
    if 'VAULT_PATH' not in cfg:
        raise KeyError("config.json 缺少 VAULT_PATH，请重新初始化。")
    return cfg['VAULT_PATH']


def get_chrome_profile() -> str:
    cfg = get_config()
    if 'CHROME_PROFILE' not in cfg:
        raise KeyError("config.json 缺少 CHROME_PROFILE，请重新初始化。")
    return cfg['CHROME_PROFILE']


def set_config(key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    cfg[key] = value
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8'
    )

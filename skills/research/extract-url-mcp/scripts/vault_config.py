#!/usr/bin/env python3
"""Shared-vault path resolution for extract-url-mcp: reads the same
~/.hskill/url-extract/config.json that extract-url writes, so both
skills' dedup index (meta.json) and article layout live in one place.

Written from scratch — does not import extract-url's config.py.
"""
import hashlib
import json
import os
from pathlib import Path


def _config_path() -> Path:
    env_cfg = os.environ.get("HSKILL_EXTRACT_URL_CONFIG")
    return Path(env_cfg) if env_cfg else Path.home() / ".hskill" / "url-extract" / "config.json"


def get_vault_path() -> str:
    config_path = _config_path()
    if not config_path.exists():
        raise FileNotFoundError(
            f"共享配置文件不存在：{config_path}\n"
            "请先运行 extract-url skill 完成初始化（配置 VAULT_PATH 和固定词表）。"
        )
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    if "VAULT_PATH" not in cfg:
        raise KeyError(f"{config_path} 缺少 VAULT_PATH，请重新运行 extract-url 完成初始化。")
    return cfg["VAULT_PATH"]


def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


def get_article_paths(url: str) -> dict:
    vault_path = get_vault_path()
    url_hash = get_url_hash(url)
    article_dir = Path(vault_path) / url_hash
    return {
        "article_dir": article_dir,
        "origin_path": article_dir / "Origin" / "article.md",
        "translation_path": article_dir / "Translation" / "article.md",
        "meta_path": article_dir / "meta.json",
    }

#!/usr/bin/env python3
"""
Shared config reader/writer for url-extract skill.
Config file: ~/.hskill/url-extract/config.json
"""
import json, os, hashlib
from pathlib import Path

_env_cfg = os.environ.get('HSKILL_EXTRACT_URL_CONFIG')
CONFIG_PATH = Path(_env_cfg) if _env_cfg else Path.home() / '.hskill' / 'url-extract' / 'config.json'


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


def get_url_hash(source_url: str) -> str:
    return hashlib.md5(source_url.encode()).hexdigest()[:8]


def get_article_paths(source_url: str, origin_title: str) -> dict:
    """文章专属文件夹路径：VAULT_PATH/<url_hash>/{Origin,Translation,Image}/"""
    import sys as _sys
    references_dir = str(Path(__file__).parent.parent / 'references')
    if references_dir not in _sys.path:
        _sys.path.insert(0, references_dir)
    from article_utils import sanitize_filename

    vault_path = get_vault_path()
    url_hash = get_url_hash(source_url)
    article_dir = os.path.join(vault_path, url_hash)
    filename = sanitize_filename(origin_title) + '.md'
    origin_dir = os.path.join(article_dir, 'Origin')
    translation_dir = os.path.join(article_dir, 'Translation')
    image_dir = os.path.join(article_dir, 'Image')
    return {
        'url_hash': url_hash,
        'article_dir': article_dir,
        'origin_dir': origin_dir,
        'translation_dir': translation_dir,
        'image_dir': image_dir,
        'origin_path': os.path.join(origin_dir, filename),
        'translation_path': os.path.join(translation_dir, filename),
    }


def set_config(key: str, value: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if CONFIG_PATH.exists():
        cfg = json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
    cfg[key] = value
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8'
    )

#!/usr/bin/env python3
"""Article path resolution for clip-url. Delegates the storage root to
store_config.articles_dir() — VAULT_PATH (the old
~/.hskill/url-extract/config.json field) has retired; that config file
now only carries fixed_tags.txt's directory. See
docs/superpowers/specs/2026-09-01-unified-store-design.md §5.1.
"""
import hashlib
from pathlib import Path

import store_config


def get_vault_path() -> str:
    return str(store_config.articles_dir())


def get_url_hash(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


def get_article_paths(url: str) -> dict:
    """origin_path/translation_path aren't included here — their filename
    is derived from the article's title (sanitize_filename(title) + ".md",
    matching extract-url's convention), which isn't known until after
    fetch_article extracts it. Callers get the real origin_path from
    fetch_article's response, and derive translation_path from it (same
    filename, Origin -> Translation)."""
    vault_path = get_vault_path()
    url_hash = get_url_hash(url)
    article_dir = Path(vault_path) / url_hash
    return {
        "article_dir": article_dir,
        "meta_path": article_dir / "meta.json",
    }

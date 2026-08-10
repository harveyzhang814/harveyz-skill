#!/usr/bin/env python3
"""Check URL dedup via meta.json existence — reimplemented from
extract-url's scripts/dedup_check.py against the same shared
~/.hskill/url-extract/config.json / VAULT_PATH.

Parameter via env var to avoid shell injection:
  CHECK_URL - URL to check
Prints: ALREADY_FETCHED or OK
"""
import json
import os

import vault_config


def is_already_fetched(url: str) -> bool:
    meta_path = vault_config.get_article_paths(url)["meta_path"]
    if not meta_path.exists():
        return False
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    return meta.get("source_url") == url


def main():
    url = os.environ["CHECK_URL"]
    print("ALREADY_FETCHED" if is_already_fetched(url) else "OK")


if __name__ == "__main__":
    main()

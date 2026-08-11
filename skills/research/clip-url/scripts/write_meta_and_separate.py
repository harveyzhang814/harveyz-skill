#!/usr/bin/env python3
"""CLI wrapper for Subagent 2: writes <hash8>/meta.json and moves any
candidate_tags entries matching the shared fixed vocabulary into tags.
Reimplemented from extract-url's scripts/validate_article.py, minus
the frontmatter-repair step (not needed — clip-url's frontmatter
is already generated cleanly server-side).

Parameters via environment variables:
  ARTICLE_URL      - source URL
  ARTICLE_PATH     - path to the translated article .md file
  FIXED_TAGS_PATH  - (optional) override path for fixed_tags.txt
Reads VAULT_PATH via vault_config (shared ~/.hskill/url-extract/config.json,
or HSKILL_EXTRACT_URL_CONFIG override) to locate <hash8>/meta.json.
"""
import os
from pathlib import Path

import article_meta
import vault_config


def run() -> Path:
    url = os.environ["ARTICLE_URL"]
    article_path = os.environ["ARTICLE_PATH"]
    fixed_tags_path = os.environ.get(
        "FIXED_TAGS_PATH", str(Path.home() / ".hskill" / "url-extract" / "fixed_tags.txt")
    )
    meta_path = vault_config.get_article_paths(url)["meta_path"]
    expected_article_dir = Path(article_path).resolve().parent.parent
    if meta_path.parent.resolve() != expected_article_dir:
        raise RuntimeError(
            f"ARTICLE_URL doesn't hash to the directory containing ARTICLE_PATH "
            f"({meta_path.parent} != {expected_article_dir}) — ARTICLE_URL must be "
            f"byte-identical to the URL used to fetch this article, or dedup "
            f"silently breaks and a stray meta.json gets written into the vault."
        )
    article_meta.enforce_tag_separation(article_path, fixed_tags_path)
    article_meta.write_meta_json(url, meta_path, article_path)
    return meta_path


def main():
    meta_path = run()
    print(f"META_PATH: {meta_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Stage 3 fetch script for clip-url: calls browser-fetch's `article`
subcommand (site-aware extraction: generic/wechat/arxiv/xcom), which
already assembles the Markdown Origin file itself (--format defaults
to "path") and returns its path — this script's only remaining job is
resolving the shared-vault article directory (via vault_config) and
printing the result.

Written from scratch — does not import or reuse extract-url's scripts.

NOTE ON MODULE NAME: the `mcp_` prefix is historical — this script was
originally an MCP client (see git history). It now shells out to the
browser-fetch CLI via browser_fetch_cli.call() instead of speaking MCP.
The prefix is kept because renaming would touch SKILL.md, references/
subagent prompt templates, and this file's own test module — out of
scope for this internal-implementation-only migration.

Usage: python3 mcp_fetch_client.py <url> [chrome_profile]
Stdout on success: eight lines — "ORIGIN_PATH: <path>", "TITLE: <title>",
"SITE: <site>", "BLOCK_COUNT: <n>", "CHAR_COUNT: <n>",
"CODE_BLOCK_COUNT: <n>", "IMAGE_COUNT: <n>", "CONTENT_THIN: <bool>",
"THIN_RETRY_USED: <bool>".
"""
import sys
from pathlib import Path
from typing import Optional

import browser_fetch_cli
import vault_config


def fetch_and_report(url: str, chrome_profile: Optional[str] = None) -> dict:
    article_dir = vault_config.get_article_paths(url)["article_dir"]
    args = ["article", url, "--out", str(article_dir), "--format", "path"]
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    payload = browser_fetch_cli.call(*args)
    payload["origin_path"] = Path(payload["origin_path"])
    return payload


def fetch_and_save(url: str, chrome_profile: Optional[str] = None) -> Path:
    return fetch_and_report(url, chrome_profile)["origin_path"]


def main():
    if len(sys.argv) < 2:
        print("Usage: mcp_fetch_client.py <url> [chrome_profile]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    chrome_profile = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    try:
        payload = fetch_and_report(url, chrome_profile)
    except Exception as e:
        # 只打裸消息，不加 "ERROR:" 前缀——subagent1-fetch-prompt.md 自己会加
        print(str(e), file=sys.stderr)
        sys.exit(1)
    print(f"ORIGIN_PATH: {payload['origin_path']}")
    print(f"TITLE: {payload['title']}")
    print(f"SITE: {payload['site']}")
    print(f"BLOCK_COUNT: {payload['block_count']}")
    print(f"CHAR_COUNT: {payload['char_count']}")
    print(f"CODE_BLOCK_COUNT: {payload['code_block_count']}")
    print(f"IMAGE_COUNT: {payload['image_count']}")
    print(f"CONTENT_THIN: {payload['content_thin']}")
    print(f"THIN_RETRY_USED: {payload['thin_retry_used']}")


if __name__ == "__main__":
    main()

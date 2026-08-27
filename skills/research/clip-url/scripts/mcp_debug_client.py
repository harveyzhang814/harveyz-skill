#!/usr/bin/env python3
"""Debug client for clip-url's self-optimization subagent: thin wrappers
around browser-fetch's `page` and `eval` subcommands, used to iterate
candidate extraction logic against a real page before solidifying a fix
into browser-fetch/browser_fetch/extractors.py.

Written from scratch, sibling to mcp_fetch_client.py — does not import or
reuse extract-url's scripts.

NOTE ON MODULE NAME: the `mcp_` prefix is historical — this script was
originally an MCP client (see git history). It now shells out to the
browser-fetch CLI via browser_fetch_cli.call() instead of speaking MCP.
The prefix is kept because renaming would touch SKILL.md, references/
subagent prompt templates, and this file's own test module — out of
scope for this internal-implementation-only migration.
"""
import tempfile
from pathlib import Path
from typing import Optional

import browser_fetch_cli


def call_fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    args = ["page", url]
    if use_auth:
        args.append("--auth")
    if chrome_profile:
        args += ["--chrome-profile", chrome_profile]
    return browser_fetch_cli.call(*args)


def call_evaluate_js(url: str, js_code: str, chrome_profile: Optional[str] = None) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as f:
        f.write(js_code)
        js_path = f.name
    try:
        args = ["eval", url, "--js-file", js_path]
        if chrome_profile:
            args += ["--chrome-profile", chrome_profile]
        return browser_fetch_cli.call(*args)
    finally:
        Path(js_path).unlink(missing_ok=True)

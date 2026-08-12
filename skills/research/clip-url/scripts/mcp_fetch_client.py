#!/usr/bin/env python3
"""Stage 3 fetch script for clip-url: calls browser-fetch-mcp's
fetch_article (site-aware extraction: generic/wechat/arxiv/xcom), which
already assembles the Markdown Origin file itself (output_format defaults
to "path") and returns its path — this script's only remaining job is
resolving the shared-vault article directory (via vault_config) and
printing the result.

Written from scratch — does not import or reuse extract-url's scripts.

Usage: python3 mcp_fetch_client.py <url> [chrome_profile]
Stdout on success: eight lines — "ORIGIN_PATH: <path>", "TITLE: <title>",
"SITE: <site>", "BLOCK_COUNT: <n>", "CHAR_COUNT: <n>",
"CODE_BLOCK_COUNT: <n>", "IMAGE_COUNT: <n>", "CONTENT_THIN: <bool>",
"THIN_RETRY_USED: <bool>".

NOTE ON mcp SDK VERSION: this script runs under the ambient system
Python (no dedicated venv, matching how extract-url's own scripts run).
That environment has mcp 1.28.1 installed, which exposes CallToolResult
fields as camelCase (isError / structuredContent) — NOT the snake_case
(is_error / structured_content) used by tools/browser-fetch-mcp's own
venv (mcp>=2.0.0). This is fine: MCP's wire protocol is JSON-RPC and is
SDK-version-independent: each side just needs to use the attribute
names its own installed SDK exposes.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

import vault_config
from browser_fetch_mcp_locate import find_browser_fetch_mcp

BROWSER_FETCH_MCP_SH = find_browser_fetch_mcp()


async def fetch_and_report(url: str, chrome_profile: Optional[str] = None) -> dict:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )

    article_dir = vault_config.get_article_paths(url)["article_dir"]
    tool_args = {"url": url, "output_dir": str(article_dir), "output_format": "path"}
    if chrome_profile:
        tool_args["chrome_profile"] = chrome_profile

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("fetch_article", tool_args)
            if result.isError:
                raise RuntimeError(f"fetch_article failed: {result.content[0].text}")
            if result.structuredContent:
                payload = result.structuredContent
            else:
                import json

                payload = json.loads(result.content[0].text)

    payload["origin_path"] = Path(payload["origin_path"])
    return payload


async def fetch_and_save(url: str, chrome_profile: Optional[str] = None) -> Path:
    payload = await fetch_and_report(url, chrome_profile)
    return payload["origin_path"]


def main():
    if len(sys.argv) < 2:
        print("Usage: mcp_fetch_client.py <url> [chrome_profile]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    chrome_profile = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else None
    try:
        payload = asyncio.run(fetch_and_report(url, chrome_profile))
    except BaseException as e:
        # anyio's TaskGroup (used internally by mcp's stdio_client/ClientSession)
        # wraps exceptions raised inside it in a BaseExceptionGroup, so a bare
        # str(e) on the outer exception can be an unhelpful wrapper — walk
        # into exception groups to find the actual leaf error message. Print
        # the bare message only (no "ERROR:" prefix) — subagent1-fetch-prompt.md
        # already adds that prefix itself when composing its own report from
        # this stderr output.
        leaf = e
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        print(str(leaf), file=sys.stderr)
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

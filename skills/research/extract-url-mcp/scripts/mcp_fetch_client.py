#!/usr/bin/env python3
"""
Stage 3 fetch script for extract-url-mcp: calls browser-fetch-mcp's
fetch_article (site-aware extraction: generic/wechat/arxiv/xcom) instead
of doing HTML parsing itself. fetch_article already handles content
extraction, site dispatch, and image downloading — this script only
formats the structured result into a Markdown Origin file.

Written from scratch — does not import or reuse extract-url's scripts.

Usage: python3 mcp_fetch_client.py <url> <output_dir> [chrome_profile]
Stdout (last line on success): "ORIGIN_PATH: <path>"

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
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)


def _format_block(block: dict) -> str:
    tag = block["tag"]
    content = block["content"]
    if tag in ("h1", "h2", "h3"):
        return f"{'#' * int(tag[1])} {content}"
    if tag == "li":
        return f"- {content}"
    if tag == "blockquote":
        return f"> {content}"
    if tag == "table":
        return content
    if tag == "pre":
        return f"```\n{content}\n```"
    if tag == "code":
        return f"`{content}`"
    return content


def _hash8(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


async def fetch_and_save(url: str, output_dir: Path, chrome_profile: Optional[str] = None) -> Path:
    server_params = StdioServerParameters(command=str(BROWSER_FETCH_MCP_SH), args=[])

    article_dir = Path(output_dir) / _hash8(url)
    tool_args = {"url": url, "output_dir": str(article_dir)}
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

    title = payload.get("title") or "Untitled"
    blocks = payload.get("blocks", [])

    # Drop a leading h1 block that just repeats the title we already use
    # as the document heading (fetch_article's generic JS extracts the
    # title from the page's own h1 but also walks that h1 into blocks).
    if blocks and blocks[0]["tag"] == "h1" and blocks[0]["content"] == title:
        blocks = blocks[1:]

    image_blocks = payload.get("image_blocks", [])
    pre_imgs = [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == -1]

    body_units = []
    if pre_imgs:
        body_units.append("\n".join(pre_imgs))

    for i, block in enumerate(blocks):
        parts = [_format_block(block)]
        for img in image_blocks:
            if img["after_block"] == i:
                parts.append(f'![](../Image/{img["filename"]})')
        body_units.append("\n".join(parts))

    body = "\n\n".join(body_units)

    origin_dir = article_dir / "Origin"
    origin_dir.mkdir(parents=True, exist_ok=True)
    origin_path = origin_dir / "article.md"

    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    content = f"""---
source_url: {url}
fetch_date: {fetch_date}
origin_title: "{title}"
author: {payload.get("author", "")}
publish_date: {payload.get("publish_date", "")}
---

# {title}

{body}
"""
    origin_path.write_text(content, encoding="utf-8")
    return origin_path


def main():
    if len(sys.argv) < 3:
        print("Usage: mcp_fetch_client.py <url> <output_dir> [chrome_profile]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    output_dir = Path(sys.argv[2])
    chrome_profile = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] else None
    origin_path = asyncio.run(fetch_and_save(url, output_dir, chrome_profile))
    print(f"ORIGIN_PATH: {origin_path}")


if __name__ == "__main__":
    main()

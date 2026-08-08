#!/usr/bin/env python3
"""
Stage 1 validation script for extract-url-mcp: a real MCP client that
spawns tools/browser-fetch-mcp as a stdio server, calls its fetch_page
tool, extracts a readable article from the returned HTML, and saves an
Origin markdown file.

Written from scratch — does not import or reuse extract-url's scripts.

Usage: python3 mcp_fetch_client.py <url> <output_dir>
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
from html.parser import HTMLParser
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)

BLOCK_TAGS = {"h1", "h2", "h3", "p", "li", "blockquote"}
SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "button", "form"}


class _ArticleExtractor(HTMLParser):
    """Minimal readable-content extractor: pulls <title> plus text from
    heading/paragraph/list/quote tags, skipping nav/script/style noise."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.blocks: list[tuple[str, str]] = []
        self._skip_depth = 0
        self._in_title = False
        self._current_tag = None
        self._current_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = True
        if tag in BLOCK_TAGS:
            self._current_tag = tag
            self._current_text = []

    def handle_endtag(self, tag):
        if tag in SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._skip_depth:
            return
        if tag == "title":
            self._in_title = False
        if tag == self._current_tag:
            text = " ".join("".join(self._current_text).split())
            if text and len(text) > 10:
                self.blocks.append((tag, text))
            self._current_tag = None
            self._current_text = []

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._current_tag:
            self._current_text.append(data)


def extract_article(html: str) -> dict:
    parser = _ArticleExtractor()
    parser.feed(html)
    return {"title": parser.title, "blocks": parser.blocks}


def _format_block(tag: str, text: str) -> str:
    if tag in ("h1", "h2", "h3"):
        return f"{'#' * int(tag[1])} {text}"
    if tag == "li":
        return f"- {text}"
    if tag == "blockquote":
        return f"> {text}"
    return text


def _hash8(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


async def fetch_and_save(url: str, output_dir: Path) -> Path:
    server_params = StdioServerParameters(command=str(BROWSER_FETCH_MCP_SH), args=[])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("fetch_page", {"url": url})
            if result.isError:
                raise RuntimeError(f"fetch_page failed: {result.content[0].text}")
            if result.structuredContent:
                payload = result.structuredContent
            else:
                import json

                payload = json.loads(result.content[0].text)

    article = extract_article(payload["html"])
    title = article["title"] or payload.get("title") or "Untitled"

    # Drop a leading h1 block that just repeats the title we already use
    # as the document heading (the extractor and the page's own <h1> both
    # pick it up otherwise).
    blocks = article["blocks"]
    if blocks and blocks[0][0] == "h1" and blocks[0][1] == title:
        blocks = blocks[1:]

    article_dir = Path(output_dir) / _hash8(url) / "Origin"
    article_dir.mkdir(parents=True, exist_ok=True)
    origin_path = article_dir / "article.md"

    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    body = "\n\n".join(_format_block(tag, text) for tag, text in blocks)

    content = f"""---
source_url: {url}
fetch_date: {fetch_date}
origin_title: "{title}"
---

# {title}

{body}
"""
    origin_path.write_text(content, encoding="utf-8")
    return origin_path


def main():
    if len(sys.argv) < 3:
        print("Usage: mcp_fetch_client.py <url> <output_dir>", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    output_dir = Path(sys.argv[2])
    origin_path = asyncio.run(fetch_and_save(url, output_dir))
    print(f"ORIGIN_PATH: {origin_path}")


if __name__ == "__main__":
    main()

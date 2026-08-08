"""MCP server exposing fetch_page (raw HTML) and fetch_article (structured,
site-aware extraction for generic/WeChat/arXiv URLs). Both share the same
warm persistent-context mechanism; X.com is not supported by fetch_article
yet — see docs/superpowers/specs/2026-08-08-browser-fetch-mcp-article-extraction-design.md."""
import hashlib
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from mcp.server import MCPServer
from playwright.async_api import async_playwright, BrowserContext

from browser_fetch_mcp.cookies import extract_cookies
from browser_fetch_mcp.extractors import (
    EXTRACT_JS,
    dispatch_site,
    extract_wechat_publish_date,
    is_thin,
)
from browser_fetch_mcp.images import download_images

mcp = MCPServer("browser-fetch-mcp")

ANON_KEY = "__anon__"

_state = {"playwright": None, "contexts": {}}


def _data_dir() -> Path:
    override = os.environ.get("BROWSER_FETCH_MCP_DATA_DIR")
    base = (
        Path(override)
        if override
        else Path.home() / ".hskill" / "browser-fetch-mcp" / "contexts"
    )
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    base.chmod(0o700)
    return base


async def _get_context(key: str) -> BrowserContext:
    if key not in _state["contexts"]:
        if _state["playwright"] is None:
            _state["playwright"] = await async_playwright().start()
        profile_dir = _data_dir() / key
        profile_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        profile_dir.chmod(0o700)
        _state["contexts"][key] = await _state["playwright"].chromium.launch_persistent_context(
            str(profile_dir), headless=True
        )
    return _state["contexts"][key]


def _profile_key(chrome_profile: str) -> str:
    return hashlib.sha256(chrome_profile.encode("utf-8")).hexdigest()[:16]


@mcp.tool()
async def fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    """Fetch a URL with a warm headless-browser context, optionally
    injecting cookies decrypted from a local Chrome profile.

    Raises ValueError if use_auth=True and chrome_profile is not given —
    this never silently degrades to an anonymous fetch, so callers can't
    mistake an anonymous result for an authenticated one.
    """
    if use_auth and not chrome_profile:
        raise ValueError("chrome_profile is required when use_auth=True")

    key = _profile_key(chrome_profile) if use_auth else ANON_KEY
    ctx = await _get_context(key)

    cookies_injected = 0
    if use_auth:
        cookies_dict = extract_cookies(url, chrome_profile)
        if cookies_dict:
            domain = urlparse(url).hostname
            pw_cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/", "secure": url.startswith("https")}
                for k, v in cookies_dict.items()
            ]
            await ctx.add_cookies(pw_cookies)
            cookies_injected = len(pw_cookies)

    page = await ctx.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        title = await page.title()
        html = await page.content()
        status = response.status if response else 0
    finally:
        await page.close()

    return {
        "html": html,
        "title": title,
        "status": status,
        "cookies_injected": cookies_injected,
    }


@mcp.tool()
async def fetch_article(
    url: str,
    output_dir: str,
    chrome_profile: Optional[str] = None,
) -> dict:
    """Fetch a URL and extract structured article content: title, author,
    publish_date, text/heading/list/table blocks, and downloaded images.
    Routes to a site-specific extraction script for generic web pages,
    WeChat official-account articles (mp.weixin.qq.com), and arXiv HTML
    papers (arxiv.org/html/...). Raises ValueError for X.com/Twitter URLs
    — not supported yet.

    If chrome_profile is given and the first (anonymous) fetch yields thin
    content (<20 blocks or <3000 chars), automatically retries once with
    cookies injected from that Chrome profile and keeps whichever result
    has more blocks. chrome_profile is optional — omit it to skip the
    retry and always return the anonymous result as-is.

    Raises ValueError if url's scheme isn't http/https — fetch_page has
    no such check today, but fetch_article adds one since it's a new
    tool that navigates to caller-supplied URLs (matches the "Security:
    validate URL scheme FIRST" guard all four extract-url scripts carry).
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    site = dispatch_site(url)
    js = EXTRACT_JS[site]

    ctx = await _get_context(ANON_KEY)
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        original_html = await page.content()
        result = await page.evaluate(js)
    finally:
        await page.close()

    cookies_injected = 0
    thin_retry_used = False
    if chrome_profile and is_thin(result):
        thin_retry_used = True
        auth_key = _profile_key(chrome_profile)
        auth_ctx = await _get_context(auth_key)

        cookies_dict = extract_cookies(url, chrome_profile)
        if cookies_dict:
            domain = urlparse(url).hostname
            pw_cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/", "secure": url.startswith("https")}
                for k, v in cookies_dict.items()
            ]
            await auth_ctx.add_cookies(pw_cookies)
            cookies_injected = len(pw_cookies)

        auth_page = await auth_ctx.new_page()
        try:
            await auth_page.goto(url, wait_until="domcontentloaded", timeout=30000)
            retry_result = await auth_page.evaluate(js)
        finally:
            await auth_page.close()

        if len(retry_result.get("blocks", [])) > len(result.get("blocks", [])):
            result = retry_result

    if site == "wechat":
        publish_date = extract_wechat_publish_date(original_html)
    else:
        publish_date = (result.get("publishDate") or "")[:10]

    image_blocks = download_images(result.get("imageBlocks", []), Path(output_dir))

    return {
        "title": result.get("title", "Untitled"),
        "author": result.get("author", ""),
        "publish_date": publish_date,
        "blocks": [{"tag": b["tag"], "content": b["content"]} for b in result.get("blocks", [])],
        "image_blocks": image_blocks,
        "site": site,
        "cookies_injected": cookies_injected,
        "thin_retry_used": thin_retry_used,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""FastMCP server exposing fetch_page: a warm-context headless browser
fetch tool. Auth (Chrome cookie injection) is wired in Task 4."""
import hashlib
import os
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, BrowserContext

from browser_fetch_mcp.cookies import extract_cookies

mcp = FastMCP("browser-fetch-mcp")

ANON_KEY = "__anon__"

_state = {"playwright": None, "contexts": {}}


def _data_dir() -> Path:
    override = os.environ.get("BROWSER_FETCH_MCP_DATA_DIR")
    base = (
        Path(override)
        if override
        else Path.home() / ".hskill" / "tools" / "browser-fetch-mcp" / "contexts"
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


async def _get_context(key: str) -> BrowserContext:
    if key not in _state["contexts"]:
        if _state["playwright"] is None:
            _state["playwright"] = await async_playwright().start()
        profile_dir = _data_dir() / key
        profile_dir.mkdir(parents=True, exist_ok=True)
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
            netloc_parts = urlparse(url).netloc.split(".")
            domain = (
                "." + ".".join(netloc_parts[-2:])
                if len(netloc_parts) >= 2
                else urlparse(url).netloc
            )
            pw_cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/", "secure": True}
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


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

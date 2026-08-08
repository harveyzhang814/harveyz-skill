"""FastMCP server exposing fetch_page: a warm-context headless browser
fetch tool. Auth (Chrome cookie injection) is wired in Task 4."""
import hashlib
import os
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, BrowserContext

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


@mcp.tool()
async def fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    """Fetch a URL with a warm headless-browser context.

    use_auth/chrome_profile are accepted here for interface stability but
    not yet implemented — Task 4 adds cookie injection.
    """
    ctx = await _get_context(ANON_KEY)
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
        "cookies_injected": 0,
    }


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

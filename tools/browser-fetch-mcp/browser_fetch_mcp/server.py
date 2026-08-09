"""MCP server exposing fetch_page (raw HTML) and fetch_article (structured,
site-aware extraction for generic/WeChat/arXiv/X.com URLs). generic/WeChat/
arXiv share the warm persistent-context mechanism; X.com uses a one-off
browser launch per call instead (headed-mode-first, headless fallback) —
see docs/superpowers/specs/2026-08-08-browser-fetch-mcp-xcom-extraction-design.md."""
import asyncio
import hashlib
import os
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from mcp.server import FastMCP
from playwright.async_api import async_playwright, BrowserContext

from browser_fetch_mcp.cookies import extract_cookies
from browser_fetch_mcp.extractors import (
    EXTRACT_JS,
    EXTRACT_JS_XCOM_HEADED,
    EXTRACT_JS_XCOM_HEADLESS,
    dispatch_site,
    extract_wechat_publish_date,
    is_thin,
)
from browser_fetch_mcp.images import download_images
from browser_fetch_mcp import config

mcp = FastMCP("browser-fetch-mcp")

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


async def _xcom_scrape(url: str, pw_cookies: list[dict], headless: bool) -> dict:
    """One-off browser launch for x.com/twitter.com — never reuses the warm
    persistent context (_get_context): headed mode needs a real display and
    shouldn't be kept alive indefinitely just because one call used it.

    Always closes the browser in a finally block. The original CLI script
    (playwright_xcom.py) had no such guard — a leaked browser process there
    was harmless because the whole process exited right after each run.
    browser-fetch-mcp is long-lived, so an unguarded leak here would
    accumulate zombie Chrome processes over the server's lifetime.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            ctx_kwargs = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            }
            if not headless:
                ctx_kwargs["viewport"] = {"width": 1280, "height": 900}

            ctx = await browser.new_context(**ctx_kwargs)
            await ctx.add_cookies(pw_cookies)
            page = await ctx.new_page()
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=60000)

            if not headless:
                is_x_notes = False
                try:
                    await page.wait_for_selector(
                        '[data-testid="twitterArticleRichTextView"]', timeout=70000
                    )
                    is_x_notes = True
                except Exception:
                    pass  # not an X Notes article, proceed normally

                if is_x_notes:
                    # Do NOT scroll for X Notes: scrolling unmounts richTextView
                    # from the virtual DOM and causes reply articles to appear
                    # before the main tweet in DOM order.
                    await page.wait_for_timeout(2000)
                else:
                    # Regular tweet: scroll to trigger Draft.js atomic block rendering
                    for i in range(25):
                        await page.evaluate(f"window.scrollTo(0, {i * 400})")
                        await page.wait_for_timeout(200)
                    try:
                        await page.wait_for_selector("code.language-text, pre", timeout=8000)
                    except Exception:
                        pass
                    await page.wait_for_timeout(1000)

            js = EXTRACT_JS_XCOM_HEADLESS if headless else EXTRACT_JS_XCOM_HEADED
            result = await page.evaluate(js)
            result["publishDate"] = result.get("publishDate", "")
            return result
        finally:
            await browser.close()


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
async def get_default_chrome_profile() -> dict:
    """Read the persisted default Chrome profile, set via
    set_default_chrome_profile. Returns {"profile_path": None} if no
    default has ever been configured."""
    return {"profile_path": config.get_default_chrome_profile(_data_dir())}


@mcp.tool()
async def set_default_chrome_profile(profile_path: str) -> dict:
    """Persist profile_path as the default Chrome profile fetch_article
    uses whenever a caller omits chrome_profile. Raises ValueError if
    profile_path does not exist or is not a directory — never silently
    accepts a bad path."""
    path = Path(profile_path)
    if not path.is_dir():
        raise ValueError(
            f"chrome_profile path does not exist or is not a directory: {profile_path}"
        )
    config.set_default_chrome_profile(_data_dir(), profile_path)
    return {"ok": True}


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
    papers (arxiv.org/html/...), and X.com/Twitter posts and articles
    (x.com/twitter.com).

    For x.com/twitter.com URLs, chrome_profile is required (raises ValueError
    if omitted — x.com has no anonymous mode) and the fetch uses a one-off
    browser launch (headed mode first, headless fallback) instead of the
    warm persistent context the other three sites share.

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

    if site == "xcom":
        if not chrome_profile:
            raise ValueError("chrome_profile is required for x.com/Twitter URLs")

        cookies_dict = await asyncio.to_thread(extract_cookies, "https://x.com", chrome_profile)
        if not {"auth_token", "ct0", "twid"} & cookies_dict.keys():
            raise ValueError(
                f"No x.com session cookies in {chrome_profile} — "
                "log into x.com in that Chrome profile first"
            )
        pw_cookies = [
            {"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True}
            for k, v in cookies_dict.items()
        ]

        try:
            result = await _xcom_scrape(url, pw_cookies, headless=False)
        except Exception as e:
            print(
                f"[browser-fetch-mcp] headed x.com scrape failed ({e}); "
                f"falling back to headless (lower fidelity)",
                file=sys.stderr,
            )
            try:
                result = await _xcom_scrape(url, pw_cookies, headless=True)
            except Exception as e:
                raise RuntimeError(
                    f"fetch_article failed for {url} (headed and headless both failed): {e}"
                ) from e

        if result.get("error"):
            raise RuntimeError(f"fetch_article failed for {url}: {result['error']}")

        cookies_injected = len(pw_cookies)
        thin_retry_used = False
    else:
        js = EXTRACT_JS[site]

        ctx = await _get_context(ANON_KEY)
        page = await ctx.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            if site == "wechat":
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
                if site == "wechat":
                    retry_html = await auth_page.content()
                retry_result = await auth_page.evaluate(js)
            finally:
                await auth_page.close()

            if len(retry_result.get("blocks", [])) > len(result.get("blocks", [])):
                result = retry_result
                if site == "wechat":
                    original_html = retry_html

    if site == "wechat":
        publish_date = extract_wechat_publish_date(original_html)
    else:
        publish_date = (result.get("publishDate") or "")[:10]

    image_blocks = await asyncio.to_thread(download_images, result.get("imageBlocks", []), Path(output_dir))

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

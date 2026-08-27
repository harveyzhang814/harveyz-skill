"""Core fetch functions exposing fetch_page (raw HTML) and fetch_article (structured,
site-aware extraction for generic/WeChat/arXiv/X.com URLs). generic/WeChat/
arXiv share the warm persistent-context mechanism; X.com uses a one-off
browser launch per call instead (headed-mode-first, headless fallback) —
see docs/superpowers/specs/2026-08-08-browser-fetch-mcp-xcom-extraction-design.md."""
import asyncio
import hashlib
import os
import random
import sys
import time
import uuid
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import urlparse

from playwright.async_api import async_playwright, BrowserContext

from browser_fetch.cookies import extract_cookies
from browser_fetch.extractors import (
    EXTRACT_JS,
    EXTRACT_JS_XCOM_HEADED,
    EXTRACT_JS_XCOM_HEADLESS,
    EXTRACT_JS_XCOM_TIMELINE,
    EXTRACT_JS_YOUTUBE_CHANNEL,
    build_channel_video_list,
    dispatch_site,
    is_thin,
    normalize_youtube_channel_url,
    parse_youtube_rss,
    wechat_publish_date_from_ct,
    youtube_feed_url,
)
from browser_fetch.images import download_images
from browser_fetch.profiles import list_chrome_profiles as _list_chrome_profiles
from browser_fetch import config, markdown, pacing, pacing_log

ANON_KEY = "__anon__"

_state = {"playwright": None, "contexts": {}}
_rng = random.Random()


def _data_dir() -> Path:
    override = os.environ.get("BROWSER_FETCH_DATA_DIR")
    base = (
        Path(override)
        if override
        else Path.home() / ".hskill" / "browser-fetch" / "contexts"
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


_TIMELINE_MAX_SCROLL_ITERATIONS = 15
_TIMELINE_STALL_LIMIT = 2


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


async def _xcom_scrape_timeline(
    profile_url: str, pw_cookies: list[dict], headless: bool, max_tweets: int, run_id: str
) -> dict:
    """One-off browser launch for an x.com/twitter.com profile timeline —
    same lifecycle model as _xcom_scrape (never reuses the warm persistent
    context, always closes in finally), but scrolls repeatedly and merges
    each pass's visible cards into an accumulator (keyed by tweet_id, so a
    card re-seen after scrolling doesn't duplicate) instead of extracting
    once. Stops early once max_tweets are collected, or after
    _TIMELINE_STALL_LIMIT consecutive scroll passes yield no new tweets
    (the account has fewer than max_tweets total, or the feed stopped
    loading more).

    Scroll choreography uses page.mouse.wheel (a trusted, CDP-dispatched
    input event) broken into several small ticks with randomized gaps,
    occasional backscroll, and randomized read pauses — see
    docs/superpowers/specs/2026-08-17-xtimeline-human-pacing-design.md.
    A backscroll pass is expected to yield zero new tweets (the viewport
    moves back over already-collected cards) and must not count toward
    stalls, or it gets misread as "reached the end of the feed"."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        attempt = "headless" if headless else "headed"
        try:
            viewport = pacing.pick_viewport(_rng)
            pacing_log.append_event(
                _data_dir(), "viewport", run_id=run_id, attempt=attempt,
                width=viewport["width"], height=viewport["height"],
            )
            ctx_kwargs = {
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
                "viewport": viewport,
            }

            ctx = await browser.new_context(**ctx_kwargs)
            await ctx.add_cookies(pw_cookies)
            page = await ctx.new_page()
            await page.goto(profile_url, timeout=60000, wait_until="domcontentloaded")
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=60000)
            initial_dwell = pacing.pick_initial_dwell(_rng)
            pacing_log.append_event(
                _data_dir(), "initial_dwell", run_id=run_id, attempt=attempt,
                dwell_s=round(initial_dwell, 2),
            )
            await page.wait_for_timeout(initial_dwell * 1000)

            collected: dict[str, dict] = {}
            stalls = 0
            backscrolled = False
            stopped_reason = "iteration_limit"
            iterations_run = 0
            for i in range(_TIMELINE_MAX_SCROLL_ITERATIONS):
                iterations_run = i + 1
                result = await page.evaluate(EXTRACT_JS_XCOM_TIMELINE)
                before = len(collected)
                for tweet in result["tweets"]:
                    collected[tweet["tweetId"]] = tweet

                if len(collected) >= max_tweets:
                    stopped_reason = "max_tweets"
                    break
                if len(collected) == before:
                    if backscrolled:
                        pass
                    else:
                        stalls += 1
                        if stalls >= _TIMELINE_STALL_LIMIT:
                            stopped_reason = "stall_limit"
                            break
                else:
                    stalls = 0

                pacing_log.append_event(
                    _data_dir(), "scroll_pass_start", run_id=run_id, attempt=attempt,
                    iteration=i, tweets_before=before, stalls=stalls,
                )

                x, y, steps = pacing.plan_mouse_move(_rng, viewport)
                await page.mouse.move(x, y, steps=steps)

                backscrolled = pacing.should_backscroll(_rng)
                for tick_index, (delta, gap) in enumerate(pacing.plan_scroll_burst(_rng, backward=backscrolled)):
                    await page.mouse.wheel(0, delta)
                    await page.wait_for_timeout(gap * 1000)
                    pacing_log.append_event(
                        _data_dir(), "wheel_tick", run_id=run_id, attempt=attempt,
                        iteration=i, tick_index=tick_index, delta=delta, gap_s=round(gap, 3),
                    )

                read_pause = pacing.pick_read_pause(_rng)
                await page.wait_for_timeout(read_pause * 1000)

                pacing_log.append_event(
                    _data_dir(), "scroll_pass_end", run_id=run_id, attempt=attempt,
                    iteration=i, tweets_after=len(collected), backscroll=backscrolled,
                    mouse_move={"x": x, "y": y, "steps": steps}, read_pause_s=round(read_pause, 2),
                )

            tweets = sorted(collected.values(), key=lambda t: int(t["tweetId"]), reverse=True)
            tweets = tweets[:max_tweets]
            pacing_log.append_event(
                _data_dir(), "scrape_attempt_end", run_id=run_id, attempt=attempt,
                total_tweets=len(tweets), iterations_run=iterations_run, stopped_reason=stopped_reason,
            )
            return {"tweets": tweets}
        finally:
            await browser.close()


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


async def get_default_chrome_profile() -> dict:
    """Read the persisted default Chrome profile, set via
    set_default_chrome_profile. Returns {"profile_path": None} if no
    default has ever been configured."""
    return {"profile_path": config.get_default_chrome_profile(_data_dir())}


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


async def list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> dict:
    """List local Chrome profiles and, for each, which of cookie_names
    exist for the given host_keys (existence-only, never decrypted).
    Returns {"profiles": [{"profile_path", "account_email",
    "matched_cookie_names", "looks_logged_in"}, ...]}. Callers decide
    which profile to recommend/use — this tool never picks one."""
    profiles = await asyncio.to_thread(_list_chrome_profiles, host_keys, cookie_names)
    return {"profiles": profiles}


async def fetch_article(
    url: str,
    output_dir: str,
    chrome_profile: Optional[str] = None,
    output_format: Literal["path", "json"] = "path",
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

    output_format controls the return shape:
    - "path" (default): assembles the article into Markdown, writes it to
      <output_dir>/Origin/<sanitized title>.md, and returns {"origin_path", "title",
      "author", "publish_date", "site", "cookies_injected",
      "thin_retry_used", "block_count", "char_count", "code_block_count",
      "image_count", "content_thin"} — no blocks/image_blocks, keeping the
      payload out of the caller's context.
    - "json": returns the raw structured data instead — {"title", "author",
      "publish_date", "blocks", "image_blocks", "site", "cookies_injected",
      "thin_retry_used", "block_count", "char_count", "code_block_count",
      "image_count", "content_thin"} — no file is written.
    block_count/char_count/code_block_count/image_count/content_thin are
    lightweight diagnostics (ints and a bool, never the extracted content
    itself) so a caller can report stats or detect thin/failed extraction
    without pulling blocks into its context.
    Raises ValueError for any other value.

    Raises ValueError if url's scheme isn't http/https — fetch_page has
    no such check today, but fetch_article adds one since it's a new
    tool that navigates to caller-supplied URLs (matches the "Security:
    validate URL scheme FIRST" guard all four extract-url scripts carry).
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    if output_format not in ("path", "json"):
        raise ValueError(f"Invalid output_format: {output_format!r} (expected 'path' or 'json')")

    effective_chrome_profile = chrome_profile or config.get_default_chrome_profile(_data_dir())

    site = dispatch_site(url)

    if site == "xcom":
        if not effective_chrome_profile:
            raise ValueError("chrome_profile is required for x.com/Twitter URLs")

        cookies_dict = await asyncio.to_thread(extract_cookies, "https://x.com", effective_chrome_profile)
        if not {"auth_token", "ct0", "twid"} & cookies_dict.keys():
            raise ValueError(
                f"No x.com session cookies in {effective_chrome_profile} — "
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
            result = await page.evaluate(js)
        finally:
            await page.close()

        cookies_injected = 0
        thin_retry_used = False
        if effective_chrome_profile and is_thin(result):
            thin_retry_used = True
            auth_key = _profile_key(effective_chrome_profile)
            auth_ctx = await _get_context(auth_key)

            cookies_dict = extract_cookies(url, effective_chrome_profile)
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
        publish_date = wechat_publish_date_from_ct(result.get("ct"))
    else:
        publish_date = (result.get("publishDate") or "")[:10]

    image_blocks = await asyncio.to_thread(download_images, result.get("imageBlocks", []), Path(output_dir))

    title = result.get("title", "Untitled")
    author = result.get("author", "")
    blocks = [{"tag": b["tag"], "content": b["content"]} for b in result.get("blocks", [])]
    block_count = len(blocks)
    char_count = sum(len(b["content"]) for b in blocks)
    code_block_count = sum(1 for b in blocks if b["tag"] == "pre")
    image_count = len(image_blocks)
    content_thin = is_thin(result)

    if output_format == "json":
        return {
            "title": title,
            "author": author,
            "publish_date": publish_date,
            "blocks": blocks,
            "image_blocks": image_blocks,
            "site": site,
            "cookies_injected": cookies_injected,
            "thin_retry_used": thin_retry_used,
            "block_count": block_count,
            "char_count": char_count,
            "code_block_count": code_block_count,
            "image_count": image_count,
            "content_thin": content_thin,
        }

    origin_path = markdown.assemble_and_write(
        Path(output_dir), url, title, author, publish_date, blocks, image_blocks
    )
    return {
        "origin_path": str(origin_path),
        "title": title,
        "author": author,
        "publish_date": publish_date,
        "site": site,
        "cookies_injected": cookies_injected,
        "thin_retry_used": thin_retry_used,
        "block_count": block_count,
        "char_count": char_count,
        "code_block_count": code_block_count,
        "image_count": image_count,
        "content_thin": content_thin,
    }


async def fetch_user_timeline(
    profile_url: str,
    chrome_profile: Optional[str] = None,
    max_tweets: int = 20,
) -> dict:
    """Fetch the most recent tweets visible on an x.com/twitter.com profile
    timeline page — a lightweight batch listing (tweet_id/url/text/
    timestamp/author_handle/type per tweet), NOT the full per-tweet
    extraction fetch_article does (no thread expansion, no image download).
    Scrolls the timeline collecting distinct tweet cards until max_tweets
    are found or the feed stops yielding new ones, then returns them sorted
    most-recent-first by tweet_id (X's snowflake IDs are monotonically
    increasing, so numeric comparison is a reliable recency order).

    type is one of "post", "repost", "quote", "reply" (repost > quote >
    reply > post priority when multiple signals are present — e.g. a
    repost of a reply classifies as "repost", since that's why it's on
    this timeline). For "repost", the returned url/text/author_handle
    already belong to the ORIGINAL tweet (X renders reposted cards with
    the original tweet's own data, not the reposter's). For "reply",
    reply_to_handle names who it's replying to. For "quote",
    quoted_author/quoted_text/quoted_timestamp describe the embedded
    quoted tweet (its own permalink isn't extractable — X doesn't render
    it as a real link in this view). All four of reply_to_handle/
    quoted_author/quoted_text/quoted_timestamp are None except for their
    one applicable type.

    chrome_profile is required (falls back to the persisted default if
    omitted; raises ValueError if neither is set) — x.com has no
    anonymous timeline view. Uses the same one-off browser launch as
    fetch_article's xcom path (headed first, headless fallback).

    Raises ValueError if profile_url's scheme isn't http/https, or if
    profile_url isn't an x.com/twitter.com URL.
    """
    parsed_url = urlparse(profile_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    if dispatch_site(profile_url) != "xcom":
        raise ValueError(f"fetch_user_timeline only supports x.com/twitter.com URLs, got: {profile_url}")

    effective_chrome_profile = chrome_profile or config.get_default_chrome_profile(_data_dir())
    if not effective_chrome_profile:
        raise ValueError("chrome_profile is required for fetch_user_timeline")

    cookies_dict = await asyncio.to_thread(extract_cookies, "https://x.com", effective_chrome_profile)
    if not {"auth_token", "ct0", "twid"} & cookies_dict.keys():
        raise ValueError(
            f"No x.com session cookies in {effective_chrome_profile} — "
            "log into x.com in that Chrome profile first"
        )
    pw_cookies = [
        {"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True}
        for k, v in cookies_dict.items()
    ]

    run_id = uuid.uuid4().hex[:12]

    now = time.time()
    last = config.get_last_timeline_fetch_at(_data_dir())
    if last is not None:
        planned_cooldown = pacing.pick_cooldown(_rng)
        remaining = planned_cooldown - (now - last)
        waited = max(remaining, 0.0)
        pacing_log.append_event(
            _data_dir(), "cooldown", run_id=run_id, profile_url=profile_url, last_fetch_at=last,
            planned_cooldown_s=round(planned_cooldown, 2), waited_s=round(waited, 2),
        )
        if remaining > 0:
            await asyncio.sleep(remaining)
    else:
        pacing_log.append_event(
            _data_dir(), "cooldown_skipped", run_id=run_id, profile_url=profile_url, reason="no_previous_fetch",
        )

    scrape_start = time.time()
    result = None
    error_msg = None
    headless_fallback = False
    try:
        try:
            result = await _xcom_scrape_timeline(
                profile_url, pw_cookies, headless=False, max_tweets=max_tweets, run_id=run_id
            )
        except Exception as e:
            headless_fallback = True
            print(
                f"[browser-fetch-mcp] headed timeline scrape failed ({e}); "
                f"falling back to headless (lower fidelity)",
                file=sys.stderr,
            )
            try:
                result = await _xcom_scrape_timeline(
                    profile_url, pw_cookies, headless=True, max_tweets=max_tweets, run_id=run_id
                )
            except Exception as e2:
                error_msg = str(e2)
                raise RuntimeError(
                    f"fetch_user_timeline failed for {profile_url} (headed and headless both failed): {e2}"
                ) from e2
    finally:
        config.set_last_timeline_fetch_at(_data_dir(), now)
        pacing_log.append_event(
            _data_dir(), "fetch_end", run_id=run_id, profile_url=profile_url,
            total_tweets=len(result["tweets"]) if result is not None else 0,
            headless_fallback=headless_fallback,
            duration_s=round(time.time() - scrape_start, 2),
            error=error_msg,
        )

    tweets = [
        {
            "tweet_id": t["tweetId"],
            "url": t["url"],
            "text": t["text"],
            "timestamp": t["timestamp"],
            "author_handle": t["authorHandle"],
            "type": t["type"],
            "reply_to_handle": t["replyToHandle"],
            "quoted_author": t["quotedAuthor"],
            "quoted_text": t["quotedText"],
            "quoted_timestamp": t["quotedTimestamp"],
        }
        for t in result["tweets"]
    ]
    return {"tweets": tweets}


async def fetch_channel_videos(
    channel_url: str,
    chrome_profile: Optional[str] = None,
    max_videos: int = 30,
) -> dict:
    """List the most recent uploads on a YouTube channel — title, canonical
    watch URL and publish date per video, nothing else. This is a listing
    tool: it never downloads a video, transcript or description.

    channel_url may be any channel URL form (/@handle, /channel/UCxxx, /c/,
    /user/, with or without a tab suffix); it is normalized to the Videos tab
    before fetching. Returns videos newest-first, in the order YouTube's
    uploads grid renders them, capped at max_videos (~30 fit on the first
    render — the grid is not scrolled).

    Each video carries `published_text` (the grid's relative date, e.g.
    "2 weeks ago") and `published_at` (an exact ISO 8601 timestamp taken from
    the channel's Atom uploads feed). The feed only covers the ~15 newest
    uploads, so `published_at` is None for anything older — use
    `published_text` as the fallback. `url` is the canonical
    https://www.youtube.com/watch?v=<id> form, stable enough to use as a
    video's unique key.

    chrome_profile (falling back to the persisted default) supplies youtube.com
    cookies so the page renders as the signed-in user. Unlike
    fetch_user_timeline it is optional: channel pages are publicly viewable, so
    a missing profile degrades to an anonymous fetch rather than an error.

    Raises ValueError if channel_url's scheme isn't http/https or it isn't a
    YouTube channel URL, and RuntimeError if the page renders without
    ytInitialData (consent wall, bot check, or a YouTube layout change).
    """
    parsed_url = urlparse(channel_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    videos_url = normalize_youtube_channel_url(channel_url)

    effective_chrome_profile = chrome_profile or config.get_default_chrome_profile(_data_dir())
    if effective_chrome_profile:
        ctx = await _get_context(_profile_key(effective_chrome_profile))
        cookies_dict = await asyncio.to_thread(
            extract_cookies, "https://www.youtube.com", effective_chrome_profile
        )
        if cookies_dict:
            await ctx.add_cookies([
                {"name": k, "value": v, "domain": ".youtube.com", "path": "/", "secure": True}
                for k, v in cookies_dict.items()
            ])
    else:
        ctx = await _get_context(ANON_KEY)

    page = await ctx.new_page()
    try:
        await page.goto(videos_url, wait_until="domcontentloaded", timeout=60000)
        result = await page.evaluate(EXTRACT_JS_YOUTUBE_CHANNEL)
    finally:
        await page.close()

    if result.get("error"):
        raise RuntimeError(f"fetch_channel_videos failed for {videos_url}: {result['error']}")

    # Exact publish timestamps live only in the uploads feed; a failure here
    # costs precision (published_at stays None), not the whole result.
    published_by_id: dict[str, str] = {}
    feed_url = youtube_feed_url(result.get("channelId", ""))
    if feed_url:
        try:
            response = await ctx.request.get(feed_url, timeout=30000)
            if response.ok:
                published_by_id = parse_youtube_rss(await response.text())
        except Exception as e:
            print(
                f"[browser-fetch-mcp] uploads feed fetch failed for {feed_url} ({e}); "
                f"falling back to relative dates only",
                file=sys.stderr,
            )

    return {
        "channel_url": videos_url,
        "channel_id": result.get("channelId", ""),
        "channel_title": result.get("channelTitle", ""),
        "videos": build_channel_video_list(result["videos"], published_by_id, max_videos),
    }


async def evaluate_js(
    url: str,
    js_code: str,
    chrome_profile: Optional[str] = None,
) -> dict:
    """Navigate to url and execute js_code via page.evaluate(), returning
    its result. Debug-only tool for the self-optimization workflow to
    iterate candidate extraction logic against a real page — writes no
    files, downloads no images, and has no thin-content retry. If
    chrome_profile is given, injects cookies decrypted from that Chrome
    profile before navigating; omit it for an anonymous fetch.

    Raises ValueError if url's scheme isn't http/https (same guard as
    fetch_article).
    """
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ValueError(f"Rejected URL with scheme '{parsed_url.scheme}' — only http/https allowed")

    if chrome_profile:
        ctx = await _get_context(_profile_key(chrome_profile))
        cookies_dict = extract_cookies(url, chrome_profile)
        if cookies_dict:
            domain = parsed_url.hostname
            pw_cookies = [
                {"name": k, "value": v, "domain": domain, "path": "/", "secure": url.startswith("https")}
                for k, v in cookies_dict.items()
            ]
            await ctx.add_cookies(pw_cookies)
    else:
        ctx = await _get_context(ANON_KEY)

    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        result = await page.evaluate(js_code)
    finally:
        await page.close()

    return {"result": result}

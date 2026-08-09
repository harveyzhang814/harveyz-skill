# fetch_article Server-Side Markdown Assembly + File Output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move "assemble Markdown, write article.md/images, return a path" from `extract-url-mcp/scripts/mcp_fetch_client.py` into browser-fetch-mcp's `fetch_article` MCP tool itself, so any caller gets the file-based contract by default while still being able to opt into the raw structured-JSON contract.

**Architecture:** `fetch_article` gains an `output_format: str = "path"` parameter. A new pure module `browser_fetch_mcp/markdown.py` holds the block-formatting/h1-dedup/image-placement/frontmatter logic (ported verbatim from `mcp_fetch_client.py`). `output_format="path"` (default) calls that module and returns `{origin_path, title, author, publish_date, site, cookies_injected, thin_retry_used}`; `output_format="json"` returns exactly today's shape (`{title, author, publish_date, blocks, image_blocks, site, cookies_injected, thin_retry_used}`), unchanged. `mcp_fetch_client.py` shrinks to a thin wrapper: compute the per-URL `article_dir`, call `fetch_article` (default `output_format`), return `Path(payload["origin_path"])`.

**Tech Stack:** Python, MCP SDK (`mcp>=2.0.0` in `tools/browser-fetch-mcp/.venv`; ambient system Python `mcp==1.28.1` for `extract-url-mcp` scripts), pytest, pytest-asyncio.

## Global Constraints

- `output_format` default is `"path"`; `"json"` must remain byte-for-byte compatible with today's `fetch_article` return shape (same keys, same values, no `article.md` written).
- Frontmatter fields and format (`source_url`, `fetch_date` in UTC+8 via `timezone(timedelta(hours=8))`, `origin_title`, `author`, `publish_date`) stay exactly as today — no new configuration.
- `fetch_page` is unchanged; out of scope for this work.
- Image download behavior (`<output_dir>/Image/img_N.ext`, filename-only metadata) is unchanged and unaffected by `output_format` — it already runs unconditionally today.
- An invalid `output_format` value raises `ValueError` before any network fetch happens (fail fast).
- `tools/browser-fetch-mcp` tests run via its dedicated venv: `tools/browser-fetch-mcp/.venv/bin/pytest`. `extract-url-mcp` tests run via ambient system Python: `python3 -m pytest skills/research/extract-url-mcp/tests/`.

---

### Task 1: `browser_fetch_mcp/markdown.py` — pure article-assembly module

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/markdown.py`
- Test: `tools/browser-fetch-mcp/tests/test_markdown.py`

**Interfaces:**
- Produces: `assemble_and_write(output_dir: Path, url: str, title: str, author: str, publish_date: str, blocks: list[dict], image_blocks: list[dict]) -> Path`. `blocks` entries are `{"tag": str, "content": str}`. `image_blocks` entries are `{"filename": str, "alt": str, "after_block": int}` (as produced by `browser_fetch_mcp.images.download_images`). Writes `<output_dir>/Origin/article.md` and returns that `Path`. Task 2 imports this as `from browser_fetch_mcp import markdown` and calls `markdown.assemble_and_write(...)`.
- Also exposes `_format_block(block: dict) -> str` (module-private, but directly unit-tested).

- [ ] **Step 1: Write the failing tests**

Create `tools/browser-fetch-mcp/tests/test_markdown.py`:

```python
"""Unit tests for markdown.py's article assembly — pure string/file
logic, no MCP protocol, no browser, no network."""
from pathlib import Path

from browser_fetch_mcp.markdown import assemble_and_write, _format_block


def test_writes_frontmatter_and_heading(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Example Domain",
        author="",
        publish_date="",
        blocks=[{"tag": "p", "content": "Some body text."}],
        image_blocks=[],
    )
    assert origin_path == tmp_path / "Origin" / "article.md"
    content = origin_path.read_text(encoding="utf-8")
    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "# Example Domain" in content
    assert "Some body text." in content


def test_leading_h1_matching_title_is_deduped(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="My Title",
        author="",
        publish_date="",
        blocks=[
            {"tag": "h1", "content": "My Title"},
            {"tag": "p", "content": "Body paragraph."},
        ],
        image_blocks=[],
    )
    content = origin_path.read_text(encoding="utf-8")
    # frontmatter's origin_title + the "# My Title" heading only —
    # the h1 block must not ALSO appear a third time as a body block.
    assert content.count("My Title") == 2


def test_image_before_first_block_is_prepended(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[{"tag": "p", "content": "Body paragraph."}],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": -1}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body = content.split("# Untitled\n\n", 1)[1]
    assert body.startswith("![](../Image/img_1.jpg)")


def test_image_after_block_zero_moves_to_pre_imgs_when_h1_deduped(tmp_path):
    """Regression: after_block indices are computed against the ORIGINAL
    (undeduped) blocks list. When blocks[0] is a dropped h1, an image with
    after_block == 0 meant 'right after the h1' — that h1 is gone, so the
    image belongs at the very start of the body (pre_imgs), not glued to
    the next real paragraph."""
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="My Title",
        author="",
        publish_date="",
        blocks=[
            {"tag": "h1", "content": "My Title"},
            {"tag": "p", "content": "Intro paragraph."},
        ],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": 0}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body_units = content.split("\n\n")
    intro_unit = next(u for u in body_units if "Intro paragraph." in u)
    assert "![](../Image/img_1.jpg)" not in intro_unit
    assert any("![](../Image/img_1.jpg)" in u for u in body_units if u != intro_unit)


def test_image_placed_after_matching_block_index(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[
            {"tag": "p", "content": "First paragraph."},
            {"tag": "p", "content": "Second paragraph."},
        ],
        image_blocks=[{"filename": "img_1.jpg", "alt": "", "after_block": 0}],
    )
    content = origin_path.read_text(encoding="utf-8")
    body_units = content.split("\n\n")
    first_unit = next(u for u in body_units if "First paragraph." in u)
    assert "![](../Image/img_1.jpg)" in first_unit


def test_block_tag_formatting():
    assert _format_block({"tag": "h2", "content": "Heading"}) == "## Heading"
    assert _format_block({"tag": "li", "content": "Item"}) == "- Item"
    assert _format_block({"tag": "blockquote", "content": "Quoted"}) == "> Quoted"
    assert _format_block({"tag": "table", "content": "| a | b |"}) == "| a | b |"
    assert _format_block({"tag": "pre", "content": "code()"}) == "```\ncode()\n```"
    assert _format_block({"tag": "code", "content": "x"}) == "`x`"
    assert _format_block({"tag": "p", "content": "Plain text."}) == "Plain text."


def test_creates_origin_dir_and_returns_its_path(tmp_path):
    origin_path = assemble_and_write(
        tmp_path,
        url="https://example.com",
        title="Untitled",
        author="",
        publish_date="",
        blocks=[],
        image_blocks=[],
    )
    assert origin_path.parent == tmp_path / "Origin"
    assert origin_path.parent.is_dir()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && .venv/bin/pytest tests/test_markdown.py -v`
Expected: FAIL/ERROR — `ModuleNotFoundError: No module named 'browser_fetch_mcp.markdown'`

- [ ] **Step 3: Write the implementation**

Create `tools/browser-fetch-mcp/browser_fetch_mcp/markdown.py`:

```python
"""Article Markdown assembly for fetch_article's output_format="path"
mode: block formatting, leading-h1 dedup against the title, image
placement by after_block index, and YAML frontmatter — ported verbatim
from extract-url-mcp/scripts/mcp_fetch_client.py's original
_format_block/fetch_and_save assembly logic.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path


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


def assemble_and_write(
    output_dir: Path,
    url: str,
    title: str,
    author: str,
    publish_date: str,
    blocks: list[dict],
    image_blocks: list[dict],
) -> Path:
    """Assemble blocks/image_blocks into Markdown with YAML frontmatter
    and write it to <output_dir>/Origin/article.md. Returns that path."""
    dedup_offset = 0
    if blocks and blocks[0]["tag"] == "h1" and blocks[0]["content"] == title:
        blocks = blocks[1:]
        dedup_offset = 1

    pre_imgs = [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == -1]
    if dedup_offset:
        # after_block == 0 meant "right after the h1" — that h1 is gone
        # now, so those images belong at the very start of the body instead.
        pre_imgs += [f'![](../Image/{img["filename"]})' for img in image_blocks if img["after_block"] == 0]

    body_units = []
    if pre_imgs:
        body_units.append("\n".join(pre_imgs))

    for i, block in enumerate(blocks):
        parts = [_format_block(block)]
        for img in image_blocks:
            if img["after_block"] == i + dedup_offset:
                parts.append(f'![](../Image/{img["filename"]})')
        body_units.append("\n".join(parts))

    body = "\n\n".join(body_units)

    origin_dir = Path(output_dir) / "Origin"
    origin_dir.mkdir(parents=True, exist_ok=True)
    origin_path = origin_dir / "article.md"

    fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")

    content = f"""---
source_url: {url}
fetch_date: {fetch_date}
origin_title: "{title}"
author: "{author}"
publish_date: "{publish_date}"
---

# {title}

{body}
"""
    origin_path.write_text(content, encoding="utf-8")
    return origin_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && .venv/bin/pytest tests/test_markdown.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/markdown.py tools/browser-fetch-mcp/tests/test_markdown.py
git commit -m "feat(browser-fetch-mcp): add markdown.assemble_and_write article assembly module"
```

---

### Task 2: Wire `output_format` into `fetch_article`

**Files:**
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py:26-28` (imports), `:208-340` (`fetch_article` function)
- Test: `tools/browser-fetch-mcp/tests/test_fetch_article.py`

**Interfaces:**
- Consumes: `markdown.assemble_and_write(output_dir, url, title, author, publish_date, blocks, image_blocks) -> Path` from Task 1.
- Produces: `fetch_article(url: str, output_dir: str, chrome_profile: Optional[str] = None, output_format: str = "path") -> dict`. For `output_format="path"`: `{"origin_path": str, "title": str, "author": str, "publish_date": str, "site": str, "cookies_injected": int, "thin_retry_used": bool}`. For `output_format="json"`: `{"title": str, "author": str, "publish_date": str, "blocks": list[dict], "image_blocks": list[dict], "site": str, "cookies_injected": int, "thin_retry_used": bool}` — identical to the function's return shape before this task. Any other value raises `ValueError`.

- [ ] **Step 1: Modify the two existing real-network tests that assert on `blocks`**

In `tools/browser-fetch-mcp/tests/test_fetch_article.py`, replace `test_fetch_article_generic_real_network` with:

```python
async def test_fetch_article_generic_real_network(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://en.wikipedia.org/wiki/Model_Context_Protocol",
                output_dir=str(output_dir),
                output_format="json",
            )
    assert payload["site"] == "generic"
    assert len(payload["blocks"]) > 5
    assert "Model Context Protocol" in payload["title"]
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0
```

Replace `test_fetch_article_arxiv_real_network` with:

```python
async def test_fetch_article_arxiv_real_network(tmp_path):
    """Real arXiv HTML paper page. If this specific ID has been withdrawn
    or lacks an HTML render by the time this runs, swap in any current
    arxiv.org/html/<id> URL — check https://arxiv.org/list/cs.AI/recent."""
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://arxiv.org/html/2608.06020",
                output_dir=str(output_dir),
                output_format="json",
            )
    assert payload["site"] == "arxiv"
    assert len(payload["blocks"]) > 5
```

(Both changes are additive — only the `output_format="json"` kwarg is new — so existing assertions on `payload["blocks"]` continue to exercise the pre-change return shape unchanged.)

- [ ] **Step 2: Append two new tests to the end of the same file**

```python
async def test_fetch_article_default_output_format_writes_origin_path(tmp_path):
    """output_format defaults to 'path' — fetch_article must assemble and
    write Origin/article.md itself and return a slim metadata dict with
    no blocks/image_blocks keys."""
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
            )
    assert "blocks" not in payload
    assert "image_blocks" not in payload
    origin_path = Path(payload["origin_path"])
    assert origin_path.exists()
    assert origin_path.name == "article.md"
    assert origin_path.parent.name == "Origin"
    content = origin_path.read_text(encoding="utf-8")
    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "# Example Domain" in content


async def test_fetch_article_invalid_output_format_raises(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
                output_format="bogus",
            )
    assert result.is_error is True
    assert "Invalid output_format" in result.content[0].text
```

(`Path` is already imported at the top of this file — no new import needed.)

- [ ] **Step 3: Run the affected tests to verify they fail**

Run: `cd tools/browser-fetch-mcp && .venv/bin/pytest tests/test_fetch_article.py -v -k "generic_real_network or arxiv_real_network or output_format"`
Expected: FAIL — the two modified tests fail with a tool-call validation error (`output_format` isn't a recognized parameter yet), and the two new tests fail because `fetch_article` still returns `blocks`/`image_blocks` for every call and raises no `ValueError` for `output_format="bogus"`.

- [ ] **Step 4: Modify `server.py`'s imports**

At `tools/browser-fetch-mcp/browser_fetch_mcp/server.py:28`, change:

```python
from browser_fetch_mcp import config
```

to:

```python
from browser_fetch_mcp import config, markdown
```

- [ ] **Step 5: Replace the `fetch_article` function**

Replace the entire `fetch_article` function (`tools/browser-fetch-mcp/browser_fetch_mcp/server.py:208-340`, from `@mcp.tool()` through the final closing `}`) with:

```python
@mcp.tool()
async def fetch_article(
    url: str,
    output_dir: str,
    chrome_profile: Optional[str] = None,
    output_format: str = "path",
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
      <output_dir>/Origin/article.md, and returns {"origin_path", "title",
      "author", "publish_date", "site", "cookies_injected",
      "thin_retry_used"} — no blocks/image_blocks, keeping the payload out
      of the caller's context.
    - "json": returns the raw structured data instead — {"title", "author",
      "publish_date", "blocks", "image_blocks", "site", "cookies_injected",
      "thin_retry_used"} — no file is written.
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
            if site == "wechat":
                original_html = await page.content()
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

    title = result.get("title", "Untitled")
    author = result.get("author", "")
    blocks = [{"tag": b["tag"], "content": b["content"]} for b in result.get("blocks", [])]

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
    }
```

- [ ] **Step 6: Run the affected tests to verify they pass**

Run: `cd tools/browser-fetch-mcp && .venv/bin/pytest tests/test_fetch_article.py -v -k "generic_real_network or arxiv_real_network or output_format"`
Expected: PASS (4 passed)

- [ ] **Step 7: Run the full browser-fetch-mcp test suite to confirm no regressions**

Run: `cd tools/browser-fetch-mcp && .venv/bin/pytest tests/ -v`
Expected: PASS — every test in `tests/` (including Task 1's `test_markdown.py` and the untouched chrome-profile-default tests) passes.

- [ ] **Step 8: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch-mcp/tests/test_fetch_article.py
git commit -m "feat(browser-fetch-mcp): add output_format param to fetch_article, default to file-path output"
```

---

### Task 3: Shrink `mcp_fetch_client.py` to a thin wrapper

**Files:**
- Modify: `skills/research/extract-url-mcp/scripts/mcp_fetch_client.py` (full-file rewrite)
- Test: `skills/research/extract-url-mcp/tests/test_mcp_fetch_client.py` (unchanged — used as the regression check for this task)

**Interfaces:**
- Consumes: `fetch_article`'s `output_format="path"` default from Task 2 (relies on the default — never passes `output_format` explicitly), reading `payload["origin_path"]` from the MCP result.
- Produces: `fetch_and_save(url: str, output_dir: Path, chrome_profile: Optional[str] = None) -> Path` — same signature and same external behavior as before this task (writes the identical `article.md`/images, returns the identical `Path`), since Task 1 ported the assembly logic verbatim. `main()`'s CLI contract (`ORIGIN_PATH: <path>` on stdout) is unchanged.

- [ ] **Step 1: Replace the file**

Replace the entire contents of `skills/research/extract-url-mcp/scripts/mcp_fetch_client.py` with:

```python
#!/usr/bin/env python3
"""Stage 3 fetch script for extract-url-mcp: calls browser-fetch-mcp's
fetch_article (site-aware extraction: generic/wechat/arxiv/xcom), which
already assembles the Markdown Origin file itself (output_format defaults
to "path") and returns its path — this script's only remaining job is
computing the per-URL article directory and printing that path.

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
import os
import sys
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)


def _hash8(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()[:8]


async def fetch_and_save(url: str, output_dir: Path, chrome_profile: Optional[str] = None) -> Path:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )

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

    return Path(payload["origin_path"])


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
```

This removes `_format_block` and the `datetime`/`timedelta`/`timezone` import (both are now dead code — `markdown.py` owns that logic) and replaces the manual assembly block with `Path(payload["origin_path"])`.

- [ ] **Step 2: Run the existing extract-url-mcp test suite to confirm no regressions**

These tests were written against the old `fetch_and_save` and never mock `fetch_article` — they hit the real network and the real (now-modified) `browser-fetch-mcp` subprocess. Since Task 1 ported the assembly logic verbatim and Task 2's default `output_format="path"` reproduces the same file, these tests should pass unchanged with no edits — they now serve as an end-to-end regression proof that the port preserved behavior exactly.

Run: `python3 -m pytest skills/research/extract-url-mcp/tests/test_mcp_fetch_client.py -v`
Expected: PASS — all 4 tests (`test_fetch_and_save_writes_real_content`, `test_fetch_and_save_extracts_multiple_blocks_and_downloads_images`, `test_fetch_and_save_accepts_chrome_profile_without_crashing`, `test_fetch_and_save_image_placement_after_h1_dedup`) pass with no changes to the test file itself.

If any of these 4 tests fails, that is a real regression (the Markdown output differs from before this plan) — do not edit the test to make it pass; fix `markdown.py` or the `fetch_article` wiring instead.

- [ ] **Step 3: Commit**

```bash
git add skills/research/extract-url-mcp/scripts/mcp_fetch_client.py
git commit -m "refactor(extract-url-mcp): shrink mcp_fetch_client.py to a thin wrapper around fetch_article's path output"
```

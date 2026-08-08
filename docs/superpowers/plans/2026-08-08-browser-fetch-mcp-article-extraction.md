# browser-fetch-mcp: fetch_article (generic/wechat/arxiv extraction) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `fetch_article` tool to the `browser-fetch-mcp` MCP server that fetches a URL and returns structured, site-aware extracted content (title/author/publish_date/blocks/downloaded images) for generic web pages, WeChat official-account articles, and arXiv HTML papers — ported from `extract-url`'s three corresponding Playwright scripts.

**Architecture:** `fetch_article` reuses `fetch_page`'s existing warm persistent-context mechanism (`_get_context`) to navigate live to the URL, then runs a site-specific extraction JS (ported verbatim from `extract-url`) via `page.evaluate()` directly on that live page — not the two-hop "pre-fetch HTML → `page.set_content()` reconstruction" that the original scripts use. Site routing is exact-hostname Python matching, not LLM string matching. A thin-content auto-retry (cookie-injected re-navigation) and image download step round out the tool.

**Tech Stack:** Python 3.11+, Playwright async API, MCP SDK ≥2.0.0 (`MCPServer`), pytest + pytest-asyncio (`asyncio_mode = "auto"`).

## Global Constraints

- New tool signature: `fetch_article(url: str, output_dir: str, chrome_profile: Optional[str] = None) -> dict` in `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`. No `use_auth` parameter.
- Return shape (exact keys): `{"title": str, "author": str, "publish_date": str, "blocks": [{"tag": str, "content": str}], "image_blocks": [{"filename": str, "alt": str, "after_block": int}], "site": "generic"|"wechat"|"arxiv", "cookies_injected": int, "thin_retry_used": bool}`.
- Site dispatch is exact-hostname match (not substring) — see the routing table in Task 1. `x.com`/`www.x.com`/`twitter.com`/`www.twitter.com` raise `ValueError("X.com not supported yet")` immediately, before any browser context is touched.
- Extraction JS runs via `page.evaluate()` on the page from `page.goto(url, ...)` — never `page.set_content()` — reusing `fetch_page`'s exact fetch mechanism (`_get_context`, `ANON_KEY`, `_profile_key`).
- Thin-content threshold (unchanged from the original scripts): `len(blocks) < 20 or total_chars < 3000`.
- Thin retry only runs when `chrome_profile` is truthy; it reuses the existing cookie-injection code shape already in `fetch_page` (`extract_cookies` + `ctx.add_cookies`).
- `output_dir` is required; downloaded images go to `<output_dir>/Image/img_N.ext`. `fetch_article` never reads or writes `extract-url`'s `~/.hskill/url-extract/config.json`.
- `skills/research/extract-url/` is never modified by this plan — build-only, no consumer migration.
- No `dedup_check.py`/`repair_frontmatter`/`candidate_tags` logic is ported — those are Markdown-file-organization rules, out of scope for a fetch/extract tool.
- No new third-party dependencies. Image download uses stdlib `urllib.request` (blocking call inside an async function), matching the existing precedent in `cookies.py`'s `extract_cookies` (also a blocking call inside async `fetch_page`).

---

### Task 1: `extractors.py` — site dispatch, thin-content check, ported extraction JS

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/extractors.py`
- Test: `tools/browser-fetch-mcp/tests/test_extractors.py`

**Interfaces:**
- Consumes: nothing from other tasks (pure Python, stdlib only).
- Produces (used by Task 3):
  - `dispatch_site(url: str) -> str` — returns `"generic"`, `"wechat"`, or `"arxiv"`; raises `ValueError` for x.com/twitter.com hostnames.
  - `is_thin(result: dict) -> bool`
  - `extract_wechat_publish_date(html: str) -> str` — returns `"YYYY-MM-DD"` or `""`.
  - `EXTRACT_JS: dict[str, str]` — keys `"generic"`, `"wechat"`, `"arxiv"`, values are the three ported JS strings. Each JS block, when passed to `page.evaluate()`, returns a JS object with (at minimum) `title`, `blocks` (list of `{tag, content}`), `imageBlocks` (list of `{src, alt, afterBlock}`); `"generic"` and `"arxiv"` also return `author`/`publishDate`; `"wechat"` also returns `author` (no `publishDate` — computed separately via `extract_wechat_publish_date`).

- [ ] **Step 1: Write `extractors.py` with `dispatch_site` and `is_thin`**

```python
"""Site-specific HTML extraction: URL routing, thin-content detection, and
the in-browser extraction scripts ported from extract-url's
playwright_web.py / playwright_web_wechat.py / playwright_web_arxiv.py.

X.com/Twitter is deliberately excluded — it needs a headed-mode-first,
different-JS-on-headless-fallback browser lifecycle that conflicts with
the warm persistent-context model this server uses everywhere else. See
docs/superpowers/specs/2026-08-08-browser-fetch-mcp-article-extraction-design.md.
"""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

_XCOM_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}


def dispatch_site(url: str) -> str:
    """Return "generic", "wechat", or "arxiv" for the given URL's site.

    Raises ValueError for x.com/twitter.com — not supported yet.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in _XCOM_HOSTS:
        raise ValueError(f"X.com not supported yet: {url}")
    if hostname == "mp.weixin.qq.com":
        return "wechat"
    if hostname == "arxiv.org" and "/html/" in (parsed.path or ""):
        return "arxiv"
    return "generic"


def is_thin(result: dict) -> bool:
    """True if the extracted content looks too sparse to be the real
    article body (e.g. a paywall/login gate instead of the article)."""
    blocks = result.get("blocks", [])
    total_chars = sum(len(b["content"]) for b in blocks)
    return len(blocks) < 20 or total_chars < 3000


_CT_RE = re.compile(r'var\s+ct\s*=\s*["\'](\d+)["\']')


def extract_wechat_publish_date(html: str) -> str:
    """WeChat sets the publish date client-side from `var ct = "<unix ts>"`;
    it's never in the DOM (not even hidden), so pull it from raw HTML text."""
    match = _CT_RE.search(html)
    if not match:
        return ""
    return datetime.fromtimestamp(
        int(match.group(1)), tz=timezone(timedelta(hours=8))
    ).strftime("%Y-%m-%d")
```

- [ ] **Step 2: Append the three ported extraction JS blocks and the `EXTRACT_JS` dict**

Append to `extractors.py`:

```python
# Ported verbatim from extract-url/scripts/playwright_web.py (_EXTRACT_JS).
_EXTRACT_JS_GENERIC = r"""() => {
    const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE','BUTTON','FORM']);
    const contentUnits = [];
    const imageBlocks  = [];

    const titleEl   = document.querySelector('h1') || document.querySelector('title');
    const title     = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

    const dateMeta  = document.querySelector('meta[property="article:published_time"]')
                   || document.querySelector('meta[name="date"]')
                   || document.querySelector('time');
    const publishDate = dateMeta
        ? (dateMeta.getAttribute('content') || dateMeta.getAttribute('datetime') || '')
        : '';

    const authorMeta = document.querySelector('meta[name="author"]')
                    || document.querySelector('[rel="author"]');
    const author = authorMeta
        ? (authorMeta.getAttribute('content') || authorMeta.innerText || '').trim()
        : '';

    const main   = document.querySelector('main') || document.querySelector('article') || document.body;
    const walker = document.createTreeWalker(main, NodeFilter.SHOW_ELEMENT);
    let node;
    while (node = walker.nextNode()) {
        if (skipTags.has(node.tagName.toUpperCase())) continue;
        const tag = node.tagName.toUpperCase();

        if (tag === 'IMG') {
            const src = node.src || node.getAttribute('data-src') || '';
            if (src && !src.startsWith('data:') && src.startsWith('http')) {
                imageBlocks.push({src, alt: node.alt || '', afterBlock: contentUnits.length - 1});
            }
        } else if (['H1','H2','H3','P','LI','BLOCKQUOTE','PRE','CODE'].includes(tag)) {
            const t = node.innerText.replace(/\s+/g, ' ').trim();
            if (t && t.length > 10) {
                contentUnits.push({tag: tag.toLowerCase(), content: t});
            }
        }
    }

    return {title, author, publishDate, blocks: contentUnits, imageBlocks};
}"""

# Ported verbatim from extract-url/scripts/playwright_web_wechat.py (_EXTRACT_JS).
# Reads textContent (not innerText) because #js_content stays
# visibility:hidden in our headless context (WeChat's own unlock script
# never runs), and innerText on a hidden element returns "" in Chromium.
# Checks data-src before src because article images are lazy-loaded: the
# src DOM property resolves to the page's base URI (truthy) when the
# attribute is absent, short-circuiting a `src || data-src` fallback.
_EXTRACT_JS_WECHAT = r"""() => {
    const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE','BUTTON','FORM']);
    const contentUnits = [];
    const imageBlocks  = [];

    const titleEl = document.querySelector('#activity-name')
                 || document.querySelector('h1')
                 || document.querySelector('title');
    const title   = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

    const authorEl = document.querySelector('#js_name');
    const author    = authorEl ? authorEl.innerText.replace(/\s+/g, ' ').trim() : '';

    const main = document.querySelector('#js_content')
              || document.querySelector('main')
              || document.querySelector('article')
              || document.body;

    const walker = document.createTreeWalker(main, NodeFilter.SHOW_ELEMENT);
    let node;
    while (node = walker.nextNode()) {
        if (skipTags.has(node.tagName.toUpperCase())) continue;
        const tag = node.tagName.toUpperCase();

        if (tag === 'IMG') {
            const src = node.getAttribute('data-src') || node.src || '';
            if (src && !src.startsWith('data:') && src.startsWith('http')) {
                imageBlocks.push({src, alt: node.alt || '', afterBlock: contentUnits.length - 1});
            }
        } else if (['H1','H2','H3','P','LI','BLOCKQUOTE','PRE','CODE'].includes(tag)) {
            const t = node.textContent.replace(/\s+/g, ' ').trim();
            if (t && t.length > 10) {
                contentUnits.push({tag: tag.toLowerCase(), content: t});
            }
        }
    }

    return {title, author, blocks: contentUnits, imageBlocks};
}"""

# Ported verbatim from extract-url/scripts/playwright_web_arxiv.py (_EXTRACT_JS).
# The original script injects <base href="{url}"> before page.set_content()
# so relative image paths resolve against the real URL instead of
# about:blank. fetch_article navigates live via page.goto(url), so the
# page already has the real base URI — no <base> injection needed.
_EXTRACT_JS_ARXIV = r"""() => {
    const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE','BUTTON','FORM']);
    const contentUnits = [];
    const imageBlocks  = [];

    const titleEl   = document.querySelector('h1') || document.querySelector('title');
    const title     = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

    const dateMeta  = document.querySelector('meta[property="article:published_time"]')
                   || document.querySelector('meta[name="date"]')
                   || document.querySelector('time');
    const publishDate = dateMeta
        ? (dateMeta.getAttribute('content') || dateMeta.getAttribute('datetime') || '')
        : '';

    const authorMeta = document.querySelector('meta[name="author"]')
                    || document.querySelector('[rel="author"]');
    const author = authorMeta
        ? (authorMeta.getAttribute('content') || authorMeta.innerText || '').trim()
        : '';

    const main = document.querySelector('main') || document.querySelector('article') || document.body;

    function tableToMarkdown(table) {
        const rows = Array.from(table.querySelectorAll('tr'));
        if (!rows.length) return '';
        const grid = rows.map(tr =>
            Array.from(tr.querySelectorAll('th,td')).map(cell =>
                cell.innerText.replace(/\s+/g, ' ').trim().replace(/\|/g, '\\|')
            )
        );
        const nCols = Math.max(...grid.map(r => r.length));
        const pad = r => { while (r.length < nCols) r.push(''); return r; };
        const lines = [];
        lines.push('| ' + pad(grid[0]).join(' | ') + ' |');
        lines.push('| ' + Array(nCols).fill('---').join(' | ') + ' |');
        for (let i = 1; i < grid.length; i++) {
            lines.push('| ' + pad(grid[i]).join(' | ') + ' |');
        }
        return lines.join('\n');
    }

    // Only real data tables (ltx_tabular) — LaTeXML also renders block
    // equations as <table class="ltx_equation ltx_eqn_table">, skip those.
    const tables     = Array.from(main.querySelectorAll('table'));
    const tableSlots = new Map();
    for (const t of tables) {
        if (!/\bltx_tabular\b/.test(t.className)) continue;
        const md = tableToMarkdown(t);
        if (md) tableSlots.set(t, md);
    }

    const walker = document.createTreeWalker(main, NodeFilter.SHOW_ELEMENT);
    let node;
    while (node = walker.nextNode()) {
        const tag = node.tagName.toUpperCase();
        if (skipTags.has(tag)) continue;

        if (tag === 'TABLE' && tableSlots.has(node)) {
            contentUnits.push({tag: 'table', content: tableSlots.get(node)});
            continue;
        }

        const ownerTable = node.closest ? node.closest('table') : null;
        if (ownerTable && ownerTable !== node && tableSlots.has(ownerTable)) continue;

        if (tag === 'IMG') {
            const src = node.src || node.getAttribute('data-src') || '';
            if (src && !src.startsWith('data:') && src.startsWith('http')) {
                imageBlocks.push({src, alt: node.alt || '', afterBlock: contentUnits.length - 1});
            }
        } else if (['H1','H2','H3','P','LI','BLOCKQUOTE','PRE','CODE'].includes(tag)) {
            const t = node.innerText.replace(/\s+/g, ' ').trim();
            if (t && t.length > 10) {
                contentUnits.push({tag: tag.toLowerCase(), content: t});
            }
        }
    }

    return {title, author, publishDate, blocks: contentUnits, imageBlocks};
}"""

EXTRACT_JS = {
    "generic": _EXTRACT_JS_GENERIC,
    "wechat": _EXTRACT_JS_WECHAT,
    "arxiv": _EXTRACT_JS_ARXIV,
}
```

- [ ] **Step 3: Write the test file**

```python
import pytest

from browser_fetch_mcp.extractors import (
    EXTRACT_JS,
    dispatch_site,
    extract_wechat_publish_date,
    is_thin,
)


@pytest.mark.parametrize(
    "url,expected_site",
    [
        ("https://example.com/some-article", "generic"),
        ("https://blog.example.com/post/1", "generic"),
        ("https://mp.weixin.qq.com/s/abc123", "wechat"),
        ("https://arxiv.org/html/2312.11805", "arxiv"),
        ("https://arxiv.org/abs/2312.11805", "generic"),  # no /html/ in path
    ],
)
def test_dispatch_site_routes_by_hostname(url, expected_site):
    assert dispatch_site(url) == expected_site


@pytest.mark.parametrize(
    "url",
    [
        "https://x.com/someuser/status/123",
        "https://www.x.com/someuser/status/123",
        "https://twitter.com/someuser/status/123",
        "https://www.twitter.com/someuser/status/123",
    ],
)
def test_dispatch_site_rejects_x_dot_com(url):
    with pytest.raises(ValueError, match="X.com not supported"):
        dispatch_site(url)


def test_dispatch_site_rejects_only_exact_hostname_not_substring():
    """A lookalike hostname must not be misrouted to wechat's extractor —
    exact match only, no substring matching."""
    assert dispatch_site("https://notmp.weixin.qq.com.evil.com/s/abc") == "generic"


def test_is_thin_true_below_block_count_threshold():
    result = {"blocks": [{"tag": "p", "content": "x" * 500} for _ in range(19)]}
    assert is_thin(result) is True


def test_is_thin_false_at_block_count_threshold_with_enough_chars():
    result = {"blocks": [{"tag": "p", "content": "x" * 200} for _ in range(20)]}
    assert is_thin(result) is False


def test_is_thin_true_below_char_threshold_even_with_many_blocks():
    result = {"blocks": [{"tag": "p", "content": "x"} for _ in range(25)]}
    assert is_thin(result) is True


def test_extract_wechat_publish_date_parses_ct_variable():
    html = '<html><head><script>var ct = "1719763200";</script></head></html>'
    # 1719763200 -> 2024-07-01 in UTC+8
    assert extract_wechat_publish_date(html) == "2024-07-01"


def test_extract_wechat_publish_date_missing_returns_empty():
    assert extract_wechat_publish_date("<html></html>") == ""


def test_extract_js_dict_has_all_three_sites():
    assert set(EXTRACT_JS.keys()) == {"generic", "wechat", "arxiv"}
    for js in EXTRACT_JS.values():
        assert isinstance(js, str) and js.strip().startswith("()")
```

- [ ] **Step 4: Run the tests**

Run (from `tools/browser-fetch-mcp/`): `python3 -m pip install -q -e ".[dev]" && python3 -m pytest tests/test_extractors.py -v`. The `pip install -e ".[dev]"` is idempotent — safe to run every time; it installs this package plus `pytest`/`pytest-asyncio` into whatever Python is on `PATH`. This task's tests are pure Python and don't need Playwright/Chromium installed.
Expected: all tests PASS. None of these tests touch a browser or the network.

- [ ] **Step 5: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/extractors.py tools/browser-fetch-mcp/tests/test_extractors.py
git commit -m "feat(browser-fetch-mcp): add site dispatch and extraction JS module"
```

---

### Task 2: `images.py` — SSRF-safe image download

**Files:**
- Create: `tools/browser-fetch-mcp/browser_fetch_mcp/images.py`
- Test: `tools/browser-fetch-mcp/tests/test_images.py`

**Interfaces:**
- Consumes: nothing from Task 1 (independent, pure Python + stdlib networking).
- Produces (used by Task 3):
  - `is_safe_image_url(src: str) -> bool`
  - `infer_ext(url: str, content_type: str = "") -> str`
  - `download_images(image_blocks: list[dict], output_dir: "Path") -> list[dict]` — `image_blocks` items have `{"src": str, "alt": str, "afterBlock": int}` (this is the JS-side camelCase shape returned by `page.evaluate()`, i.e. the same shape as `EXTRACT_JS`'s `imageBlocks` output). Returns a list of `{"filename": str, "alt": str, "after_block": int}` — unsafe URLs are silently dropped from the result; failed downloads still get an entry (matches `extract-url`'s three scripts, which never let one bad image abort the whole fetch).

- [ ] **Step 1: Write `images.py`**

```python
"""Image download for fetch_article: SSRF-safe URL check, extension
inference, and the download loop. Ported from extract-url's
playwright_web.py / playwright_web_wechat.py / playwright_web_arxiv.py,
which all carry an identical copy of this logic.
"""
import ipaddress
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


def is_safe_image_url(src: str) -> bool:
    """Block file://, non-HTTP schemes, and private/loopback/link-local
    IPs (SSRF prevention)."""
    parsed = urlparse(src)
    if parsed.scheme not in ("http", "https"):
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except (ValueError, TypeError):
        pass  # hostname, not a bare IP — allow
    return True


_EXT_MAP = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


def infer_ext(url: str, content_type: str = "") -> str:
    """Guess a file extension from the URL or an explicit Content-Type."""
    if content_type:
        return _EXT_MAP.get(content_type, ".jpg")
    url_lower = url.lower()
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        if ext in url_lower:
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download_images(image_blocks: list[dict], output_dir: Path) -> list[dict]:
    """Download each safe image in image_blocks to <output_dir>/Image/.

    Unsafe URLs are skipped entirely (not present in the result). A
    download failure still produces an entry with the intended filename —
    the caller can tell it failed by the file not existing on disk — so
    one bad image never aborts extraction of the rest of the article.
    """
    image_dir = Path(output_dir) / "Image"
    image_dir.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for i, img in enumerate(image_blocks):
        if not is_safe_image_url(img["src"]):
            continue
        ext = infer_ext(img["src"])
        filename = f"img_{i + 1}{ext}"
        fpath = image_dir / filename
        try:
            req = urllib.request.Request(img["src"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
            fpath.write_bytes(data)
        except Exception:
            pass
        downloaded.append(
            {"filename": filename, "alt": img.get("alt", ""), "after_block": img["afterBlock"]}
        )
    return downloaded
```

- [ ] **Step 2: Write the test file**

```python
from pathlib import Path

import pytest

from browser_fetch_mcp.images import download_images, infer_ext, is_safe_image_url


@pytest.mark.parametrize(
    "src,expected",
    [
        ("https://example.com/img.png", True),
        ("http://example.com/img.png", True),
        ("file:///etc/passwd", False),
        ("ftp://example.com/img.png", False),
        ("http://127.0.0.1/img.png", False),
        ("http://169.254.169.254/latest/meta-data/", False),
        ("http://10.0.0.5/img.png", False),
        ("http://not-an-ip-hostname.example.com/img.png", True),
    ],
)
def test_is_safe_image_url(src, expected):
    assert is_safe_image_url(src) is expected


def test_infer_ext_from_url_extension():
    assert infer_ext("https://example.com/photo.png") == ".png"
    assert infer_ext("https://example.com/photo.jpeg") == ".jpg"
    assert infer_ext("https://example.com/photo.webp") == ".webp"


def test_infer_ext_from_content_type_takes_priority():
    assert infer_ext("https://example.com/photo", content_type="image/png") == ".png"


def test_infer_ext_defaults_to_jpg():
    assert infer_ext("https://example.com/photo") == ".jpg"


def test_download_images_skips_unsafe_url(tmp_path):
    blocks = [{"src": "file:///etc/passwd", "alt": "bad", "afterBlock": 0}]
    result = download_images(blocks, tmp_path)
    assert result == []


def test_download_images_real_network(tmp_path):
    blocks = [
        {"src": "https://www.python.org/static/img/python-logo.png", "alt": "logo", "afterBlock": -1}
    ]
    result = download_images(blocks, tmp_path)
    assert len(result) == 1
    assert result[0]["filename"] == "img_1.png"
    assert result[0]["alt"] == "logo"
    assert result[0]["after_block"] == -1
    downloaded_file = Path(tmp_path) / "Image" / "img_1.png"
    assert downloaded_file.exists()
    assert downloaded_file.stat().st_size > 0


def test_download_images_failed_download_still_returns_entry(tmp_path):
    """urlopen() raises HTTPError for a 404 before any bytes are written,
    so the file never gets created — but the entry is still returned so
    the caller can see which image failed."""
    blocks = [{"src": "https://example.com/definitely-does-not-exist-404.png", "alt": "", "afterBlock": 0}]
    result = download_images(blocks, tmp_path)
    assert len(result) == 1
    assert result[0]["filename"] == "img_1.png"
    assert not (Path(tmp_path) / "Image" / "img_1.png").exists()
```

- [ ] **Step 3: Run the tests**

Run (from `tools/browser-fetch-mcp/`): `python3 -m pip install -q -e ".[dev]" && python3 -m pytest tests/test_images.py -v` (needs real network access for `test_download_images_real_network`; the `pip install` line is idempotent, safe even if Task 1 already ran it).
Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/images.py tools/browser-fetch-mcp/tests/test_images.py
git commit -m "feat(browser-fetch-mcp): add SSRF-safe image download module"
```

---

### Task 3: Wire `fetch_article` into `server.py`

**Files:**
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`
- Test: `tools/browser-fetch-mcp/tests/test_fetch_article.py`

**Interfaces:**
- Consumes:
  - From Task 1: `dispatch_site(url) -> str`, `is_thin(result) -> bool`, `extract_wechat_publish_date(html) -> str`, `EXTRACT_JS: dict[str, str]`.
  - From Task 2: `download_images(image_blocks, output_dir) -> list[dict]`.
  - Existing in `server.py`: `_get_context(key) -> BrowserContext`, `_profile_key(chrome_profile) -> str`, `ANON_KEY`, `extract_cookies(url, chrome_profile) -> dict[str, str]` (imported from `browser_fetch_mcp.cookies`).
- Produces: `fetch_article` MCP tool, callable exactly like `fetch_page`.

- [ ] **Step 1: Update the module docstring and imports**

In `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`, replace lines 1-12:

```python
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
```

- [ ] **Step 2: Add the `fetch_article` tool**

Insert after `fetch_page`'s closing `return {...}` block (i.e. after the existing line `}` that ends `fetch_page`, before `def main():`):

```python
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
```

- [ ] **Step 3: Write the test file**

```python
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.async_api import async_playwright

from browser_fetch_mcp.extractors import EXTRACT_JS, extract_wechat_publish_date

SERVER_MODULE = "browser_fetch_mcp.server"


def _server_params(data_dir: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
    )


async def _call_fetch_article(session, **kwargs):
    result = await session.call_tool("fetch_article", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_article_generic_real_network(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://en.wikipedia.org/wiki/Model_Context_Protocol",
                output_dir=str(output_dir),
            )
    assert payload["site"] == "generic"
    assert len(payload["blocks"]) > 5
    assert "Model Context Protocol" in payload["title"]
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0


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
                url="https://arxiv.org/html/2312.11805",
                output_dir=str(output_dir),
            )
    assert payload["site"] == "arxiv"
    assert len(payload["blocks"]) > 5


async def test_fetch_article_x_dot_com_is_rejected(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
            )
    assert result.is_error is True


async def test_fetch_article_rejects_file_scheme(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="file:///etc/passwd",
                output_dir=str(output_dir),
            )
    assert result.is_error is True


async def test_fetch_article_thin_retry_triggers_with_chrome_profile_no_matching_cookies(tmp_path):
    """example.com is naturally thin (well under 20 blocks / 3000 chars).
    With an empty (non-real) chrome_profile dir, the retry attempt runs
    but finds no cookies, so cookies_injected stays 0 — this only checks
    that the retry path executes and doesn't crash, not that it recovers
    real content (that needs a real logged-in Chrome profile, out of
    scope for an automated test)."""
    empty_profile = tmp_path / "EmptyProfile"
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
                chrome_profile=str(empty_profile),
            )
    assert payload["thin_retry_used"] is True
    assert payload["cookies_injected"] == 0


async def _evaluate_extraction(site: str, html: str, tmp_path: Path) -> dict:
    """Test-only helper: load `html` via page.set_content() (NOT the
    production page.goto() path — this exists purely to feed a synthetic
    DOM into the extraction JS for fixture-based correctness testing) and
    run the site's extraction JS against it."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        result = await page.evaluate(EXTRACT_JS[site])
        await browser.close()
    return result


_WECHAT_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>WeChat Test Article</title>
  <script>var ct = "1719763200";</script>
</head>
<body>
  <h1 id="activity-name">WeChat Test Article</h1>
  <a id="js_name">Test Official Account</a>
  <div id="js_content" style="visibility: hidden; opacity: 0;">
    <p>First paragraph with sufficient content to be captured by the wechat extraction JS under test here.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test here.</p>
    <section><img data-src="https://mmbiz.qpic.cn/test/640?wx_fmt=png" alt="pic"></section>
  </div>
</body>
</html>
"""


async def test_extract_js_wechat_reads_hidden_content_via_fixture(tmp_path):
    result = await _evaluate_extraction("wechat", _WECHAT_FIXTURE_HTML, tmp_path)
    assert result["title"] == "WeChat Test Article"
    assert result["author"] == "Test Official Account"
    assert len(result["blocks"]) == 2
    assert "First paragraph" in result["blocks"][0]["content"]
    assert len(result["imageBlocks"]) == 1
    assert result["imageBlocks"][0]["src"] == "https://mmbiz.qpic.cn/test/640?wx_fmt=png"

    publish_date = extract_wechat_publish_date(_WECHAT_FIXTURE_HTML)
    assert publish_date == "2024-07-01"


_ARXIV_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Test Paper Title</title></head>
<body>
<main>
  <h1>Test Paper Title</h1>
  <p>This is the abstract paragraph with enough characters to pass the ten character minimum length check.</p>
  <table class="ltx_tabular">
    <tr><th>Metric</th><th>Score</th></tr>
    <tr><td>Accuracy</td><td>0.95</td></tr>
  </table>
  <table class="ltx_equation ltx_eqn_table">
    <tr><td>x = y + z</td></tr>
  </table>
</main>
</body>
</html>
"""


async def test_extract_js_arxiv_converts_data_table_but_skips_equation_table(tmp_path):
    result = await _evaluate_extraction("arxiv", _ARXIV_FIXTURE_HTML, tmp_path)
    assert result["title"] == "Test Paper Title"
    table_blocks = [b for b in result["blocks"] if b["tag"] == "table"]
    assert len(table_blocks) == 1
    assert "Accuracy" in table_blocks[0]["content"]
    assert "0.95" in table_blocks[0]["content"]
    assert "x = y + z" not in "".join(b["content"] for b in result["blocks"])
```

- [ ] **Step 4: Run the tests**

Run (from `tools/browser-fetch-mcp/`): `python3 -m pip install -q -e ".[dev]" && python3 -m playwright install chromium && python3 -m pytest tests/test_fetch_article.py -v` (needs real network access).
Expected: all tests PASS.

- [ ] **Step 5: Run the full test suite for the package**

Run (from `tools/browser-fetch-mcp/`): `python3 -m pytest -v`.
Expected: all tests (Tasks 1-3 plus the existing `test_cookies.py`/`test_server.py`) PASS.

- [ ] **Step 6: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch-mcp/tests/test_fetch_article.py
git commit -m "feat(browser-fetch-mcp): add fetch_article tool (generic/wechat/arxiv)"
```

---

## Post-plan verification

- [ ] Run `npm test` from the repo root — confirms this branch doesn't break the repo-wide skill/hskill test suite.
- [ ] Confirm `skills/research/extract-url/` has zero diff against `staging` (`git diff staging -- skills/research/extract-url/` produces no output) — the Global Constraint that this plan never touches `extract-url`.

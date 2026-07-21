#!/usr/bin/env python3
"""
Playwright scraper for WeChat official-account articles (mp.weixin.qq.com).
Usage: python playwright_web_wechat.py <url> <html_path>
  html_path: path to pre-fetched HTML file (e.g. /tmp/fetched_page.html)
Reads VAULT_PATH and CHROME_PROFILE from ~/.hskill/url-extract/config.json
Stdout: "ORIGIN_PATH: <path>" on success

Fork of playwright_web.py with three WeChat-specific fixes:
1. WeChat wraps the article body in <div id="js_content" style="visibility:
   hidden; opacity: 0;">. The visibility only flips to visible after WeChat's
   own unlock script runs (requires the real WeChat client environment), which
   never happens in our headless context. `.innerText` on a hidden element
   returns "" in Chromium, so the generic script's TreeWalker sees an empty
   article. This fork reads `.textContent` instead, which ignores visibility.
2. Article images are lazy-loaded: the <img> `src` attribute is absent (so
   the DOM property resolves to the page's base URI, e.g. "about:blank",
   which is truthy and short-circuits the generic script's `src ||
   data-src` fallback). The real URL lives in `data-src`. This fork checks
   `data-src` first.
3. Title/author come from WeChat-specific elements (#activity-name,
   #js_name) instead of generic <h1>/meta selectors. Publish date isn't in
   the DOM at all — WeChat sets it client-side from a `var ct = "<unix ts>"`
   script variable — so this fork extracts `ct` from the raw HTML with regex.

If the pre-fetched HTML yields thin content (<20 blocks or <3000 chars), the
script automatically retries by navigating directly with Chrome cookies injected
(same mechanism as playwright_xcom.py). Useful for paywalled / login-gated sites.
"""
import re
import sys, os, ipaddress
from urllib.parse import urlparse
from pathlib import Path

# --- Security: validate URL scheme FIRST, before any heavy imports ---
url       = sys.argv[1]
html_path = sys.argv[2]

_parsed = urlparse(url)
if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
    print(f"ERROR: Rejected URL with scheme '{_parsed.scheme}' — only http/https allowed", file=sys.stderr)
    sys.exit(1)

# --- Config (after security check) ---
sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_chrome_profile, get_article_paths
vault_path = get_vault_path()
skill_dir  = str(Path(__file__).parent.parent)

import urllib.request, shutil, tempfile
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import infer_ext, format_block, repair_frontmatter, record_fetch_issues


def _is_safe_image_url(src):
    """Block file://, non-HTTP schemes, and private/loopback IPs (SSRF prevention)."""
    p = urlparse(src)
    if p.scheme not in ('http', 'https'):
        return False
    try:
        ip = ipaddress.ip_address(p.hostname)
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False
    except (ValueError, TypeError):
        pass
    return True


_EXTRACT_JS = r"""() => {
    const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE','BUTTON','FORM']);
    const contentUnits = [];
    const imageBlocks  = [];

    const titleEl = document.querySelector('#activity-name')
                 || document.querySelector('h1')
                 || document.querySelector('title');
    const title   = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

    const authorEl = document.querySelector('#js_name');
    const author    = authorEl ? authorEl.innerText.replace(/\s+/g, ' ').trim() : '';

    // #js_content is server-rendered but sits behind visibility:hidden until
    // WeChat's client-side unlock script runs (never happens here), so we
    // read via textContent below instead of innerText.
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
            // Real URL lives in data-src (lazy-load); src attribute is
            // usually absent, so the src *property* would otherwise resolve
            // to the page's base URI instead of falling through.
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


def _is_thin(result):
    blocks = result.get('blocks', [])
    total_chars = sum(len(b['content']) for b in blocks)
    return len(blocks) < 20 or total_chars < 3000


def _fetch_with_cookies(url):
    """Navigate directly to URL with Chrome profile cookies. Returns extracted result or None."""
    try:
        import pycookiecheat
        chrome_profile = get_chrome_profile()
        cookie_origin  = f"{_parsed.scheme}://{_parsed.netloc}"
        tmp = tempfile.mktemp(suffix='.db')
        shutil.copy2(str(Path(chrome_profile) / 'Cookies'), tmp)
        cookies_dict = pycookiecheat.chrome_cookies(cookie_origin, cookie_file=tmp)
        Path(tmp).unlink(missing_ok=True)
        if not cookies_dict:
            return None
        pw_cookies = [
            {'name': k, 'value': v, 'domain': _parsed.netloc, 'path': '/'}
            for k, v in cookies_dict.items()
        ]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
            )
            ctx.add_cookies(pw_cookies)
            page = ctx.new_page()
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(3000)
            result = page.evaluate(_EXTRACT_JS)
            browser.close()
        return result
    except Exception as e:
        print(f"Chrome cookie 重试失败（忽略）: {e}", file=sys.stderr)
        return None


# --- Load HTML and extract content ---
with open(html_path, encoding='utf-8', errors='replace') as f:
    html = f.read()

# WeChat sets the publish date client-side from `var ct = "<unix ts>"`;
# it's never in the DOM (not even hidden), so pull it straight from the
# raw HTML instead of via page.evaluate.
publish_date = ''
_ct_match = re.search(r'var\s+ct\s*=\s*["\'](\d+)["\']', html)
if _ct_match:
    publish_date = datetime.fromtimestamp(
        int(_ct_match.group(1)), tz=timezone(timedelta(hours=8))
    ).strftime('%Y-%m-%d')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page    = browser.new_page()
    page.set_content(html, wait_until='domcontentloaded')
    result  = page.evaluate(_EXTRACT_JS)
    browser.close()

if _is_thin(result):
    print(f"内容偏少（{len(result.get('blocks',[]))} blocks），尝试用 Chrome cookies 重抓…", file=sys.stderr)
    retried = _fetch_with_cookies(url)
    if retried and len(retried.get('blocks', [])) > len(result.get('blocks', [])):
        result = retried
        print(f"Cookie 重试成功，获得 {len(result['blocks'])} blocks", file=sys.stderr)

title = result.get('title', 'Untitled')
paths = get_article_paths(url, title)
image_dir   = paths['image_dir']
origin_dir  = paths['origin_dir']
origin_path = paths['origin_path']
os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)

# --- Download images ---
downloaded = []
for i, img in enumerate(result.get('imageBlocks', [])):
    if not _is_safe_image_url(img['src']):
        print(f"  [{i+1}] Skipped unsafe image URL: {img['src'][:80]}")
        continue
    ext   = infer_ext(img['src'])
    fname = f"img_{i+1}{ext}"
    fpath = os.path.join(image_dir, fname)
    try:
        req = urllib.request.Request(img['src'], headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        print(f"  [{i+1}] Downloaded {fname} ({len(data)} bytes)")
        downloaded.append({**img, 'filename': fname})
    except Exception as e:
        print(f"  [{i+1}] Failed: {e}")
        downloaded.append({**img, 'filename': fname})

# --- Build origin file ---
blocks     = result['blocks']
author     = result.get('author', '')
fetch_date = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

body_units = []
for i, block in enumerate(blocks):
    parts = [format_block(block)]
    for img in downloaded:
        if img.get('afterBlock') == i:
            parts.append(f'![](../Image/{img["filename"]})')
    body_units.append('\n'.join(parts))

body = '\n\n'.join(body_units)

origin_content = f"""---
publish_date: {publish_date}
fetch_date: {fetch_date}
author: {author}
source_url: {url}
origin_title: "{title}"
---

# {title}

{body}
"""

with open(origin_path, 'w', encoding='utf-8') as f:
    f.write(origin_content)

# --- Validate ---
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date}, skip_remaining_fields={'description'})
if remaining:
    record_fetch_issues('; '.join(remaining), paths['article_dir'])
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_fetch_issues('', paths['article_dir'])

print(f"ORIGIN_PATH: {origin_path}")
print(f"抓取完成：{title} ({len(blocks)} blocks, {len(downloaded)} images)")

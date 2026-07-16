#!/usr/bin/env python3
"""
Playwright scraper for arXiv HTML paper pages (e.g. https://arxiv.org/html/<id>).
Usage: python playwright_web_arxiv.py <url> <html_path>
  html_path: path to pre-fetched HTML file (e.g. /tmp/fetched_page.html)
Reads VAULT_PATH and CHROME_PROFILE from ~/.hskill/url-extract/config.json
Stdout: "ORIGIN_PATH: <path>" on success

Fork of playwright_web.py with two arXiv-specific fixes:
1. Injects <base href="{url}"> before loading the HTML so relative image
   paths (arXiv HTML papers reference figures as e.g. "2607.01233v1/x1.png")
   resolve to real absolute URLs instead of about:blank-based ones.
2. Extracts <table class="ltx_tabular ...">  (real data tables) into Markdown
   pipe tables. LaTeXML also renders block equations as <table class="ltx_equation
   ltx_eqn_table">, which are excluded since they aren't tabular data.

If the pre-fetched HTML yields thin content (<20 blocks or <3000 chars), the
script automatically retries by navigating directly with Chrome cookies injected
(same mechanism as playwright_xcom.py). Useful for paywalled / login-gated sites.
"""
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
from article_utils import infer_ext, format_block, repair_frontmatter, record_issues


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

        // Skip content inside an already-captured table (but not the table
        // node itself — closest('table') matches self too) to avoid
        // duplicating cell text as loose <p>/<li> blocks.
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


db_path = os.path.join(vault_path, 'url-index.db')

# --- Load HTML and extract content ---
with open(html_path, encoding='utf-8', errors='replace') as f:
    html = f.read()

# Inject <base> so relative image URLs resolve against the real page URL
# instead of about:blank (page.set_content has no base URL by default).
base_tag = f'<base href="{url}">'
if '<head>' in html:
    html = html.replace('<head>', f'<head>{base_tag}', 1)
else:
    html = base_tag + html

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
blocks       = result['blocks']
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

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
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date})
if remaining:
    record_issues(url, '; '.join(remaining), db_path)
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_issues(url, '', db_path)

print(f"ORIGIN_PATH: {origin_path}")
print(f"抓取完成：{title} ({len(blocks)} blocks, {len(downloaded)} images)")

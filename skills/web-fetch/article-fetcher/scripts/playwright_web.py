#!/usr/bin/env python3
"""
Playwright scraper for general websites.
Usage: python playwright_web.py <url> <html_path> <vault_path> <skill_dir>
  html_path: path to pre-fetched HTML file (e.g. /tmp/fetched_page.html)
Stdout: "ORIGIN_PATH: <path>" on success
"""
import sys, os, urllib.request, hashlib, ipaddress
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

url        = sys.argv[1]
html_path  = sys.argv[2]
vault_path = sys.argv[3]
skill_dir  = sys.argv[4]

# --- Security: validate URL scheme ---
_parsed = urlparse(url)
if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
    print(f"ERROR: Rejected URL with scheme '{_parsed.scheme}' — only http/https allowed", file=sys.stderr)
    sys.exit(1)

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import infer_ext, format_block, sanitize_filename, repair_frontmatter, record_issues


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


url_hash   = hashlib.md5(url.encode()).hexdigest()[:8]
image_dir  = os.path.join(vault_path, 'Image')
origin_dir = os.path.join(vault_path, 'Origin')
db_path    = os.path.join(vault_path, 'url-index.db')

os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)

# --- Load HTML and extract content ---
with open(html_path, encoding='utf-8', errors='replace') as f:
    html = f.read()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page    = browser.new_page()
    page.set_content(html, wait_until='domcontentloaded')

    result = page.evaluate(r"""() => {
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
    }""")
    browser.close()

# --- Download images ---
downloaded = []
for i, img in enumerate(result.get('imageBlocks', [])):
    if not _is_safe_image_url(img['src']):
        print(f"  [{i+1}] Skipped unsafe image URL: {img['src'][:80]}")
        continue
    ext   = infer_ext(img['src'])
    fname = f"{url_hash}_img_{i+1}{ext}"
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
title        = result.get('title', 'Untitled')
author       = result.get('author', '')
publish_date = (result.get('publishDate') or '')[:10]
fetch_date   = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')

origin_filename = sanitize_filename(title) + '.md'
origin_path     = os.path.join(origin_dir, origin_filename)

body_units = []
for i, block in enumerate(blocks):
    parts = [format_block(block)]
    for img in downloaded:
        if img.get('afterBlock') == i:
            parts.append(f'![](Image/{img["filename"]})')
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

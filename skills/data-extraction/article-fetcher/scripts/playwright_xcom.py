#!/usr/bin/env python3
"""
Playwright scraper for X.com (Twitter) articles.
Usage: python playwright_xcom.py <url> <vault_path> <skill_dir>
Stdout: "ORIGIN_PATH: <path>" on success
"""
import sys, os, ipaddress
from urllib.parse import urlparse

# --- Security: validate URL scheme FIRST, before any heavy imports ---
url        = sys.argv[1]
vault_path = sys.argv[2]
skill_dir  = sys.argv[3]

_parsed = urlparse(url)
if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
    print(f"ERROR: Rejected URL with scheme '{_parsed.scheme}' — only http/https allowed", file=sys.stderr)
    sys.exit(1)

import json, urllib.request, hashlib
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(skill_dir, 'references'))
from article_utils import infer_ext, format_block, sanitize_filename, repair_frontmatter, record_issues

chrome_profile = os.path.expanduser('~/Library/Application Support/Google/Chrome/Profile 2')
url_hash   = hashlib.md5(url.encode()).hexdigest()[:8]
image_dir  = os.path.join(vault_path, 'Image')
origin_dir = os.path.join(vault_path, 'Origin')
db_path    = os.path.join(vault_path, 'url-index.db')

os.makedirs(image_dir, exist_ok=True)
os.makedirs(origin_dir, exist_ok=True)


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
        pass  # hostname, not a bare IP — allow
    return True


# --- Scrape ---
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(user_data_dir=chrome_profile, headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
    page.goto(url, timeout=30000)
    page.wait_for_timeout(8000)

    result = page.evaluate(r"""() => {
        const article = document.querySelector('article[data-testid="tweet"]');
        if (!article) return {error: 'No article found'};

        const titleEl = article.querySelector('[data-testid="twitter-article-title"]');
        const title = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

        const timeEl = article.querySelector('article time');
        const publishDate = timeEl ? timeEl.getAttribute('datetime') : '';

        const authorEl = article.querySelector('[data-testid="User-Name"]');
        let author = '';
        if (authorEl) {
            const authorText = authorEl.innerText.replace(/\s+/g, ' ').trim();
            author = authorText.split('@')[0].trim();
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        let lastText = '';

        const walker = document.createTreeWalker(article, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (tag === 'DIV' && tid === 'tweetPhoto') {
                const img = node.querySelector('img');
                if (img && img.src && !img.src.includes('data:') && !img.src.includes('/profile_images/')) {
                    contentUnits.push({type: 'image', src: img.src, alt: img.alt || ''});
                }
            } else if (tag === 'SPAN' && tid === '') {
                let directText = '';
                for (const cn of node.childNodes) {
                    if (cn.nodeType === Node.TEXT_NODE) {
                        directText += (cn.textContent || '').replace(/\s+/g, ' ').trim() + ' ';
                    }
                }
                directText = directText.trim();
                let hasLiAncestor = false;
                let ancestor = node.parentElement;
                while (ancestor && ancestor.tagName) {
                    if (['LI','OL','UL'].includes(ancestor.tagName.toUpperCase())) {
                        hasLiAncestor = true;
                        break;
                    }
                    ancestor = ancestor.parentElement;
                }
                if (hasLiAncestor) continue;
                const isNoise = (
                    directText.length < 30 ||
                    /^[@#]?[\d.]+[KMB]?$/i.test(directText) ||
                    directText.startsWith('@')
                );
                const isSubset = lastText.length > 10 && (lastText.includes(directText) || directText.includes(lastText));
                if (!isNoise && !isSubset && directText.length >= 30) {
                    contentUnits.push({type: 'text', tag: 'span', content: directText});
                    lastText = directText;
                }
            } else if (['H2','H3','P','LI','BLOCKQUOTE','PRE'].includes(tag)) {
                const t = node.innerText.replace(/\s+/g, ' ').trim();
                if (t && t.length > 5) {
                    contentUnits.push({type: 'text', tag: tag.toLowerCase(), content: t});
                    lastText = t;
                }
            }
        }

        const blocks = [];
        const imageBlocks = [];
        for (let i = 0; i < contentUnits.length; i++) {
            const unit = contentUnits[i];
            if (unit.type === 'text') {
                blocks.push({
                    type: ['H2','H3'].includes(unit.tag.toUpperCase()) ? 'heading' : 'block',
                    tag: unit.tag,
                    content: unit.content,
                    blockIndex: blocks.length
                });
            } else if (unit.type === 'image') {
                imageBlocks.push({src: unit.src, alt: unit.alt, afterBlock: blocks.length - 1});
            }
        }

        return {title, author, publishDate, blocks, imageBlocks,
                totalTextBlocks: blocks.length, totalImages: imageBlocks.length};
    }""")

    result['publishDate'] = result.get('publishDate', '')
    ctx.close()

if result.get('error'):
    print(f"ERROR: {result['error']}", file=sys.stderr)
    sys.exit(1)

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
        req = urllib.request.Request(img['src'], headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/*'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
        with open(fpath, 'wb') as f:
            f.write(data)
        print(f"  [{i+1}] Downloaded {fname} ({len(data)} bytes)")
        downloaded.append({**img, 'filename': fname})
    except Exception as e:
        print(f"  [{i+1}] Failed {fname}: {e}")
        downloaded.append({**img, 'filename': fname})

# --- Build origin file ---
blocks       = result['blocks']
title        = result.get('title', 'Untitled')
author       = result.get('author', '')
publish_date = result.get('publishDate', '')[:10]
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

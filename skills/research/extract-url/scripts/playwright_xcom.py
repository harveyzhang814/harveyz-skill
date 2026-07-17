#!/usr/bin/env python3
"""
Playwright scraper for X.com (Twitter) articles.
Usage: python playwright_xcom.py <url>
Reads VAULT_PATH and CHROME_PROFILE from ~/.hskill/url-extract/config.json
Stdout: "ORIGIN_PATH: <path>" on success
"""
import sys, os, ipaddress
from urllib.parse import urlparse

# --- Security: validate URL scheme FIRST, before any heavy imports ---
url = sys.argv[1]

_parsed = urlparse(url)
if _parsed.scheme not in ('http', 'https') or not _parsed.netloc:
    print(f"ERROR: Rejected URL with scheme '{_parsed.scheme}' — only http/https allowed", file=sys.stderr)
    sys.exit(1)

# --- Config (after security check) ---
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from config import get_vault_path, get_chrome_profile, get_article_paths
vault_path     = get_vault_path()
chrome_profile = get_chrome_profile()
skill_dir      = str(Path(__file__).parent.parent)

import json, urllib.request, urllib.error, ssl, shutil, tempfile
import certifi
from datetime import datetime, timezone, timedelta
from playwright.sync_api import sync_playwright
import pycookiecheat

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
        pass  # hostname, not a bare IP — allow
    return True


# --- Extract cookies from Chrome profile (works even when Chrome is running) ---
_cookies_src = Path(chrome_profile) / 'Cookies'
with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as _f:
    _tmp_cookies = _f.name
shutil.copy2(_cookies_src, _tmp_cookies)
try:
    _cookies_dict = pycookiecheat.chrome_cookies('https://x.com', cookie_file=_tmp_cookies)
finally:
    os.unlink(_tmp_cookies)

_pw_cookies = [
    {'name': k, 'value': v, 'domain': '.x.com', 'path': '/', 'secure': True}
    for k, v in _cookies_dict.items()
]

# --- Scrape ---
# JS used in headed mode: SPAN threshold 3, CODE handler, PRE preserves whitespace,
# plus querySelectorAll fallback to catch Draft.js atomic code blocks.
_EXTRACT_JS_HEADED = r"""() => {
        const article = document.querySelector('article[data-testid="tweet"]');
        if (!article) return {error: 'No article found'};

        // X Notes: rich text body lives outside the tweet wrapper — use it as content root
        const richTextView = document.querySelector('[data-testid="twitterArticleRichTextView"]');
        const contentRoot = richTextView || article;

        // Title: explicit title element first, then H1 inside rich text view
        const titleEl = article.querySelector('[data-testid="twitter-article-title"]')
            || (richTextView ? richTextView.querySelector('h1') : null);
        const title = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

        // Author and date always from the outer tweet wrapper (not the notes body)
        const timeEl = article.querySelector('time');
        const publishDate = timeEl ? timeEl.getAttribute('datetime') : '';

        const authorEl = article.querySelector('[data-testid="User-Name"]');
        let author = '';
        if (authorEl) {
            const authorText = authorEl.innerText.replace(/\s+/g, ' ').trim();
            author = authorText.split('@')[0].trim();
        }

        // Skip nodes that are inside a nested embedded tweet article (quoted tweets)
        function insideNestedTweet(node) {
            let el = node.parentElement;
            while (el && el !== contentRoot) {
                if (el.tagName === 'ARTICLE' && el.getAttribute('data-testid') === 'tweet') return true;
                el = el.parentElement;
            }
            return false;
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        let lastText = '';

        const walker = document.createTreeWalker(contentRoot, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            if (insideNestedTweet(node)) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (tag === 'DIV' && tid === 'tweetPhoto') {
                const img = node.querySelector('img');
                if (img && img.src && !img.src.includes('data:') && !img.src.includes('/profile_images/')) {
                    contentUnits.push({type: 'image', src: img.src, alt: img.alt || ''});
                }
            } else if (tag === 'IMG' && richTextView) {
                // X Notes inline images not wrapped in tweetPhoto divs (tweetPhoto imgs already captured above)
                if (!node.closest('div[data-testid="tweetPhoto"]')
                        && node.src && !node.src.includes('data:') && !node.src.includes('/profile_images/')
                        && !node.src.includes('/emoji/') && node.width > 50) {
                    contentUnits.push({type: 'image', src: node.src, alt: node.alt || ''});
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
                    directText.length < 3 ||
                    /^[@#]?[\d.]+[KMB]?$/i.test(directText) ||
                    directText.startsWith('@')
                );
                const isSubset = lastText.length > 10 && (lastText.includes(directText) || directText.includes(lastText));
                if (!isNoise && !isSubset && directText.length >= 3) {
                    contentUnits.push({type: 'text', tag: 'span', content: directText});
                    lastText = directText;
                }
            } else if (tag === 'CODE') {
                // Standalone <code> not inside <pre> → inline code snippet
                let insidePre = false;
                let p = node.parentElement;
                while (p) { if (p.tagName === 'PRE') { insidePre = true; break; } p = p.parentElement; }
                if (!insidePre) {
                    const t = node.innerText.trim();
                    if (t && !lastText.includes(t)) {
                        contentUnits.push({type: 'text', tag: 'code', content: t});
                        lastText = t;
                    }
                }
            } else if (tag === 'PRE') {
                // Preserve whitespace in code blocks — do NOT collapse
                const t = node.innerText;
                if (t && t.trim().length > 5) {
                    contentUnits.push({type: 'text', tag: 'pre', content: t});
                    lastText = t.trim();
                }
            } else if (['H2','H3','P','LI','BLOCKQUOTE'].includes(tag)) {
                const t = node.innerText.replace(/\s+/g, ' ').trim();
                if (t && t.length > 5) {
                    contentUnits.push({type: 'text', tag: tag.toLowerCase(), content: t});
                    lastText = t;
                }
            }
        }

        // Collect code block keys already captured via tree walker
        const capturedCodeTexts = new Set(
            contentUnits.filter(u => u.tag === 'pre' || u.tag === 'code')
                        .map(u => u.content.trim().substring(0, 50))
        );

        // Direct fallback: query code.language-text (Draft.js atomic render)
        // These are NOT visited reliably by the tree walker due to lazy rendering timing
        contentRoot.querySelectorAll('code.language-text, pre').forEach(el => {
            const t = el.innerText;
            if (t && t.trim().length > 5) {
                const key = t.trim().substring(0, 50);
                if (!capturedCodeTexts.has(key)) {
                    capturedCodeTexts.add(key);
                    const tag = el.tagName === 'PRE' ? 'pre' : 'pre'; // treat both as pre
                    contentUnits.push({type: 'text', tag, content: t});
                }
            }
        });

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
}"""

# JS used in headless fallback: exact HEAD version — SPAN threshold 30, no CODE handler,
# PRE folds whitespace, no querySelectorAll patch.
_EXTRACT_JS_HEADLESS = r"""() => {
        const article = document.querySelector('article[data-testid="tweet"]');
        if (!article) return {error: 'No article found'};

        // X Notes: rich text body lives outside the tweet wrapper — use it as content root
        const richTextView = document.querySelector('[data-testid="twitterArticleRichTextView"]');
        const contentRoot = richTextView || article;

        const titleEl = article.querySelector('[data-testid="twitter-article-title"]')
            || (richTextView ? richTextView.querySelector('h1') : null);
        const title = titleEl ? titleEl.innerText.replace(/\s+/g, ' ').trim() : 'Untitled';

        const timeEl = article.querySelector('time');
        const publishDate = timeEl ? timeEl.getAttribute('datetime') : '';

        const authorEl = article.querySelector('[data-testid="User-Name"]');
        let author = '';
        if (authorEl) {
            const authorText = authorEl.innerText.replace(/\s+/g, ' ').trim();
            author = authorText.split('@')[0].trim();
        }

        function insideNestedTweet(node) {
            let el = node.parentElement;
            while (el && el !== contentRoot) {
                if (el.tagName === 'ARTICLE' && el.getAttribute('data-testid') === 'tweet') return true;
                el = el.parentElement;
            }
            return false;
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        let lastText = '';

        const walker = document.createTreeWalker(contentRoot, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            if (insideNestedTweet(node)) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (tag === 'DIV' && tid === 'tweetPhoto') {
                const img = node.querySelector('img');
                if (img && img.src && !img.src.includes('data:') && !img.src.includes('/profile_images/')) {
                    contentUnits.push({type: 'image', src: img.src, alt: img.alt || ''});
                }
            } else if (tag === 'IMG' && richTextView) {
                if (!node.closest('div[data-testid="tweetPhoto"]')
                        && node.src && !node.src.includes('data:') && !node.src.includes('/profile_images/')
                        && !node.src.includes('/emoji/') && node.width > 50) {
                    contentUnits.push({type: 'image', src: node.src, alt: node.alt || ''});
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
}"""


def _do_scrape(headless: bool) -> dict:
    with sync_playwright() as p:
        ctx_kwargs = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        }
        if not headless:
            ctx_kwargs['viewport'] = {'width': 1280, 'height': 900}

        browser = p.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        ctx  = browser.new_context(**ctx_kwargs)
        ctx.add_cookies(_pw_cookies)
        page = ctx.new_page()
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_selector('article[data-testid="tweet"]', timeout=60000)

        if not headless:
            # X Notes articles render content lazily; wait for the rich text view before extracting.
            is_x_notes = False
            try:
                page.wait_for_selector('[data-testid="twitterArticleRichTextView"]', timeout=70000)
                is_x_notes = True
            except Exception:
                pass  # not an X Notes article, proceed normally

            if is_x_notes:
                # Do NOT scroll for X Notes: scrolling unmounts richTextView from the virtual DOM
                # and causes reply articles to appear before the main tweet in DOM order.
                page.wait_for_timeout(2000)
            else:
                # Regular tweet: scroll to trigger Draft.js atomic block rendering
                for _i in range(25):
                    page.evaluate(f"window.scrollTo(0, {_i * 400})")
                    page.wait_for_timeout(200)
                try:
                    page.wait_for_selector('code.language-text, pre', timeout=8000)
                except Exception:
                    pass
                page.wait_for_timeout(1000)

        result = page.evaluate(_EXTRACT_JS_HEADLESS if headless else _EXTRACT_JS_HEADED)
        result['publishDate'] = result.get('publishDate', '')
        browser.close()
        return result


# Try headed first — renders Draft.js code blocks via real viewport.
# Fall back to headless if no display or browser fails (servers, cron, CI).
result = None
try:
    result = _do_scrape(headless=False)
except Exception as _e:
    print(f"Headed scrape failed ({_e}), falling back to headless", file=sys.stderr)
    result = _do_scrape(headless=True)

if result.get('error'):
    print(f"ERROR: {result['error']}", file=sys.stderr)
    sys.exit(1)

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
        req = urllib.request.Request(img['src'], headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'image/*'})
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        with urllib.request.urlopen(req, timeout=15, context=ssl_ctx) as resp:
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
author       = result.get('author', '')
publish_date = result.get('publishDate', '')[:10]
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
fm, fixed, remaining = repair_frontmatter(origin_path, url, {'fetch_date': fetch_date}, skip_remaining_fields={'description'})
if remaining:
    record_fetch_issues('; '.join(remaining), paths['article_dir'])
    print(f"警告：校验问题 {remaining}", file=sys.stderr)
else:
    record_fetch_issues('', paths['article_dir'])

print(f"ORIGIN_PATH: {origin_path}")
print(f"抓取完成：{title} ({len(blocks)} blocks, {len(downloaded)} images)")

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

EXTRACT_JS = {
    "generic": _EXTRACT_JS_GENERIC,
    "wechat": _EXTRACT_JS_WECHAT,
    "arxiv": _EXTRACT_JS_ARXIV,
}

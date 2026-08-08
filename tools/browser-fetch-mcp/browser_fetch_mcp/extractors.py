"""Site-specific HTML extraction: URL routing, thin-content detection, and
the in-browser extraction scripts ported from extract-url's
playwright_web.py / playwright_web_wechat.py / playwright_web_arxiv.py /
playwright_xcom.py.

X.com/Twitter's two extraction scripts (EXTRACT_JS_XCOM_HEADED /
EXTRACT_JS_XCOM_HEADLESS) live here, but the browser lifecycle that picks
between them — a one-off launch instead of the warm persistent context the
other three sites share — lives in server.py, since it needs a different
lifecycle than everything else this module's dispatch_site() routes to.
See docs/superpowers/specs/2026-08-08-browser-fetch-mcp-xcom-extraction-design.md.
"""
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

_XCOM_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}


def dispatch_site(url: str) -> str:
    """Return "generic", "wechat", "arxiv", or "xcom" for the given URL's site."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    if hostname in _XCOM_HOSTS:
        return "xcom"
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

# Ported verbatim from extract-url/scripts/playwright_xcom.py
# (_EXTRACT_JS_HEADED). JS used in headed mode: SPAN threshold 3, CODE
# handler, PRE preserves whitespace, plus querySelectorAll fallback to
# catch Draft.js atomic code blocks.
EXTRACT_JS_XCOM_HEADED = r"""() => {
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

        // X Articles/Notes render each paragraph as a Draft.js block div whose
        // children are per-style-run spans (a new sibling span starts wherever
        // bold toggles on/off). Without merging these runs, every bold word
        // becomes its own top-level paragraph and the bold styling is lost.
        function isDraftParagraphBlock(node) {
            return node.tagName === 'DIV' && node.classList
                && node.classList.contains('public-DraftStyleDefault-block');
        }

        function isBoldRun(span) {
            // Inline style only (X marks bold runs with style="font-weight: bold"
            // directly on the run) — NOT computed style, which would also pick up
            // ambient bold from a heading ancestor and false-positive every run.
            const w = span.style && span.style.fontWeight;
            return w === 'bold' || parseInt(w) >= 600;
        }

        function paragraphToInlineMarkdown(blockDiv) {
            let out = '';
            for (const run of blockDiv.children) {
                const text = (run.textContent || '').replace(/\s+/g, ' ');
                if (!text) continue;
                const trimmed = text.trim();
                if (isBoldRun(run) && trimmed) {
                    const lead = text.slice(0, text.indexOf(trimmed));
                    const trail = text.slice(text.indexOf(trimmed) + trimmed.length);
                    out += lead + '**' + trimmed + '**' + trail;
                } else {
                    out += text;
                }
            }
            return out.trim();
        }

        function isInsideProcessedParagraph(node, processed) {
            let el = node.parentElement;
            while (el && el !== contentRoot) {
                if (processed.has(el)) return true;
                el = el.parentElement;
            }
            return false;
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        const processedParagraphs = new Set();
        let lastText = '';

        const walker = document.createTreeWalker(contentRoot, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            if (insideNestedTweet(node)) continue;
            if (isInsideProcessedParagraph(node, processedParagraphs)) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (isDraftParagraphBlock(node)) {
                const md = paragraphToInlineMarkdown(node);
                if (md && md.length > 5) {
                    contentUnits.push({type: 'text', tag: 'p', content: md});
                    lastText = md;
                }
                processedParagraphs.add(node);
                continue;
            }

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
                // Mark processed so a nested Draft.js paragraph div (headings/
                // blockquotes wrap one internally) isn't ALSO captured below,
                // which would duplicate this element's text as an extra block.
                processedParagraphs.add(node);
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

# Ported verbatim from extract-url/scripts/playwright_xcom.py
# (_EXTRACT_JS_HEADLESS). JS used in headless fallback: exact HEAD
# version — SPAN threshold 30, no CODE handler, PRE folds whitespace,
# no querySelectorAll patch.
EXTRACT_JS_XCOM_HEADLESS = r"""() => {
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

        // X Articles/Notes render each paragraph as a Draft.js block div whose
        // children are per-style-run spans (a new sibling span starts wherever
        // bold toggles on/off). Without merging these runs, every bold word
        // becomes its own top-level paragraph and the bold styling is lost.
        function isDraftParagraphBlock(node) {
            return node.tagName === 'DIV' && node.classList
                && node.classList.contains('public-DraftStyleDefault-block');
        }

        function isBoldRun(span) {
            // Inline style only (X marks bold runs with style="font-weight: bold"
            // directly on the run) — NOT computed style, which would also pick up
            // ambient bold from a heading ancestor and false-positive every run.
            const w = span.style && span.style.fontWeight;
            return w === 'bold' || parseInt(w) >= 600;
        }

        function paragraphToInlineMarkdown(blockDiv) {
            let out = '';
            for (const run of blockDiv.children) {
                const text = (run.textContent || '').replace(/\s+/g, ' ');
                if (!text) continue;
                const trimmed = text.trim();
                if (isBoldRun(run) && trimmed) {
                    const lead = text.slice(0, text.indexOf(trimmed));
                    const trail = text.slice(text.indexOf(trimmed) + trimmed.length);
                    out += lead + '**' + trimmed + '**' + trail;
                } else {
                    out += text;
                }
            }
            return out.trim();
        }

        function isInsideProcessedParagraph(node, processed) {
            let el = node.parentElement;
            while (el && el !== contentRoot) {
                if (processed.has(el)) return true;
                el = el.parentElement;
            }
            return false;
        }

        const skipTags = new Set(['SCRIPT','STYLE','NAV','FOOTER','HEADER','ASIDE']);
        const contentUnits = [];
        const processedParagraphs = new Set();
        let lastText = '';

        const walker = document.createTreeWalker(contentRoot, NodeFilter.SHOW_ELEMENT);
        let node;
        while (node = walker.nextNode()) {
            if (skipTags.has(node.tagName.toUpperCase())) continue;
            if (insideNestedTweet(node)) continue;
            if (isInsideProcessedParagraph(node, processedParagraphs)) continue;
            const tag = node.tagName.toUpperCase();
            const tid = node.getAttribute('data-testid') || '';

            if (isDraftParagraphBlock(node)) {
                const md = paragraphToInlineMarkdown(node);
                if (md && md.length > 5) {
                    contentUnits.push({type: 'text', tag: 'p', content: md});
                    lastText = md;
                }
                processedParagraphs.add(node);
                continue;
            }

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
                // Mark processed so a nested Draft.js paragraph div (headings/
                // blockquotes wrap one internally) isn't ALSO captured below,
                // which would duplicate this element's text as an extra block.
                processedParagraphs.add(node);
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

# browser-fetch-mcp: X.com/Twitter Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `fetch_article` support x.com/twitter.com URLs by porting `extract-url`'s `playwright_xcom.py` (headed-mode-first, headless-fallback, two different extraction scripts) into `browser-fetch-mcp`, as an independent browser lifecycle that coexists with the existing warm-context model used by the other three sites.

**Architecture:** `dispatch_site()` now routes x.com/twitter.com to `"xcom"` instead of raising. `fetch_article` branches early on `site == "xcom"`: instead of the shared warm persistent context, it does a one-off `browser.launch()` → use → `browser.close()` per call, trying headed mode first and falling back to headless (with a different extraction script) on any exception. The shared "assemble the return dict" tail (image download, block-shape normalization, publish_date branch) is reused unchanged across all four sites.

**Tech Stack:** Python 3.11+, Playwright async API, MCP SDK ≥2.0.0.

## Global Constraints

- `dispatch_site()` returns `"xcom"` for `x.com`/`www.x.com`/`twitter.com`/`www.twitter.com` (exact hostname match, same set already defined as `_XCOM_HOSTS`) instead of raising `ValueError`.
- The xcom branch requires `chrome_profile` — raises `ValueError` immediately if not given, before any browser is touched. x.com has no anonymous mode.
- xcom **never** uses `_get_context()` / the warm persistent context. Every call does its own `browser.launch()` → use → `browser.close()`, wrapped in `try/finally` so the browser always closes even on exception — this is a deliberate deviation from the original CLI script (which had no such guard, because the whole process exited right after each run; `browser-fetch-mcp` is long-lived, so an unguarded browser leak would accumulate zombie Chrome processes over the server's lifetime).
- Headed is attempted first (`headless=False`, `args=["--disable-blink-features=AutomationControlled"]`, `viewport={"width": 1280, "height": 900}`). On any exception, retry once with `headless=True` (no viewport override). Each mode uses its own extraction script — `EXTRACT_JS_XCOM_HEADED` / `EXTRACT_JS_XCOM_HEADLESS` — ported **verbatim** (including all comments) from `skills/research/extract-url/scripts/playwright_xcom.py`'s `_EXTRACT_JS_HEADED` / `_EXTRACT_JS_HEADLESS`.
- If both attempts raise, or the final result dict has an `"error"` key, raise `RuntimeError` with the failure detail.
- Cookie extraction and injection are hardcoded to x.com's origin/domain (`extract_cookies("https://x.com", chrome_profile)`, injected cookies use `"domain": ".x.com"`) regardless of whether the matched hostname was x.com or twitter.com — this matches `playwright_xcom.py`'s behavior exactly (it always reads x.com's stored cookies, since twitter.com redirects to x.com and Chrome stores the post-redirect session there).
- Return shape is unchanged: the same 8 keys (`title`/`author`/`publish_date`/`blocks`/`image_blocks`/`site`/`cookies_injected`/`thin_retry_used`) as the rest of `fetch_article`. `site` is `"xcom"`. `thin_retry_used` is always `False` for xcom (no thin-content-retry concept applies — x.com always fetches with cookies from the start). The extra fields xcom's JS returns (`totalTextBlocks`, `totalImages`, and each block's `type`/`blockIndex`) are dropped — the existing `{"tag": b["tag"], "content": b["content"]}` list comprehension already only reads `tag`/`content`, so no new code is needed to drop them.
- Reuse `browser_fetch_mcp.images.download_images()` unchanged for image downloading — no new image-handling code.
- No automated tests are written for this capability — headed mode needs a real display, which most automated test environments don't have. A documented manual verification checklist (Step in Task 1) is the completion gate instead of pytest, run by a human on a machine with a real GUI.
- `skills/research/extract-url/` must not be modified.
- `fetch_page` and the existing generic/wechat/arxiv code paths must keep their current behavior — this task only adds a new branch, it doesn't touch the existing warm-context logic.

---

### Task 1: Port xcom extraction into extractors.py and server.py

**Files:**
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/extractors.py`
- Modify: `tools/browser-fetch-mcp/browser_fetch_mcp/server.py`

**Interfaces:**
- Consumes: existing `extract_cookies(url, chrome_profile) -> dict[str, str]` (from `browser_fetch_mcp.cookies`, unchanged), existing `download_images(image_blocks, output_dir) -> list[dict]` (from `browser_fetch_mcp.images`, unchanged).
- Produces: `dispatch_site(url) -> str` now returns `"xcom"` for x.com/twitter.com hosts instead of raising. `EXTRACT_JS_XCOM_HEADED: str` and `EXTRACT_JS_XCOM_HEADLESS: str` (module-level constants in `extractors.py`, public — no leading underscore, since `server.py` imports them directly; unlike `EXTRACT_JS_GENERIC` etc., these are NOT added to the `EXTRACT_JS` dict, since that dict's contract is one JS string per site key and xcom needs two). `fetch_article` gains x.com/twitter.com support with no change to its public signature.

- [ ] **Step 1: Update `extractors.py`'s module docstring and `dispatch_site()`**

Replace the module docstring (lines 1-9) — the current one says X.com is "deliberately excluded"; that's no longer true:

```python
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
```

Replace `dispatch_site()` (currently raises `ValueError` for xcom hosts):

```python
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
```

- [ ] **Step 2: Append the two ported xcom extraction JS blocks to `extractors.py`**

Append after the existing `EXTRACT_JS = {...}` dict at the end of the file:

```python
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
```

- [ ] **Step 3: Verify the ported JS is byte-identical to the source**

Run these two diffs to confirm the JS payload (ignoring only the Python variable name/wrapper) matches `skills/research/extract-url/scripts/playwright_xcom.py` exactly — this is the exact mistake a previous round's plan made by hand-typing JS instead of copying it precisely, and it was caught in review, so verify it now instead of waiting for a reviewer to catch it again:

```bash
python3 -c "
import re
src = open('skills/research/extract-url/scripts/playwright_xcom.py').read()
new = open('tools/browser-fetch-mcp/browser_fetch_mcp/extractors.py').read()

def extract(text, marker):
    start = text.index(marker)
    start = text.index('r\"\"\"', start) + 4
    end = text.index('}\"\"\"', start) + 1
    return text[start:end]

src_headed = extract(src, '_EXTRACT_JS_HEADED = r')
new_headed = extract(new, 'EXTRACT_JS_XCOM_HEADED = r')
src_headless = extract(src, '_EXTRACT_JS_HEADLESS = r')
new_headless = extract(new, 'EXTRACT_JS_XCOM_HEADLESS = r')

print('HEADED match:', src_headed == new_headed)
print('HEADLESS match:', src_headless == new_headless)
if src_headed != new_headed:
    print('HEADED differs — inspect manually')
if src_headless != new_headless:
    print('HEADLESS differs — inspect manually')
"
```

Expected: `HEADED match: True` and `HEADLESS match: True`. If either is `False`, find and fix the discrepancy before continuing — do not proceed with a non-verbatim port.

- [ ] **Step 4: Update `server.py`'s module docstring and imports**

Replace the module docstring (lines 1-4):

```python
"""MCP server exposing fetch_page (raw HTML) and fetch_article (structured,
site-aware extraction for generic/WeChat/arXiv/X.com URLs). generic/WeChat/
arXiv share the warm persistent-context mechanism; X.com uses a one-off
browser launch per call instead (headed-mode-first, headless fallback) —
see docs/superpowers/specs/2026-08-08-browser-fetch-mcp-xcom-extraction-design.md."""
```

Update the import block (currently lines 16-21) to add the two new xcom JS constants:

```python
from browser_fetch_mcp.extractors import (
    EXTRACT_JS,
    EXTRACT_JS_XCOM_HEADED,
    EXTRACT_JS_XCOM_HEADLESS,
    dispatch_site,
    extract_wechat_publish_date,
    is_thin,
)
```

- [ ] **Step 5: Add the `_xcom_scrape` helper to `server.py`**

Insert this function after `_profile_key` and before `fetch_page`:

```python
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
```

- [ ] **Step 6: Restructure `fetch_article` to branch on `site == "xcom"`**

Replace the body of `fetch_article` from `site = dispatch_site(url)` through the closing of the thin-retry `if` block (i.e. everything between the scheme-validation `raise` and the `if site == "wechat": publish_date = ...` line) with:

```python
    site = dispatch_site(url)

    if site == "xcom":
        if not chrome_profile:
            raise ValueError("chrome_profile is required for x.com/Twitter URLs")

        cookies_dict = extract_cookies("https://x.com", chrome_profile)
        pw_cookies = [
            {"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True}
            for k, v in cookies_dict.items()
        ]

        try:
            result = await _xcom_scrape(url, pw_cookies, headless=False)
        except Exception:
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
                if site == "wechat":
                    retry_html = await auth_page.content()
                retry_result = await auth_page.evaluate(js)
            finally:
                await auth_page.close()

            if len(retry_result.get("blocks", [])) > len(result.get("blocks", [])):
                result = retry_result
                if site == "wechat":
                    original_html = retry_html
```

The tail after this (the `if site == "wechat": publish_date = ...` branch, the `image_blocks = await asyncio.to_thread(...)` line, and the final `return {...}` block) stays exactly as it already is — it already only reads `result`, `site`, `cookies_injected`, and `thin_retry_used`, all of which the xcom branch now sets too, plus `original_html` which is only read when `site == "wechat"` (never true for xcom). Do not duplicate or modify that tail.

Also update `fetch_article`'s docstring. Find this text (it wraps across two lines in the source):

```
    papers (arxiv.org/html/...). Raises ValueError for X.com/Twitter URLs
    — not supported yet.
```

Replace it with:

```
    papers (arxiv.org/html/...), and X.com/Twitter posts and articles
    (x.com/twitter.com).

    For x.com/twitter.com URLs, chrome_profile is required (raises ValueError
    if omitted — x.com has no anonymous mode) and the fetch uses a one-off
    browser launch (headed mode first, headless fallback) instead of the
    warm persistent context the other three sites share.
```

- [ ] **Step 7: Run the existing automated test suite to confirm no regressions**

Run (from `tools/browser-fetch-mcp/`): `[ -x .venv/bin/python3 ] || python3 -m venv .venv; .venv/bin/pip install -q -e ".[dev]"; .venv/bin/python3 -m playwright install chromium; .venv/bin/python3 -m pytest -v`

Expected: all 44 existing tests still PASS (none of them exercise the new xcom branch — `dispatch_site` tests for x.com/twitter.com hosts currently assert a `ValueError`, see Step 8 below for the required fix — everything else is unaffected).

- [ ] **Step 8: Fix the now-outdated x.com dispatch test**

`tools/browser-fetch-mcp/tests/test_extractors.py` (lines 25-36) has this test, which asserts `dispatch_site` raises `ValueError` for x.com/twitter.com hosts — that's no longer true:

```python
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
```

Replace it with:

```python
@pytest.mark.parametrize(
    "url",
    [
        "https://x.com/someuser/status/123",
        "https://www.x.com/someuser/status/123",
        "https://twitter.com/someuser/status/123",
        "https://www.twitter.com/someuser/status/123",
    ],
)
def test_dispatch_site_routes_x_dot_com_to_xcom(url):
    assert dispatch_site(url) == "xcom"
```

The `pytest` import at the top of the file stays — `pytest.mark.parametrize` is used throughout the rest of the file (e.g. `test_dispatch_site_routes_by_hostname`), independent of this change.

`tools/browser-fetch-mcp/tests/test_fetch_article.py` (lines 65-75) has this test:

```python
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
```

It doesn't pass `chrome_profile`, so with this task's changes it still errors (via the new mandatory-`chrome_profile` check) and the assertion still holds — but the name now overclaims: x.com URLs aren't categorically rejected anymore, only this specific no-`chrome_profile` case is. Rename it (function name only, body unchanged) to:

```python
async def test_fetch_article_x_dot_com_without_chrome_profile_is_rejected(tmp_path):
```

Re-run it after the rename to confirm it still passes.

Re-run the full suite after this fix:

Run (from `tools/browser-fetch-mcp/`): `.venv/bin/python3 -m pytest -v`
Expected: all tests PASS (same count as before, content of one test changed).

- [ ] **Step 9: Commit**

```bash
git add tools/browser-fetch-mcp/browser_fetch_mcp/extractors.py tools/browser-fetch-mcp/browser_fetch_mcp/server.py tools/browser-fetch-mcp/tests/test_extractors.py
git commit -m "feat(browser-fetch-mcp): add X.com/Twitter extraction to fetch_article"
```

- [ ] **Step 10: Manual verification checklist (not automated — run this yourself on a machine with a real display)**

This capability has no automated test coverage (see Global Constraints). Before considering this feature done, manually verify:

1. Pick a real X.com article or tweet URL that requires a logged-in session to view fully (e.g. one behind a login wall, or one you know has rich content).
2. Find your real Chrome profile path (same mechanism `extract-url`'s own setup uses — typically `~/Library/Application Support/Google/Chrome/<Profile Name>` on macOS) and make sure you're logged into x.com in that Chrome profile.
3. Start the MCP server in dev mode and call `fetch_article` with that URL and your real `chrome_profile` path, e.g. via a small script using the same `mcp` client pattern as `skills/research/extract-url-mcp/scripts/mcp_fetch_client.py`, or via any MCP client you have configured.
4. Confirm: a real (visible, not headless) Chrome window briefly opens on your screen during the call.
5. Confirm the returned `title`/`author`/`blocks` look like real, correct content from that article/tweet (not empty, not garbled).
6. If any images were in the article, confirm `image_blocks` is non-empty and the files actually exist under `<output_dir>/Image/`.
7. **Negative case — wrong/logged-out profile**: call `fetch_article` again with the same x.com URL but a `chrome_profile` path that either doesn't exist or points at a profile not logged into x.com. Confirm this fails fast (milliseconds, not ~2.5 minutes) with the `ValueError` about missing session cookies — not a timeout.
8. **Headless-fallback path, without touching source**: run the same real call in an environment with no display available (e.g. over SSH without X forwarding, or with `DISPLAY` unset on Linux — do NOT temporarily edit `_xcom_scrape` to force an exception, since that risks the edit not getting reverted). Confirm: (a) a message appears on the server's stderr about falling back to headless, (b) the call still returns real content (lower quality is expected — e.g. code blocks may be missing — but it shouldn't be empty or crash).
9. **Zombie-process check**: before step 8's forced-failure run, note the Chromium process count (`pgrep -fl Chromium | wc -l` or equivalent). After the run completes (whether it succeeded or the headed attempt failed), check the count again — it should match what it was before the call started (i.e. no leaked Chromium process from the try/finally around `browser.close()`, which is the entire justification for that guard existing).

Report back what you found — if the headed window didn't appear, if content looked wrong, if the negative case took minutes instead of failing fast, if the fallback stayed silent, if a Chromium process leaked, or if anything raised an unexpected error — that's a real finding to fix before this capability is considered working, not something to silently accept.

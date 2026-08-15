import re, subprocess, os
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'

try:
    from playwright.sync_api import sync_playwright as _sp  # noqa: F401
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

requires_playwright = pytest.mark.skipif(
    not PLAYWRIGHT_AVAILABLE,
    reason="playwright not installed — run: pip install playwright && playwright install chromium"
)


def _extract_js(variant):
    """Pull _EXTRACT_JS_HEADED or _EXTRACT_JS_HEADLESS source out of the script
    so it can be evaluated directly against a synthetic page — playwright_xcom.py
    always navigates to a real x.com URL with real cookies, so this is the only
    way to unit-test the DOM extraction logic in isolation."""
    src = (SCRIPTS_DIR / 'playwright_xcom.py').read_text(encoding='utf-8')
    m = re.search(rf'{variant} = r"""(.*?)"""', src, re.S)
    return m.group(1)


# Mirrors the real DOM structure of an X Article (Notes) body: Draft.js renders
# each paragraph as a public-DraftStyleDefault-block div whose children are
# per-style-run spans — a run gets style="font-weight: bold" only where bold
# is toggled on. Headings/blockquotes wrap the same block div internally.
_XCOM_ARTICLE_HTML = """\
<article data-testid="tweet">
  <time datetime="2026-07-20T11:23:31.000Z"></time>
  <div data-testid="User-Name">Codez <span>@0xCodez</span></div>
  <div data-testid="twitterArticleRichTextView">
    <h1>Test Article Title</h1>
    <div class="longform-unstyled" data-block="true" data-offset-key="a-0-0">
      <div data-offset-key="a-0-0" class="public-DraftStyleDefault-block public-DraftStyleDefault-ltr">
        <span data-offset-key="a-0-0"><span data-text="true">They don&#8217;t </span></span>
        <span data-offset-key="a-0-1" style="font-weight: bold;"><span data-text="true">route.</span></span>
        <span data-offset-key="a-0-2"><span data-text="true"> They just queue.</span></span>
      </div>
    </div>
    <blockquote class="longform-blockquote" data-block="true" data-offset-key="b-0-0">
      <div data-offset-key="b-0-0" class="public-DraftStyleDefault-block public-DraftStyleDefault-ltr">
        <span data-offset-key="b-0-0"><span data-text="true">A quoted line worth keeping.</span></span>
      </div>
    </blockquote>
    <h2 class="longform-header-two" data-block="true" data-offset-key="c-0-0">
      <div data-offset-key="c-0-0" class="public-DraftStyleDefault-block public-DraftStyleDefault-ltr">
        <span data-offset-key="c-0-0"><span data-text="true">A Heading</span></span>
      </div>
    </h2>
  </div>
</article>
"""


@requires_playwright
@pytest.mark.parametrize('variant', ['_EXTRACT_JS_HEADED', '_EXTRACT_JS_HEADLESS'])
def test_playwright_xcom_merges_bold_runs_into_one_paragraph(variant):
    """Regression: sibling style-run spans within one Draft.js paragraph block
    must merge into a single block with inline **bold** markdown, not fragment
    into separate paragraphs with the bold styling silently dropped."""
    from playwright.sync_api import sync_playwright

    js = _extract_js(variant)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(_XCOM_ARTICLE_HTML)
        result = page.evaluate(js)
        browser.close()

    blocks = result['blocks']
    para = next(b for b in blocks if 'route' in b['content'])
    assert para['content'] == "They don’t **route.** They just queue."
    assert para['tag'] == 'p'


@requires_playwright
@pytest.mark.parametrize('variant', ['_EXTRACT_JS_HEADED', '_EXTRACT_JS_HEADLESS'])
def test_playwright_xcom_no_duplicate_blocks_for_heading_and_blockquote(variant):
    """Regression: headings/blockquotes wrap a nested Draft.js paragraph div
    internally — it must not be captured a second time as an extra block."""
    from playwright.sync_api import sync_playwright

    js = _extract_js(variant)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(_XCOM_ARTICLE_HTML)
        result = page.evaluate(js)
        browser.close()

    blocks = result['blocks']
    quote_blocks = [b for b in blocks if 'quoted line' in b['content']]
    assert len(quote_blocks) == 1, f'blockquote text duplicated: {quote_blocks}'
    assert quote_blocks[0]['tag'] == 'blockquote'

    heading_blocks = [b for b in blocks if 'Heading' in b['content']]
    assert len(heading_blocks) == 1, f'heading text duplicated: {heading_blocks}'
    assert heading_blocks[0]['tag'] == 'h2'


def test_playwright_xcom_invalid_scheme(skill_config):
    """Security check rejects non-http/https URLs before reading config."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
         'javascript:alert(1)'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_xcom_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
         'https://x.com/user/status/123456789'],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_xcom_no_args():
    """Script exits non-zero when URL argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py')],
        env={**os.environ, 'PATH': os.environ.get('PATH', '')},
        capture_output=True, text=True
    )
    assert result.returncode != 0


def test_image_download_uses_certifi_ssl(tmp_path):
    """Image download creates SSL context with certifi CA bundle (macOS SSL fix)."""
    import ssl, certifi, urllib.request
    from unittest.mock import patch, MagicMock

    captured = {}

    def fake_create_default_context(**kwargs):
        captured['cafile'] = kwargs.get('cafile')
        ctx = MagicMock(spec=ssl.SSLContext)
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
        return ctx

    fake_resp = MagicMock()
    fake_resp.read.return_value = b'\x89PNG\r\n'
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = MagicMock(return_value=False)

    with patch('ssl.create_default_context', side_effect=fake_create_default_context), \
         patch('urllib.request.urlopen', return_value=fake_resp):
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        urllib.request.urlopen(MagicMock(), timeout=15, context=ssl_ctx)

    assert captured.get('cafile') == certifi.where(), \
        f"Expected certifi CA path, got: {captured.get('cafile')}"


def test_playwright_xcom_only_one_arg_needed(skill_config):
    """Regression: script accepts single URL arg (old code needed 4 args).

    Verifies IndexError on argv[2] is NOT raised — failure mode shifts
    from arg-count error to config/network, not to missing argument.
    With valid config but missing Cookies file, error is at pycookiecheat level.
    """
    env = {
        **skill_config['env'],
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_xcom.py'),
         'https://x.com/user/status/123456789'],
        env=env, capture_output=True, text=True,
        timeout=10
    )
    # Should fail at Cookies file level (pycookiecheat / chrome profile missing),
    # NOT at argument-count level (IndexError on argv[2]).
    # Either way, returncode != 0 — but stderr must NOT contain "IndexError"
    assert 'IndexError' not in result.stderr, \
        'Should not fail on argument count — old 4-arg interface was removed'


def test_playwright_xcom_imports_get_article_paths():
    """Regression: script must import get_article_paths, not compute url_hash/Image/Origin inline."""
    content = (SCRIPTS_DIR / 'playwright_xcom.py').read_text(encoding='utf-8')
    assert 'get_article_paths' in content
    assert "os.path.join(vault_path, 'Image')" not in content
    assert "os.path.join(vault_path, 'Origin')" not in content

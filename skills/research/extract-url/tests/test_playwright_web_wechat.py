import subprocess, os, pytest
from pathlib import Path

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

# Mirrors real mp.weixin.qq.com markup: #js_content starts visibility:hidden
# (WeChat's own unlock script never runs in our headless context), images
# are lazy-loaded via data-src with no usable src attribute, and the publish
# date lives only in a `var ct = "<unix ts>"` script variable.
_TEST_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>WeChat Test Article</title>
  <script>var ct = "1719763200";</script>
</head>
<body>
  <h1 class="rich_media_title" id="activity-name">
    <span class="js_title_inner">WeChat Test Article</span>
  </h1>
  <a id="js_name">Test Official Account</a>
  <div id="js_content" style="visibility: hidden; opacity: 0;">
    <p>First paragraph with sufficient content to be captured by the playwright_web_wechat scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
    <section><img data-src="https://mmbiz.qpic.cn/test/640?wx_fmt=png" class="rich_pages wxw-img"></section>
  </div>
</body>
</html>
"""

_TEST_HTML_NO_AUTHOR = """\
<!DOCTYPE html>
<html>
<head>
  <title>WeChat No Author Article</title>
</head>
<body>
  <h1 class="rich_media_title" id="activity-name">
    <span class="js_title_inner">WeChat No Author Article</span>
  </h1>
  <div id="js_content" style="visibility: hidden; opacity: 0;">
    <p>First paragraph with sufficient content to be captured by the playwright_web_wechat scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </div>
</body>
</html>
"""


def test_playwright_web_wechat_invalid_url_scheme(skill_config, tmp_path):
    """Security check rejects non-http/https URLs before reading config."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'file:///etc/passwd', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_web_wechat_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'https://mp.weixin.qq.com/s/testid', str(html)],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_web_wechat_too_few_args(skill_config):
    """Script exits non-zero when html_path argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'https://mp.weixin.qq.com/s/testid'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0


@requires_playwright
def test_playwright_web_wechat_e2e(skill_config, tmp_path):
    """Full e2e: hidden #js_content + data-src images + ct timestamp all extracted correctly."""
    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'https://mp.weixin.qq.com/s/testid001', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert 'ORIGIN_PATH:' in result.stdout

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    origin_file = Path(origin_path)
    assert origin_file.exists(), f'Origin file not found at {origin_path}'

    content = origin_file.read_text(encoding='utf-8')
    assert 'WeChat Test Article' in content
    assert 'source_url: https://mp.weixin.qq.com/s/testid001' in content
    assert 'author: Test Official Account' in content
    # ct = 1719763200 -> 2024-07-01 in UTC+8
    assert 'publish_date: 2024-07-01' in content
    # Content behind visibility:hidden must still be captured via textContent.
    assert 'First paragraph with sufficient content' in content
    assert 'Second paragraph providing additional body text' in content

    import hashlib
    expected_hash = hashlib.md5('https://mp.weixin.qq.com/s/testid001'.encode()).hexdigest()[:8]
    assert origin_file.parent.name == 'Origin'
    assert origin_file.parent.parent.name == expected_hash
    assert origin_file.parent.parent.parent == skill_config['vault']

    assert not (origin_file.parent.parent / '.fetch_issues.tmp').exists()


@requires_playwright
def test_playwright_web_wechat_finds_data_src_image(skill_config, tmp_path):
    """Lazy-loaded images (data-src, no usable src attribute) are recognized as
    real image URLs instead of being skipped (network fetch itself isn't under test)."""
    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'https://mp.weixin.qq.com/s/testid002', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert 'Skipped unsafe image URL' not in result.stdout
    assert '1 images' in result.stdout


@requires_playwright
def test_playwright_web_wechat_e2e_writes_fetch_issues_tmp_when_incomplete(skill_config, tmp_path):
    """When origin frontmatter has real gaps (missing author/date), a temp issues file is written."""
    html = tmp_path / 'no-author.html'
    html.write_text(_TEST_HTML_NO_AUTHOR, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_wechat.py'),
         'https://mp.weixin.qq.com/s/testid003', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True,
        timeout=60
    )
    assert result.returncode == 0, result.stderr

    origin_path = next(
        line.split('ORIGIN_PATH:', 1)[1].strip()
        for line in result.stdout.splitlines()
        if line.startswith('ORIGIN_PATH:')
    )
    article_dir = Path(origin_path).parent.parent
    tmp_issues = article_dir / '.fetch_issues.tmp'
    assert tmp_issues.exists()
    text = tmp_issues.read_text(encoding='utf-8')
    assert 'author空' in text
    assert 'publish_date空' in text
    assert 'description空' not in text

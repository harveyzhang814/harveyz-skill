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

_TEST_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>arXiv Test Article</title>
  <meta name="author" content="arXiv Author">
  <meta property="article:published_time" content="2024-06-01">
</head>
<body>
  <article>
    <h1>arXiv Test Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web_arxiv scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""

_TEST_HTML_NO_AUTHOR = """\
<!DOCTYPE html>
<html>
<head>
  <title>arXiv No Author Article</title>
</head>
<body>
  <article>
    <h1>arXiv No Author Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web_arxiv scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""


def test_playwright_web_arxiv_invalid_url_scheme(skill_config, tmp_path):
    """Security check rejects non-http/https URLs before reading config."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'file:///etc/passwd', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_web_arxiv_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.01234', str(html)],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_web_arxiv_too_few_args(skill_config):
    """Script exits non-zero when html_path argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.01234'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0


@requires_playwright
def test_playwright_web_arxiv_e2e(skill_config, tmp_path):
    """Full e2e: HTML file → ORIGIN_PATH in stdout + file saved to vault."""
    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.06001', str(html)],
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
    assert 'arXiv Test Article' in content
    assert 'source_url: https://arxiv.org/html/2024.06001' in content

    import hashlib
    expected_hash = hashlib.md5('https://arxiv.org/html/2024.06001'.encode()).hexdigest()[:8]
    assert origin_file.parent.name == 'Origin'
    assert origin_file.parent.parent.name == expected_hash
    assert origin_file.parent.parent.parent == skill_config['vault']

    assert not (origin_file.parent.parent / '.fetch_issues.tmp').exists()


@requires_playwright
def test_playwright_web_arxiv_e2e_writes_fetch_issues_tmp_when_incomplete(skill_config, tmp_path):
    """When origin frontmatter has real gaps (missing author/date), a temp issues file is written."""
    html = tmp_path / 'no-author.html'
    html.write_text(_TEST_HTML_NO_AUTHOR, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web_arxiv.py'),
         'https://arxiv.org/html/2024.07002', str(html)],
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

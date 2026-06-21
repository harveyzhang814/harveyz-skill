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
  <title>E2E Test Article</title>
  <meta name="author" content="E2E Author">
  <meta property="article:published_time" content="2024-06-01">
</head>
<body>
  <article>
    <h1>E2E Test Article</h1>
    <p>First paragraph with sufficient content to be captured by the playwright_web scraper logic.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test.</p>
  </article>
</body>
</html>
"""


def test_playwright_web_invalid_url_scheme(skill_config, tmp_path):
    """Security check rejects non-http/https URLs before reading config."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'file:///etc/passwd', str(html)],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert 'Rejected URL' in result.stderr


def test_playwright_web_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    html = tmp_path / 'test.html'
    html.write_text('<html><body><h1>X</h1></body></html>')
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com', str(html)],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0


def test_playwright_web_too_few_args(skill_config):
    """Script exits non-zero when html_path argument is missing."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com'],
        env=skill_config['env'],
        capture_output=True, text=True
    )
    assert result.returncode != 0


@requires_playwright
def test_playwright_web_e2e(skill_config, tmp_path):
    """Full e2e: HTML file → ORIGIN_PATH in stdout + file saved to vault."""
    # Import conftest's url_index_db fixture
    import sqlite3
    db_path = skill_config['vault'] / 'url-index.db'
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS url_index (
            source_url   TEXT PRIMARY KEY,
            title        TEXT,
            fetched_at   TEXT,
            issues       TEXT,
            category     TEXT,
            origin_path  TEXT,
            article_path TEXT
        )
    """)
    conn.commit()
    conn.close()

    html = tmp_path / 'article.html'
    html.write_text(_TEST_HTML, encoding='utf-8')

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'playwright_web.py'),
         'https://example.com/e2e-test', str(html)],
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
    assert 'E2E Test Article' in content
    assert 'source_url: https://example.com/e2e-test' in content

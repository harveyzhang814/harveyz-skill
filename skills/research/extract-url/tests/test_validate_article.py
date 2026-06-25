import sqlite3, subprocess, os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def test_validate_article_success(skill_config, valid_article_files):
    """Valid article exits 0 and writes URL to SQLite."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    valid_article_files['url'],
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr

    db_path = skill_config['vault'] / 'url-index.db'
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        'SELECT source_url FROM url_index WHERE source_url=?',
        (valid_article_files['url'],)
    ).fetchone()
    conn.close()
    assert row is not None, 'URL should be written to SQLite after successful validation'


def test_validate_article_no_article_db_env_needed(skill_config, valid_article_files):
    """Regression: ARTICLE_DB env var must NOT be required."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/no-db-test',
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    env.pop('ARTICLE_DB', None)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, \
        f'Should work without ARTICLE_DB env var. stderr: {result.stderr}'


def test_validate_article_no_skill_dir_env_needed(skill_config, valid_article_files):
    """Regression: ARTICLE_SKILL_DIR env var must NOT be required."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/no-skill-dir-test',
        'ARTICLE_ORIGIN': str(valid_article_files['origin']),
        'ARTICLE_PATH':   str(valid_article_files['article']),
        'PATH': os.environ.get('PATH', ''),
    }
    env.pop('ARTICLE_SKILL_DIR', None)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, \
        f'Should work without ARTICLE_SKILL_DIR env var. stderr: {result.stderr}'


def test_validate_article_missing_article_path(skill_config, url_index_db):
    """Exits 1 when ARTICLE_PATH does not exist."""
    env = {
        **skill_config['env'],
        'ARTICLE_URL':    'https://example.com/missing',
        'ARTICLE_ORIGIN': str(skill_config['vault'] / 'Origin' / 'missing.md'),
        'ARTICLE_PATH':   str(skill_config['vault'] / 'missing.md'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert 'not found' in result.stderr


def test_validate_article_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    env = {
        **os.environ,
        'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
        'ARTICLE_URL':    'https://example.com/test',
        'ARTICLE_ORIGIN': str(tmp_path / 'origin.md'),
        'ARTICLE_PATH':   str(tmp_path / 'article.md'),
        'PATH': os.environ.get('PATH', ''),
    }
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'validate_article.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode != 0

import sqlite3, subprocess, os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def test_dedup_check_ok_new_url(skill_config):
    """New URL returns OK on stdout."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': 'https://example.com/new'},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


def test_dedup_check_already_fetched(skill_config, url_index_db):
    """URL already in DB returns ALREADY_FETCHED."""
    url = 'https://example.com/existing'
    conn = sqlite3.connect(str(url_index_db))
    conn.execute("INSERT INTO url_index (source_url) VALUES (?)", (url,))
    conn.commit()
    conn.close()

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ALREADY_FETCHED'


def test_dedup_check_creates_db_file(skill_config):
    """Script creates url-index.db if it does not yet exist."""
    db_path = skill_config['vault'] / 'url-index.db'
    assert not db_path.exists()

    subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': 'https://example.com/creates-db'},
        capture_output=True, text=True
    )
    assert db_path.exists()


def test_dedup_check_missing_config(tmp_path):
    """Clear error when config.json does not exist."""
    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={
            **os.environ,
            'HSKILL_EXTRACT_URL_CONFIG': str(tmp_path / 'nonexistent.json'),
            'CHECK_URL': 'https://example.com/test',
            'PATH': os.environ.get('PATH', ''),
        },
        capture_output=True, text=True
    )
    assert result.returncode != 0
    assert '配置文件不存在' in result.stderr


def test_dedup_check_no_db_path_env_needed(skill_config):
    """Regression: DB_PATH env var must NOT be required after refactor."""
    env = skill_config['env'].copy()
    env.pop('DB_PATH', None)
    env['CHECK_URL'] = 'https://example.com/no-db-path-test'

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() in ('OK', 'ALREADY_FETCHED')

import json, subprocess, os
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


def test_dedup_check_already_fetched(skill_config, write_meta_json_fixture):
    """URL with existing meta.json returns ALREADY_FETCHED."""
    url = 'https://example.com/existing'
    write_meta_json_fixture(url)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'ALREADY_FETCHED'


def test_dedup_check_hash_collision_url_mismatch_returns_ok(skill_config):
    """meta.json exists but source_url differs (hash collision) still returns OK."""
    from config import get_url_hash
    url = 'https://example.com/collision-check'
    hash8 = get_url_hash(url)
    article_dir = skill_config['vault'] / hash8
    article_dir.mkdir(parents=True)
    (article_dir / 'meta.json').write_text(
        json.dumps({'source_url': 'https://example.com/a-different-url'}), encoding='utf-8'
    )

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


def test_dedup_check_partial_state_no_meta_json_returns_ok(skill_config):
    """Origin exists (Subagent 1 done) but meta.json not yet written (Subagent 2 pending) -> OK, allow retry."""
    from config import get_url_hash
    url = 'https://example.com/partial'
    hash8 = get_url_hash(url)
    (skill_config['vault'] / hash8 / 'Origin').mkdir(parents=True)

    result = subprocess.run(
        ['python3', str(SCRIPTS_DIR / 'dedup_check.py')],
        env={**skill_config['env'], 'CHECK_URL': url},
        capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'OK'


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

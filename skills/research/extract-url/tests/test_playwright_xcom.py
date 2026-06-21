import subprocess, os
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


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

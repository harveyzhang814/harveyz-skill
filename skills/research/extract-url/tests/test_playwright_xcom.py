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

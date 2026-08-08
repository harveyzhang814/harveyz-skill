"""Offline tests for detect_xcom_chrome_profile.py — uses
EXTRACT_URL_MCP_CHROME_BASE to point at a fake profile directory tree
instead of touching real Chrome profile data. Real detection against an
actually-logged-in profile can't be automated (needs a real Chrome
install with real cookies) — this only tests the script's own logic
(profile iteration, cookie-existence query, "not found" reporting)
against controlled fixtures.

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "detect_xcom_chrome_profile.py"


def _make_cookies_db(path: Path, rows):
    """rows: list of (name, host_key) tuples"""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cookies (name TEXT, host_key TEXT)")
    conn.executemany("INSERT INTO cookies (name, host_key) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def _run(chrome_base: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "EXTRACT_URL_MCP_CHROME_BASE": str(chrome_base)},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_no_chrome_dir_reports_none_found(tmp_path):
    nonexistent = tmp_path / "NoChromeHere"
    output = _run(nonexistent)
    assert "RECOMMENDED_PROFILE: (none found)" in output


def test_profile_with_no_cookies_db_reports_none_found(tmp_path):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    output = _run(chrome_base)
    assert "(no X.com cookies)" in output
    assert "RECOMMENDED_PROFILE: (none found)" in output


def test_profile_with_auth_cookies_is_recommended(tmp_path):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("auth_token", ".x.com"), ("ct0", ".x.com"), ("some_other_cookie", ".example.com")],
    )
    output = _run(chrome_base)
    assert "auth_token" in output
    assert "looks logged in" in output
    assert f"RECOMMENDED_PROFILE: {default_dir}" in output
    assert "some_other_cookie" not in output


def test_profile_with_unrelated_cookies_only_is_not_recommended(tmp_path):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("session_id", ".x.com")],  # present but not one of the auth cookie names
    )
    output = _run(chrome_base)
    assert "session_id" in output
    assert "looks logged in" not in output
    assert "RECOMMENDED_PROFILE: (none found)" in output

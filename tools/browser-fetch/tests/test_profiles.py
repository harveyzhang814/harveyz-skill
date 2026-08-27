"""Unit tests for profiles.py's Chrome profile discovery — uses
BROWSER_FETCH_CHROME_BASE to point at a fake profile directory tree
instead of touching a real Chrome install. Existence-only: no cookie
value is ever decrypted here, only cookie *names* are checked."""
import os
import sqlite3
from pathlib import Path

from browser_fetch.profiles import list_chrome_profiles

HOST_KEYS = [".x.com", ".twitter.com"]
COOKIE_NAMES = ["auth_token", "ct0", "twid"]


def _make_cookies_db(path: Path, rows):
    """rows: list of (name, host_key) tuples"""
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE cookies (name TEXT, host_key TEXT)")
    conn.executemany("INSERT INTO cookies (name, host_key) VALUES (?, ?)", rows)
    conn.commit()
    conn.close()


def test_no_chrome_dir_returns_empty_list(tmp_path, monkeypatch):
    nonexistent = tmp_path / "NoChromeHere"
    monkeypatch.setenv("BROWSER_FETCH_CHROME_BASE", str(nonexistent))
    assert list_chrome_profiles(HOST_KEYS, COOKIE_NAMES) == []


def test_profile_with_no_cookies_db_is_listed_but_not_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    monkeypatch.setenv("BROWSER_FETCH_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert len(result) == 1
    assert result[0]["matched_cookie_names"] == []
    assert result[0]["looks_logged_in"] is False


def test_profile_with_auth_cookies_is_marked_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("auth_token", ".x.com"), ("ct0", ".x.com"), ("some_other_cookie", ".example.com")],
    )
    monkeypatch.setenv("BROWSER_FETCH_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert len(result) == 1
    assert result[0]["profile_path"] == str(default_dir)
    assert set(result[0]["matched_cookie_names"]) == {"auth_token", "ct0"}
    assert result[0]["looks_logged_in"] is True
    assert "some_other_cookie" not in result[0]["matched_cookie_names"]


def test_profile_with_unrelated_cookies_only_is_not_logged_in(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    _make_cookies_db(
        default_dir / "Cookies",
        [("session_id", ".x.com")],  # present but not one of cookie_names
    )
    monkeypatch.setenv("BROWSER_FETCH_CHROME_BASE", str(chrome_base))

    result = list_chrome_profiles(HOST_KEYS, COOKIE_NAMES)
    assert result[0]["matched_cookie_names"] == ["session_id"]
    assert result[0]["looks_logged_in"] is False

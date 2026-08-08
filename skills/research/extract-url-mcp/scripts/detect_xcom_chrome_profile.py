#!/usr/bin/env python3
"""
Detect which Chrome profile(s) are logged into X.com (Twitter), by
checking for the presence of X's known auth cookie names — no
decryption, just existence checks via a copy of the Cookies sqlite db.

Written from scratch — does not import extract-url's
detect_chrome_profile.py.

Usage: python3 detect_xcom_chrome_profile.py
Prints a human-readable comparison table, then one line:
  RECOMMENDED_PROFILE: <path>
or, if no profile has any of the known auth cookies:
  RECOMMENDED_PROFILE: (none found)

This script only reports candidates — it never picks one automatically
for a caller. Detection and use MUST stay separated: whoever calls this
script must show the result to a human and get explicit confirmation
before using any profile path for an authenticated fetch. This mirrors
extract-url's own detect_chrome_profile.py, which is documented as
"agent must not call this proactively / must not auto-detect and then
silently use the result" — same constraint, restated here since this is
a separate, from-scratch script.

EXTRACT_URL_MCP_CHROME_BASE env var overrides the Chrome profiles
directory (for tests — never points at a real Chrome install by default).
"""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

CHROME_BASE = Path(
    os.environ.get("EXTRACT_URL_MCP_CHROME_BASE")
    or (Path.home() / "Library" / "Application Support" / "Google" / "Chrome")
)
XCOM_HOSTS = (".twitter.com", ".x.com")
AUTH_COOKIES = {"auth_token", "ct0", "twid"}


def _profile_email(profile_dir: Path) -> str:
    prefs = profile_dir / "Preferences"
    try:
        data = json.loads(prefs.read_text(errors="ignore"))
        accounts = data.get("account_info", [])
        if accounts:
            return accounts[0].get("email", "")
        return data.get("user_name", "")
    except Exception:
        return ""


def _xcom_cookie_names(profile_dir: Path) -> set:
    """Cookie names found for x.com/twitter.com in this profile — existence
    only, never decrypted."""
    cookies_db = profile_dir / "Cookies"
    if not cookies_db.exists():
        return set()

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        shutil.copy2(cookies_db, tmp_path)
        conn = sqlite3.connect(tmp_path)
        try:
            cur = conn.cursor()
            placeholders = ",".join("?" * len(XCOM_HOSTS))
            cur.execute(
                f"SELECT name FROM cookies WHERE host_key IN ({placeholders})",
                XCOM_HOSTS,
            )
            return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return set()
    finally:
        os.unlink(tmp_path)


def main():
    if not CHROME_BASE.exists():
        print(f"Chrome directory not found: {CHROME_BASE}")
        print("RECOMMENDED_PROFILE: (none found)")
        return

    profiles = sorted(
        (d for d in CHROME_BASE.iterdir() if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile"))),
        key=lambda d: (d.name != "Default", d.name),
    )

    print(f"{'Profile':<12} {'Account':<38} {'X.com cookies found'}")
    print("-" * 80)

    recommended = None
    for profile_dir in profiles:
        email = _profile_email(profile_dir) or "(not logged into Google)"
        cookie_names = _xcom_cookie_names(profile_dir)
        has_auth = bool(AUTH_COOKIES & cookie_names)
        status = ", ".join(sorted(cookie_names)) if cookie_names else "(no X.com cookies)"
        marker = " <-- looks logged in" if has_auth else ""
        print(f"{profile_dir.name:<12} {email:<38} {status}{marker}")
        if has_auth and recommended is None:
            recommended = profile_dir

    print()
    if recommended:
        print(f"RECOMMENDED_PROFILE: {recommended}")
    else:
        print("RECOMMENDED_PROFILE: (none found)")


if __name__ == "__main__":
    main()

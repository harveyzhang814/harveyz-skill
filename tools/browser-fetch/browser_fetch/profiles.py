"""Chrome profile discovery — lists local Chrome profiles and checks,
by cookie NAME only (no decryption), whether each looks logged into a
caller-supplied set of hosts. Generalizes extract-url-mcp's original
detect_xcom_chrome_profile.py (which hardcoded X.com's host_keys and
cookie names) into parameters, so other consumers can reuse it for a
different site later.
"""
import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path


def _chrome_base() -> Path:
    override = os.environ.get("BROWSER_FETCH_CHROME_BASE")
    return (
        Path(override)
        if override
        else Path.home() / "Library" / "Application Support" / "Google" / "Chrome"
    )


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


def _matching_cookie_names(profile_dir: Path, host_keys: list[str]) -> set[str]:
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
            placeholders = ",".join("?" * len(host_keys))
            cur.execute(
                f"SELECT DISTINCT name FROM cookies WHERE host_key IN ({placeholders})",
                host_keys,
            )
            return {row[0] for row in cur.fetchall()}
        finally:
            conn.close()
    except Exception:
        return set()
    finally:
        os.unlink(tmp_path)


def list_chrome_profiles(host_keys: list[str], cookie_names: list[str]) -> list[dict]:
    """Scan local Chrome profiles, returning one dict per profile:
    {"profile_path", "account_email", "matched_cookie_names", "looks_logged_in"}.

    looks_logged_in is True iff ANY of cookie_names was found among the
    cookies matched by host_keys in that profile — same "any match"
    semantics as the script this generalizes. Existence-only: cookie
    values are never decrypted here.
    """
    chrome_base = _chrome_base()
    if not chrome_base.exists():
        return []

    profile_dirs = sorted(
        (
            d
            for d in chrome_base.iterdir()
            if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile"))
        ),
        key=lambda d: (d.name != "Default", d.name),
    )

    required = set(cookie_names)
    results = []
    for profile_dir in profile_dirs:
        found = _matching_cookie_names(profile_dir, host_keys)
        results.append(
            {
                "profile_path": str(profile_dir),
                "account_email": _profile_email(profile_dir),
                "matched_cookie_names": sorted(found),
                "looks_logged_in": bool(required & found),
            }
        )
    return results

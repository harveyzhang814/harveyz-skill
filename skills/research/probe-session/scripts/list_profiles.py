#!/usr/bin/env python3
"""
List all Chrome profiles with their X.com login status.
Outputs a JSON array to stdout for agent parsing.

Usage: python list_profiles.py
"""
import json, os, shutil, sqlite3, tempfile, sys
from pathlib import Path

CHROME_BASE  = Path.home() / "Library/Application Support/Google/Chrome"
AUTH_COOKIES = {"auth_token", "ct0", "twid"}
XCOM_HOSTS   = (".twitter.com", ".x.com")


def get_profile_email(profile_dir):
    try:
        data = json.loads((profile_dir / "Preferences").read_text(errors="ignore"))
        accounts = data.get("account_info", [])
        return accounts[0].get("email", "") if accounts else data.get("user_name", "")
    except Exception:
        return ""


def get_xcom_cookies(profile_dir):
    cookies_db = profile_dir / "Cookies"
    if not cookies_db.exists():
        return set(), None
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = f.name
    try:
        shutil.copy2(cookies_db, tmp)
        conn = sqlite3.connect(tmp)
        found = {row[0] for row in conn.execute(
            "SELECT name FROM cookies WHERE host_key IN (?, ?)", XCOM_HOSTS
        )}
        conn.close()
        return found, None
    except Exception as e:
        return set(), str(e)
    finally:
        os.unlink(tmp)


if not CHROME_BASE.exists():
    print(json.dumps({"error": f"Chrome 目录不存在：{CHROME_BASE}"}))
    sys.exit(1)

profiles = sorted(
    [d for d in CHROME_BASE.iterdir()
     if d.is_dir() and (d.name == "Default" or d.name.startswith("Profile"))],
    key=lambda d: (d.name != "Default", d.name),
)

output = []
for p in profiles:
    email   = get_profile_email(p) or "(未关联 Google 账号)"
    cookies, error = get_xcom_cookies(p)
    has_auth = bool(AUTH_COOKIES & cookies) if not error else False
    output.append({
        "name":          p.name,
        "path":          str(p),
        "email":         email,
        "has_xcom_auth": has_auth,
        "xcom_cookies":  sorted(cookies) if not error else [],
        "error":         error,
    })

print(json.dumps(output, ensure_ascii=False, indent=2))

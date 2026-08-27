"""Chrome profile cookie extraction.

Mirrors docs/explanation/chrome-profile-cookie-injection.md's pattern:
copy the Cookies DB to a temp file first (Chrome holds an exclusive lock
on the original while running), then let pycookiecheat decrypt it. This
module only extracts plaintext cookies — injecting them into a browser
context happens in server.py, which owns the browser lifecycle.
"""
import os
import shutil
import tempfile
from pathlib import Path

import pycookiecheat


def extract_cookies(url: str, chrome_profile: str) -> dict[str, str]:
    """Return {cookie_name: plaintext_value} for `url`'s domain from the
    given Chrome profile.

    Returns {} if the profile has no Cookies file, or if pycookiecheat
    finds no matching cookies — this is a normal "not logged in" result,
    not an error condition, so it never raises for that case.
    """
    cookies_src = Path(chrome_profile) / "Cookies"
    if not cookies_src.exists():
        return {}

    fd, tmp_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        shutil.copy2(cookies_src, tmp_path)
        return pycookiecheat.chrome_cookies(url, cookie_file=tmp_path) or {}
    finally:
        os.unlink(tmp_path)

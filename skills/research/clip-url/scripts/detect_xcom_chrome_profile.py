#!/usr/bin/env python3
"""
Detect which Chrome profile(s) are logged into X.com (Twitter), via
browser-fetch's `profile list` subcommand — no direct sqlite access here
anymore; the cookie-scanning logic now lives in
tools/browser-fetch/browser_fetch/profiles.py.

Usage: python3 detect_xcom_chrome_profile.py
Prints a human-readable comparison table, then one line:
  RECOMMENDED_PROFILE: <path>
or, if no profile has any of the known auth cookies:
  RECOMMENDED_PROFILE: (none found)

This script only reports candidates — it never picks one automatically
for a caller. Detection and use MUST stay separated: whoever calls this
script must show the result to a human and get explicit confirmation
before persisting a profile via chrome_profile_config.py.
"""
import browser_fetch_cli

HOST_KEYS = [".x.com", ".twitter.com"]
COOKIE_NAMES = ["auth_token", "ct0", "twid"]


def _list_profiles() -> list[dict]:
    args = ["profile", "list"]
    for h in HOST_KEYS:
        args += ["--host-key", h]
    for c in COOKIE_NAMES:
        args += ["--cookie-name", c]
    return browser_fetch_cli.call(*args)["profiles"]


def main():
    profiles = _list_profiles()

    if not profiles:
        print("No Chrome profiles found.")
        print("RECOMMENDED_PROFILE: (none found)")
        return

    print(f"{'Profile':<50} {'Account':<38} {'X.com cookies found'}")
    print("-" * 110)

    recommended = None
    for p in profiles:
        email = p["account_email"] or "(not logged into Google)"
        names = p["matched_cookie_names"]
        status = ", ".join(names) if names else "(no X.com cookies)"
        marker = " <-- looks logged in" if p["looks_logged_in"] else ""
        print(f"{p['profile_path']:<50} {email:<38} {status}{marker}")
        if p["looks_logged_in"] and recommended is None:
            recommended = p["profile_path"]

    print()
    if recommended:
        print(f"RECOMMENDED_PROFILE: {recommended}")
    else:
        print("RECOMMENDED_PROFILE: (none found)")


if __name__ == "__main__":
    main()

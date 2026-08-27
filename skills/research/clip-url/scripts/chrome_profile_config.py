#!/usr/bin/env python3
"""Thin CLI wrapper for reading/writing browser-fetch's persisted default
Chrome profile (`profile get` / `profile set` subcommands). Written from
scratch, same browser_fetch_cli.call() pattern as mcp_fetch_client.py and
detect_xcom_chrome_profile.py.

Also tracks, purely locally (no browser-fetch call involved), whether
clip-url has already asked the user about chrome_profile once — so
SKILL.md's step 2 only prompts on the very first run, regardless of
whether the user set a profile or declined, instead of re-prompting on
every run until a profile happens to get set.

Usage:
  python3 chrome_profile_config.py get
  python3 chrome_profile_config.py set <profile_path>
  python3 chrome_profile_config.py prompted
  python3 chrome_profile_config.py mark-prompted

get prints "CONFIGURED: <path>" or "NOT_CONFIGURED".
set prints "OK" on success; on failure, prints the error to stderr and
exits 1 (e.g. profile_path doesn't exist or isn't a directory).
prompted prints "YES" or "NO".
mark-prompted records that the user has been asked and prints "OK".
"""
import os
import sys
from pathlib import Path

import browser_fetch_cli


def _prompted_marker_path() -> Path:
    env_dir = os.environ.get("HSKILL_CLIP_URL_DATA_DIR")
    base = Path(env_dir) if env_dir else Path.home() / ".hskill" / "clip-url"
    return base / "chrome_profile_prompted"


def get_prompted() -> bool:
    return _prompted_marker_path().exists()


def mark_prompted() -> None:
    marker = _prompted_marker_path()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("", encoding="utf-8")


def _get() -> str:
    payload = browser_fetch_cli.call("profile", "get")
    profile_path = payload["profile_path"]
    return f"CONFIGURED: {profile_path}" if profile_path else "NOT_CONFIGURED"


def _set(profile_path: str) -> str:
    browser_fetch_cli.call("profile", "set", profile_path)
    return "OK"


def main():
    valid = ("get", "set", "prompted", "mark-prompted")
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print(
            "Usage: chrome_profile_config.py get | set <profile_path> | prompted | mark-prompted",
            file=sys.stderr,
        )
        sys.exit(1)

    if sys.argv[1] == "get":
        print(_get())
        return

    if sys.argv[1] == "prompted":
        print("YES" if get_prompted() else "NO")
        return

    if sys.argv[1] == "mark-prompted":
        mark_prompted()
        print("OK")
        return

    if len(sys.argv) < 3:
        print("Usage: chrome_profile_config.py set <profile_path>", file=sys.stderr)
        sys.exit(1)

    try:
        print(_set(sys.argv[2]))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

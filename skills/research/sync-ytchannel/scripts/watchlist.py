#!/usr/bin/env python3
"""Persisted sync-ytchannel watchlist — one entry per watched YouTube channel:
handle, channel_url, and the set of video URLs already reported. Pure I/O +
CRUD + diff logic here, no MCP/network calls — those live in
mcp_channel_client.py and sync_channels.py.

The cursor is a set of URLs rather than sync-xtimeline's single
last_seen id: X's snowflake tweet ids sort by recency, YouTube's video ids
are opaque, so "newer than X" isn't expressible — "not yet reported" is.

Usage:
  python3 watchlist.py add <channel_url>
  python3 watchlist.py remove <handle>
  python3 watchlist.py list
"""
import json
import re
import sys
from pathlib import Path
from typing import Optional

from config import get_data_dir

_CHANNEL_URL_RE = re.compile(
    r"^https?://(?:www\.|m\.)?youtube\.com/(?:(@[^/?#]+)|(?:channel|c|user)/([^/?#]+))(?:/[^/?#]*)?/?(?:[?#].*)?$"
)


def handle_from_url(channel_url: str) -> str:
    """The watchlist key for a channel URL: the @handle without its "@", or
    the channel/c/user id. Raises ValueError for anything that isn't a
    YouTube channel URL (a /watch?v= link included — this skill watches
    channels, never single videos)."""
    match = _CHANNEL_URL_RE.match(channel_url.strip())
    if not match:
        raise ValueError(f"不是 YouTube 频道 URL：{channel_url}")
    at_handle, path_id = match.groups()
    return at_handle[1:] if at_handle else path_id


def _watchlist_path() -> Path:
    return get_data_dir() / "watchlist.json"


def load_watchlist() -> list[dict]:
    path = _watchlist_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_watchlist(entries: list[dict]) -> None:
    path = _watchlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def add_channel(channel_url: str) -> str:
    handle = handle_from_url(channel_url)
    entries = load_watchlist()
    if any(e["handle"] == handle for e in entries):
        raise ValueError(f"already watching @{handle}")
    entries.append({"handle": handle, "channel_url": channel_url, "seen_urls": None})
    save_watchlist(entries)
    return handle


def remove_channel(handle: str) -> None:
    entries = load_watchlist()
    remaining = [e for e in entries if e["handle"] != handle]
    if len(remaining) == len(entries):
        raise ValueError(f"not watching @{handle}")
    save_watchlist(remaining)


def set_seen_urls(handle: str, urls: list[str]) -> None:
    entries = load_watchlist()
    for e in entries:
        if e["handle"] == handle:
            e["seen_urls"] = urls
            save_watchlist(entries)
            return
    raise ValueError(f"not watching @{handle}")


def compute_update(entry: dict, videos: list[dict]) -> tuple[str, Optional[dict]]:
    """Pure diff: given a watchlist entry and a freshly-fetched video list
    (newest-first, per fetch_channel_videos' contract), decide what this run
    should report and persist. Never touches disk — callers persist the
    returned seen_urls via set_seen_urls().

    seen_urls is None only before the first successful fetch; that run
    establishes a baseline (record everything, report nothing) instead of
    dumping the channel's entire back catalogue into a digest.
    """
    if not videos:
        return "none", None

    fetched_urls = [v["url"] for v in videos]
    if entry["seen_urls"] is None:
        return "baseline", {"count": len(videos), "seen_urls": fetched_urls}

    seen = entry["seen_urls"]
    seen_set = set(seen)
    new = [v for v in videos if v["url"] not in seen_set]
    if not new:
        return "none", None
    return "new", {"videos": new, "seen_urls": [v["url"] for v in new] + seen}


def main():
    valid = ("add", "remove", "list")
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print("Usage: watchlist.py add <channel_url> | remove <handle> | list", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "add":
            if len(sys.argv) != 3:
                print("Usage: watchlist.py add <channel_url>", file=sys.stderr)
                sys.exit(1)
            print(f"OK @{add_channel(sys.argv[2])}")
        elif cmd == "remove":
            if len(sys.argv) != 3:
                print("Usage: watchlist.py remove <handle>", file=sys.stderr)
                sys.exit(1)
            remove_channel(sys.argv[2])
            print("OK")
        elif cmd == "list":
            entries = load_watchlist()
            if not entries:
                print("EMPTY")
                return
            for e in entries:
                seen = e["seen_urls"]
                cursor = "(none)" if seen is None else f"{len(seen)} videos"
                print(f"@{e['handle']}  {e['channel_url']}  seen={cursor}")
    except (ValueError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Persisted sync-xtimeline watchlist — one entry per watched X account: handle,
profile_url, and a last_seen_tweet_id cursor for incremental digesting.
Pure I/O + CRUD + diff logic here, no MCP/network calls — those live in
mcp_timeline_client.py and fetch_new_tweets.py.

Usage:
  python3 watchlist.py add <handle> <profile_url>
  python3 watchlist.py remove <handle>
  python3 watchlist.py list
"""
import json
import sys
from pathlib import Path
from typing import Optional

from config import get_data_dir


def _watchlist_path() -> Path:
    return Path(get_data_dir()) / "watchlist.json"


def load_watchlist() -> list[dict]:
    path = _watchlist_path()
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save_watchlist(entries: list[dict]) -> None:
    path = _watchlist_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")


def add_handle(handle: str, profile_url: str) -> None:
    entries = load_watchlist()
    if any(e["handle"] == handle for e in entries):
        raise ValueError(f"already watching @{handle}")
    entries.append({"handle": handle, "profile_url": profile_url, "last_seen_tweet_id": None})
    save_watchlist(entries)


def remove_handle(handle: str) -> None:
    entries = load_watchlist()
    remaining = [e for e in entries if e["handle"] != handle]
    if len(remaining) == len(entries):
        raise ValueError(f"not watching @{handle}")
    save_watchlist(remaining)


def set_last_seen(handle: str, tweet_id: str) -> None:
    entries = load_watchlist()
    for e in entries:
        if e["handle"] == handle:
            e["last_seen_tweet_id"] = tweet_id
            save_watchlist(entries)
            return
    raise ValueError(f"not watching @{handle}")


def compute_update(entry: dict, tweets: list[dict]) -> tuple[str, Optional[dict]]:
    """Pure diff: given a watchlist entry and freshly-fetched tweets
    (already sorted most-recent-first by tweet_id, per fetch_user_timeline's
    contract), decide what this run should report and persist. Never
    touches disk — callers persist the returned last_seen_tweet_id via
    set_last_seen()."""
    if not tweets:
        return "none", None
    if entry["last_seen_tweet_id"] is None:
        return "baseline", {"count": len(tweets), "last_seen_tweet_id": tweets[0]["tweet_id"]}
    last_seen = int(entry["last_seen_tweet_id"])
    newer = [t for t in tweets if int(t["tweet_id"]) > last_seen]
    if not newer:
        return "none", None
    return "new", {"tweets": newer, "last_seen_tweet_id": newer[0]["tweet_id"]}


def main():
    valid = ("add", "remove", "list")
    if len(sys.argv) < 2 or sys.argv[1] not in valid:
        print("Usage: watchlist.py add <handle> <profile_url> | remove <handle> | list", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    try:
        if cmd == "add":
            if len(sys.argv) != 4:
                print("Usage: watchlist.py add <handle> <profile_url>", file=sys.stderr)
                sys.exit(1)
            add_handle(sys.argv[2], sys.argv[3])
            print("OK")
        elif cmd == "remove":
            if len(sys.argv) != 3:
                print("Usage: watchlist.py remove <handle>", file=sys.stderr)
                sys.exit(1)
            remove_handle(sys.argv[2])
            print("OK")
        elif cmd == "list":
            entries = load_watchlist()
            if not entries:
                print("EMPTY")
                return
            for e in entries:
                cursor = e["last_seen_tweet_id"] or "(none)"
                print(f"@{e['handle']}  {e['profile_url']}  last_seen={cursor}")
    except ValueError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

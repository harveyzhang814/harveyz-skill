#!/usr/bin/env python3
"""Stage 1 for sync-xtimeline: for every watched handle, call fetch_user_timeline
via mcp_timeline_client, diff against each handle's last_seen_tweet_id
cursor (watchlist.compute_update), persist the updated cursor, and print
a JSON report to stdout for the orchestrating skill to translate and hand
to render_digest.py.

Usage: python3 fetch_new_tweets.py [chrome_profile]
"""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import watchlist
from config import get_data_dir
from mcp_timeline_client import fetch_timeline


def _timeline_url(profile_url: str) -> str:
    """Bare profile URLs (as stored by watchlist.add_handle) only show X's
    default Posts tab (posts + quotes) — /all is needed to also see
    reposts and replies (verified by manually probing a real profile)."""
    return profile_url.rstrip("/") + "/all"


async def run(chrome_profile: Optional[str]) -> dict:
    entries = watchlist.load_watchlist()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}

    for entry in entries:
        handle = entry["handle"]
        try:
            tweets = await fetch_timeline(_timeline_url(entry["profile_url"]), chrome_profile)
            kind, data = watchlist.compute_update(entry, tweets)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                new[handle] = data["tweets"]
            watchlist.set_last_seen(handle, data["last_seen_tweet_id"])
        except Exception as e:
            failures[handle] = str(e)
            continue

    return {
        "run_time": datetime.now(timezone.utc).isoformat(),
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }


def main():
    chrome_profile = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    report = asyncio.run(run(chrome_profile))

    pending_path = Path(get_data_dir()) / "pending.json"
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

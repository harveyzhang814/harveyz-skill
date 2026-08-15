#!/usr/bin/env python3
"""Stage 1 for watch-x: for every watched handle, call fetch_user_timeline
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
from typing import Optional

import watchlist
from mcp_timeline_client import fetch_timeline


async def run(chrome_profile: Optional[str]) -> dict:
    entries = watchlist.load_watchlist()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}

    for entry in entries:
        handle = entry["handle"]
        try:
            tweets = await fetch_timeline(entry["profile_url"], chrome_profile)
        except Exception as e:
            failures[handle] = str(e)
            continue

        kind, data = watchlist.compute_update(entry, tweets)
        if kind == "none":
            continue
        if kind == "baseline":
            baselines[handle] = data["count"]
        elif kind == "new":
            new[handle] = data["tweets"]
        watchlist.set_last_seen(handle, data["last_seen_tweet_id"])

    return {
        "run_time": datetime.now(timezone.utc).isoformat(),
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }


def main():
    chrome_profile = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    report = asyncio.run(run(chrome_profile))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()

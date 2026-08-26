#!/usr/bin/env python3
"""Stage 1 for sync-xtimeline: for every watched handle, call fetch_user_timeline
via mcp_timeline_client, diff against each handle's last_seen_tweet_id
cursor (cursor.compute_update, read from the roster), persist the updated cursor, and print
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

import cursor as cursor_mod
import roster_client
from config import get_data_dir
from mcp_timeline_client import fetch_timeline


def _timeline_url(profile_url: str) -> str:
    """Bare profile URLs (as stored on the roster) only show X's
    default Posts tab (posts + quotes) — /all is needed to also see
    reposts and replies (verified by manually probing a real profile)."""
    return profile_url.rstrip("/") + "/all"


async def run(chrome_profile: Optional[str]) -> dict:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}

    for channel in roster_client.channels():
        handle = channel["handle"]
        try:
            tweets = await fetch_timeline(_timeline_url(channel["url"]), chrome_profile)
            kind, data = cursor_mod.compute_update(roster_client.get_cursor(handle), tweets)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                new[handle] = data["tweets"]
            roster_client.set_cursor(handle, data["last_seen_tweet_id"], run_time)
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

    return {
        "run_time": run_time,
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

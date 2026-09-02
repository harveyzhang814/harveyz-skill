#!/usr/bin/env python3
"""Stage 1 for sync-xtimeline: for every watched handle, call fetch_user_timeline
via mcp_timeline_client, diff against each handle's last_seen_tweet_id
cursor (cursor.compute_update, read from the roster), and print a JSON
report to stdout for the orchestrating skill to translate and hand to
render_digest.py and then archive_tweets.py.

This step does NOT move the cursor. The value it should move to rides out
in the report's "cursors" field, and archive_tweets.py — the last stage —
writes it only after the digest and the archive are both on disk. So a
crash anywhere in the run means "this round never happened": the next run
re-fetches the same batch. The cost is redoing one round's fetch and
translation; what it buys is that no interruption can leave the cursor
parked past a batch nobody ever reported.

Usage: python3 fetch_new_tweets.py [chrome_profile] [--handle H [--handle H2 ...]]
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import cursor as cursor_mod
import roster_client
from mcp_timeline_client import fetch_timeline


def _timeline_url(profile_url: str) -> str:
    """Bare profile URLs (as stored on the roster) only show X's
    default Posts tab (posts + quotes) — /all is needed to also see
    reposts and replies (verified by manually probing a real profile)."""
    return profile_url.rstrip("/") + "/all"


def _select_channels(handles: Optional[list[str]]) -> tuple[list[dict], list[str]]:
    """No --handle means the full roster for this platform, unchanged. With
    --handle, only run those; any that aren't actually on the roster are
    reported back so the caller can surface them instead of silently no-op'ing."""
    channels = roster_client.channels()
    if not handles:
        return channels, []
    wanted = set(handles)
    selected = [c for c in channels if c["handle"] in wanted]
    found = {c["handle"] for c in selected}
    missing = [h for h in handles if h not in found]
    return selected, missing


async def run(chrome_profile: Optional[str], handles: Optional[list[str]] = None) -> dict:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}
    cursors: dict[str, str] = {}

    channels, missing = _select_channels(handles)
    for handle in missing:
        failures[handle] = "不在 roster 名册里"

    for channel in channels:
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
            cursors[handle] = data["last_seen_tweet_id"]
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

    return {
        "run_time": run_time,
        "new": new,
        "baselines": baselines,
        "failures": failures,
        "cursors": cursors,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome_profile", nargs="?", default=None)
    parser.add_argument(
        "--handle", action="append", dest="handles", default=None,
        help="只抓这个 handle（可重复传多次），不传则抓 roster 上这个平台的全部渠道",
    )
    return parser.parse_args()


def main(chrome_profile: Optional[str] = None, handles: Optional[list[str]] = None) -> None:
    report = asyncio.run(run(chrome_profile, handles))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    args = _parse_args()
    main(args.chrome_profile, args.handles)

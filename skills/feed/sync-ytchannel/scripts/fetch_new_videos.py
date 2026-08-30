#!/usr/bin/env python3
"""Stage 1 for sync-ytchannel: for every watched channel, call
fetch_channel_videos via mcp_channel_client, diff against that channel's
seen-URL cursor (cursor.compute_update, read from the roster), filter out
videos already archived, persist the advanced cursor, and print a JSON
report to stdout for the orchestrating skill to translate and hand to
digest.py.

This is the YouTube counterpart of sync-xtimeline's fetch_new_tweets.py —
same shape, including the pending.json crash-recovery handoff: cursor moves
immediately after a successful fetch, and the report is replayed verbatim
on the next call if digest.py never got to clear pending.json.

Usage: python3 fetch_new_videos.py [chrome_profile] [--handle H [--handle H2 ...]]
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cursor as cursor_mod
import roster_client
from archive_videos import _archive_path
from config import get_data_dir
from mcp_channel_client import fetch_channel_videos


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


def _archived_video_ids(handle: str) -> set[str]:
    path = _archive_path(handle)
    if not path.exists():
        return set()
    existing = json.loads(path.read_text(encoding="utf-8"))
    return {v["video_id"] for v in existing}


async def run(chrome_profile: Optional[str], handles: Optional[list[str]] = None) -> dict:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}

    channels, missing = _select_channels(handles)
    for handle in missing:
        failures[handle] = "不在 roster 名册里"

    for channel in channels:
        handle = channel["handle"]
        try:
            videos = await fetch_channel_videos(channel["url"], chrome_profile)
            kind, data = cursor_mod.compute_update(roster_client.get_cursor(handle), videos)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                fresh = [v for v in data["videos"] if v["video_id"] not in _archived_video_ids(handle)]
                if fresh:
                    new[handle] = fresh
            roster_client.set_cursor(handle, data["seen_urls"], run_time)
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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome_profile", nargs="?", default=None)
    parser.add_argument(
        "--handle", action="append", dest="handles", default=None,
        help="只抓这个频道（可重复传多次），不传则抓 roster 上这个平台的全部渠道",
    )
    return parser.parse_args()


def main(chrome_profile: Optional[str] = None, handles: Optional[list[str]] = None) -> None:
    pending_path = Path(get_data_dir()) / "youtube" / "pending.json"
    if pending_path.exists():
        print(pending_path.read_text(encoding="utf-8"))
        return

    report = asyncio.run(run(chrome_profile, handles))

    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    args = _parse_args()
    main(args.chrome_profile, args.handles)

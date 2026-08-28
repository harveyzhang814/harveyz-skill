#!/usr/bin/env python3
"""The `run` subcommand for sync-ytchannel: for every watched channel, call
fetch_channel_videos via mcp_channel_client, diff against that channel's
seen-URL cursor (cursor.compute_update, read from the roster), write a Markdown update log, and
only then persist the advanced cursors.

That ordering is the point of keeping fetch/render/persist in one script: if
the digest never lands on disk, the videos it would have reported stay
unreported and the next run picks them up again.

Usage: python3 sync_channels.py [chrome_profile] [--handle H [--handle H2 ...]]
Prints EMPTY, or WRITTEN: <path>.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cursor as cursor_mod
import digest
import roster_client
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


async def _collect(
    chrome_profile: Optional[str], handles: Optional[list[str]] = None
) -> tuple[dict, list[tuple[str, list[str]]]]:
    run_time = datetime.now(timezone.utc).isoformat()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}
    pending_cursors: list[tuple[str, list[str]]] = []

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
                new[handle] = data["videos"]
            pending_cursors.append((handle, data["seen_urls"]))
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

    report = {
        "run_time": run_time,
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }
    return report, pending_cursors


def collect(
    chrome_profile: Optional[str] = None, handles: Optional[list[str]] = None
) -> tuple[dict, list[tuple[str, list[str]]]]:
    return asyncio.run(_collect(chrome_profile, handles))


def write_digest(report: dict) -> Path:
    digests_dir = get_data_dir() / "digests" / "youtube"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    digest_path = digests_dir / f"{run_time.strftime('%Y%m%dT%H%M%S')}--digest.md"
    digest_path.write_text(digest.render_digest(report), encoding="utf-8")
    return digest_path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome_profile", nargs="?", default=None)
    parser.add_argument(
        "--handle", action="append", dest="handles", default=None,
        help="只抓这个 handle（可重复传多次），不传则抓 roster 上这个平台的全部渠道",
    )
    return parser.parse_args()


def main(chrome_profile: Optional[str] = None, handles: Optional[list[str]] = None) -> None:
    report, pending_cursors = collect(chrome_profile, handles)

    if not digest.has_content(report):
        print("EMPTY")
        return

    digest_path = write_digest(report)
    for handle, seen_urls in pending_cursors:
        roster_client.set_cursor(handle, seen_urls, report["run_time"])
    print(f"WRITTEN: {digest_path}")


if __name__ == "__main__":
    args = _parse_args()
    main(args.chrome_profile, args.handles)

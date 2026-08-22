#!/usr/bin/env python3
"""The `run` subcommand for sync-ytchannel: for every watched channel, call
fetch_channel_videos via mcp_channel_client, diff against that channel's
seen-URL cursor (watchlist.compute_update), write a Markdown update log, and
only then persist the advanced cursors.

That ordering is the point of keeping fetch/render/persist in one script: if
the digest never lands on disk, the videos it would have reported stay
unreported and the next run picks them up again.

Usage: python3 sync_channels.py [chrome_profile]
Prints EMPTY, or WRITTEN: <path>.
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import digest
import watchlist
from config import get_data_dir
from mcp_channel_client import fetch_channel_videos


async def _collect(chrome_profile: Optional[str]) -> tuple[dict, list[tuple[str, list[str]]]]:
    entries = watchlist.load_watchlist()
    new: dict[str, list[dict]] = {}
    baselines: dict[str, int] = {}
    failures: dict[str, str] = {}
    pending_cursors: list[tuple[str, list[str]]] = []

    for entry in entries:
        handle = entry["handle"]
        try:
            videos = await fetch_channel_videos(entry["channel_url"], chrome_profile)
            kind, data = watchlist.compute_update(entry, videos)
            if kind == "none":
                continue
            if kind == "baseline":
                baselines[handle] = data["count"]
            elif kind == "new":
                new[handle] = data["videos"]
            pending_cursors.append((handle, data["seen_urls"]))
        except Exception as e:
            failures[handle] = str(e)
            continue

    report = {
        "run_time": datetime.now(timezone.utc).isoformat(),
        "new": new,
        "baselines": baselines,
        "failures": failures,
    }
    return report, pending_cursors


def collect(chrome_profile: Optional[str] = None) -> tuple[dict, list[tuple[str, list[str]]]]:
    return asyncio.run(_collect(chrome_profile))


def write_digest(report: dict) -> Path:
    digests_dir = get_data_dir() / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    digest_path = digests_dir / f"{run_time.strftime('%Y%m%dT%H%M%S')}--digest.md"
    digest_path.write_text(digest.render_digest(report), encoding="utf-8")
    return digest_path


def main():
    chrome_profile = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None
    report, pending_cursors = collect(chrome_profile)

    if not digest.has_content(report):
        print("EMPTY")
        return

    digest_path = write_digest(report)
    for handle, seen_urls in pending_cursors:
        watchlist.set_seen_urls(handle, seen_urls)
    print(f"WRITTEN: {digest_path}")


if __name__ == "__main__":
    main()

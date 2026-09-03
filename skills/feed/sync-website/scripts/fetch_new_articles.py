#!/usr/bin/env python3
"""Stage 1 for sync-website: for every watched website channel, call
fetch_articles via articles_client, diff against that channel's seen-URL
cursor (cursor.compute_update, read from the roster), and print a JSON
report to stdout.

Unlike sync-ytchannel's fetch_new_videos.py, a channel whose fetch comes
back NO_RULE (articles_client.NoRuleError) or with zero articles is not
immediately a failure: it's recorded in report["needs_calibration"] instead,
left out of both report["failures"] and report["cursors"] for this run.
Writing a calibration rule needs a model reading the live page and
proposing selectors (see skills/feed/sync-website/SKILL.md's calibrate
procedure) — this script has no model access, so it cannot perform that
step itself. The orchestrating skill (a live Claude session, the same
place sync-ytchannel's run does its title-translation step) is responsible
for calibrating each channel in report["needs_calibration"], then
re-invoking this script with --handle <that channel> to fold a fresh diff
back into the overall report before handing it to digest.py — see
SKILL.md's run procedure.

Mirrors sync-ytchannel/scripts/fetch_new_videos.py otherwise, including
deferring the cursor: this step does NOT move it. The value it should move
to rides out in the report's "cursors" field, archived last by
archive_articles.py.

Usage: python3 fetch_new_articles.py [chrome_profile] [--handle H [--handle H2 ...]]
"""
import argparse
import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

import cursor as cursor_mod
import roster_client
from articles_client import fetch_articles, NoRuleError


def _select_channels(handles: Optional[list[str]]) -> tuple[list[dict], list[str]]:
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
    needs_calibration: dict[str, str] = {}
    cursors: dict[str, list[str]] = {}

    channels, missing = _select_channels(handles)
    for handle in missing:
        failures[handle] = "不在 roster 名册里"

    for channel in channels:
        handle = channel["handle"]
        list_url = channel["url"]
        try:
            articles = await fetch_articles(list_url, chrome_profile)
        except NoRuleError:
            needs_calibration[handle] = list_url
            continue
        except Exception as e:
            failures[handle] = str(e)
            roster_client.set_error(handle, str(e), run_time)
            continue

        if not articles:
            needs_calibration[handle] = list_url
            continue

        # cursor.compute_update's return key is literally named "videos"
        # (unmodified per this plan's Task 5 — no changes to cursor.py) even
        # though these are articles; it only ever reads each item's "url".
        kind, data = cursor_mod.compute_update(roster_client.get_cursor(handle), articles)
        if kind == "none":
            continue
        if kind == "baseline":
            baselines[handle] = data["count"]
        elif kind == "new":
            new[handle] = data["videos"]
        cursors[handle] = data["seen_urls"]

    return {
        "run_time": run_time,
        "new": new,
        "baselines": baselines,
        "failures": failures,
        "needs_calibration": needs_calibration,
        "cursors": cursors,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("chrome_profile", nargs="?", default=None)
    parser.add_argument(
        "--handle", action="append", dest="handles", default=None,
        help="只抓这个渠道（可重复传多次），不传则抓 roster 上这个平台的全部渠道",
    )
    return parser.parse_args()


def main(chrome_profile: Optional[str] = None, handles: Optional[list[str]] = None) -> None:
    report = asyncio.run(run(chrome_profile, handles))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    args = _parse_args()
    main(args.chrome_profile, args.handles)

#!/usr/bin/env python3
"""Archives sync-website's translated report into a per-handle JSON store
under website/creators/<handle>.json — mirrors
sync-ytchannel/scripts/archive_videos.py, deduping by `url` instead of
`video_id` (articles have no separate id field, per
docs/superpowers/specs/2026-09-02-sync-website-design.md §3.3).

Also the run's commit point: after the archive is on disk, this advances
each channel's cursor to the value fetch_new_articles.py parked in
report["cursors"]. Runs last, after digest.py, so a crash anywhere earlier
leaves the cursor untouched and the next run simply re-fetches.

Usage: python3 archive_articles.py < report.json
"""
import json
import sys
from pathlib import Path

import roster_client
from config import get_data_dir


def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "creators" / f"{handle}.json"


def archive_articles(report: dict) -> None:
    for handle, articles in report.get("new", {}).items():
        path = _archive_path(handle)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        seen_urls = {a["url"] for a in existing}
        for a in articles:
            if a["url"] not in seen_urls:
                existing.append(a)
                seen_urls.add(a["url"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def advance_cursors(report: dict) -> None:
    run_time = report["run_time"]
    for handle, value in report.get("cursors", {}).items():
        roster_client.set_cursor(handle, value, run_time)


def main():
    report = json.load(sys.stdin)
    archive_articles(report)
    advance_cursors(report)


if __name__ == "__main__":
    main()

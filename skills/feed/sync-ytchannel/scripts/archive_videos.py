#!/usr/bin/env python3
"""Archives sync-ytchannel's translated report into a per-handle JSON store
under youtube/creators/<handle>.json — the YouTube counterpart of
sync-xtimeline's archive_tweets.py. Reads the same translated report
digest.py consumes (fetch_new_videos.py's JSON, with the orchestrating
skill having added a "translated" field to each video in
report["new"][handle]); dedups by video_id, safe to re-run.

Also the run's commit point: after the archive is on disk, this advances
each channel's cursor to the value fetch_new_videos.py parked in
report["cursors"]. Runs last, after digest.py, so that a crash anywhere
earlier leaves the cursor untouched and the next run simply re-fetches.

Usage: python3 archive_videos.py < report.json
"""
import json
import sys
from pathlib import Path

import roster_client
from config import get_data_dir


def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "creators" / f"{handle}.json"


def archive_videos(report: dict) -> None:
    for handle, videos in report.get("new", {}).items():
        path = _archive_path(handle)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        seen_ids = {v["video_id"] for v in existing}
        for v in videos:
            if v["video_id"] not in seen_ids:
                existing.append(v)
                seen_ids.add(v["video_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def advance_cursors(report: dict) -> None:
    """推进游标——只有走到这里才推。抓取阶段不写游标，中途崩在任何一步游标
    都还停在原地，下一次运行会重抓同一批：代价是多写一份重复摘要，比游标先
    跑掉、那批再也抓不回来轻得多。"""
    run_time = report["run_time"]
    for handle, value in report.get("cursors", {}).items():
        roster_client.set_cursor(handle, value, run_time)


def main():
    report = json.load(sys.stdin)
    archive_videos(report)
    advance_cursors(report)


if __name__ == "__main__":
    main()

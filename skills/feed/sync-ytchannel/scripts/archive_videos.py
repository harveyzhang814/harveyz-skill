#!/usr/bin/env python3
"""Archives sync-ytchannel's translated report into a per-handle JSON store
under youtube/creators/<handle>.json — the YouTube counterpart of
sync-xtimeline's archive_tweets.py. Reads the same translated report
digest.py consumes (fetch_new_videos.py's JSON, with the orchestrating
skill having added a "translated" field to each video in
report["new"][handle]); dedups by video_id, safe to re-run.

Usage: python3 archive_videos.py < report.json
"""
import json
import sys
from pathlib import Path

from config import get_data_dir


def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "youtube" / "creators" / f"{handle}.json"


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


def main():
    report = json.load(sys.stdin)
    archive_videos(report)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Archives sync-xtimeline's translated report into a per-handle JSON store
under tweets/<handle>.json, so render_view.py can build a cumulative HTML
view across all runs. Reads the same translated report render_digest.py
consumes (fetch_new_tweets.py's JSON, with the orchestrating skill having
added a "translated" field to each tweet in report["new"][handle]); dedups
by tweet_id, safe to re-run.

Usage: python3 archive_tweets.py < report.json
"""
import json
import os
import sys
from pathlib import Path


def _data_dir() -> Path:
    env_dir = os.environ.get("HSKILL_SYNC_XTIMELINE_DATA_DIR")
    return Path(env_dir) if env_dir else Path.home() / ".hskill" / "sync-xtimeline"


def _archive_path(handle: str) -> Path:
    return _data_dir() / "tweets" / f"{handle}.json"


def archive_tweets(report: dict) -> None:
    for handle, tweets in report.get("new", {}).items():
        path = _archive_path(handle)
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
        seen_ids = {t["tweet_id"] for t in existing}
        for t in tweets:
            if t["tweet_id"] not in seen_ids:
                existing.append(t)
                seen_ids.add(t["tweet_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    report = json.load(sys.stdin)
    archive_tweets(report)


if __name__ == "__main__":
    main()

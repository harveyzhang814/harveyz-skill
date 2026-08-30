#!/usr/bin/env python3
"""Archives sync-xtimeline's translated report into a per-handle JSON store
under tweets/creators/<handle>.json. Reads the same translated report render_digest.py
consumes (fetch_new_tweets.py's JSON, with the orchestrating skill having
added a "translated" field to each tweet in report["new"][handle]); dedups
by tweet_id, safe to re-run.

Usage: python3 archive_tweets.py < report.json
"""
import json
import sys
from pathlib import Path

from config import get_data_dir


def _archive_path(handle: str) -> Path:
    return Path(get_data_dir()) / "tweets" / "creators" / f"{handle}.json"


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

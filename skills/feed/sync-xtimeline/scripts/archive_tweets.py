#!/usr/bin/env python3
"""Archives sync-xtimeline's translated report into a per-handle JSON store
under tweets/creators/<handle>.json. Reads the same translated report render_digest.py
consumes (fetch_new_tweets.py's JSON, with the orchestrating skill having
added a "translated" field to each tweet in report["new"][handle]); dedups
by tweet_id, safe to re-run.

Also the run's commit point: after the archive is on disk, this advances
each handle's cursor to the value fetch_new_tweets.py parked in
report["cursors"]. Runs last, after render_digest.py, so that a crash
anywhere earlier leaves the cursor untouched and the next run simply
re-fetches the batch.

Usage: python3 archive_tweets.py < report.json
"""
import json
import sys
from pathlib import Path

import roster_client
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


def advance_cursors(report: dict) -> None:
    """推进游标——只有走到这里才推。抓取阶段不写游标，中途崩在任何一步游标
    都还停在原地，下一次运行会重抓同一批：代价是多写一份重复摘要，比游标先
    跑掉、那批再也抓不回来轻得多。"""
    run_time = report["run_time"]
    for handle, value in report.get("cursors", {}).items():
        roster_client.set_cursor(handle, value, run_time)


def main():
    report = json.load(sys.stdin)
    archive_tweets(report)
    advance_cursors(report)


if __name__ == "__main__":
    main()

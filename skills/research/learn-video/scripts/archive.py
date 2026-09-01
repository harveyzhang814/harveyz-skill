#!/usr/bin/env python3
"""Archives learn-video's vdl output into the unified storage root: copies
the three vdl-produced files into <ROOT>/videos/<task_id>/ and writes
meta.json. Copies, never moves — vdl's own work/<task_id>/ must stay in
place for `vdl rerun` to keep working. Same task_id rerun overwrites in
place (shutil.copyfile always overwrites the destination), so this is
idempotent.

Parameters via environment variables:
  TASK_ID          - vdl's task_id (this skill's entity primary key)
  SOURCE_URL        - the video URL the user gave
  TITLE             - video title
  TRANSCRIPT_PATH   - vdl's transcript/original.md path
  ARTICLE_PATH      - vdl's writing/article.md path
  SUMMARY_PATH      - vdl's writing/summary.md path
  FETCHED_AT        - (optional) override date, defaults to today (UTC+8)
"""
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone

import store_config


def archive(task_id: str, source_url: str, title: str,
            transcript_path: str, article_path: str, summary_path: str,
            fetched_at: str | None = None) -> dict:
    video_dir = store_config.videos_dir() / task_id
    (video_dir / "transcript").mkdir(parents=True, exist_ok=True)
    (video_dir / "writing").mkdir(parents=True, exist_ok=True)

    dest_transcript = video_dir / "transcript" / "original.md"
    dest_article = video_dir / "writing" / "article.md"
    dest_summary = video_dir / "writing" / "summary.md"
    shutil.copyfile(transcript_path, dest_transcript)
    shutil.copyfile(article_path, dest_article)
    shutil.copyfile(summary_path, dest_summary)

    meta_path = video_dir / "meta.json"
    meta = {
        "source_url": source_url,
        "title": title,
        "fetched_at": fetched_at or datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "video_dir": video_dir,
        "meta_path": meta_path,
        "transcript_path": dest_transcript,
        "article_path": dest_article,
        "summary_path": dest_summary,
    }


def main():
    result = archive(
        task_id=os.environ["TASK_ID"],
        source_url=os.environ["SOURCE_URL"],
        title=os.environ["TITLE"],
        transcript_path=os.environ["TRANSCRIPT_PATH"],
        article_path=os.environ["ARTICLE_PATH"],
        summary_path=os.environ["SUMMARY_PATH"],
        fetched_at=os.environ.get("FETCHED_AT"),
    )
    print(f"VIDEO_DIR: {result['video_dir']}")
    print(f"META_PATH: {result['meta_path']}")


if __name__ == "__main__":
    main()

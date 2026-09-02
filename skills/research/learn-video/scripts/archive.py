#!/usr/bin/env python3
"""Writes meta.json into vdl's task directory, marking it as an entity in
the unified storage root. vdl's WORK_ROOT points at <ROOT>/videos, so its
work/<task_id>/ already IS the final location — nothing is copied.

The extra "work" segment is vdl's own layout (core/paths.js hardcodes it
under WORK_ROOT and builds database.sqlite / index.jsonl on top of it, so
it isn't ours to drop). See
docs/superpowers/specs/2026-09-01-unified-store-design.md §5.2.

Parameters via environment variables:
  TASK_ID     - vdl's task_id (this skill's entity primary key)
  SOURCE_URL  - the video URL the user gave
  TITLE       - video title
  FETCHED_AT  - (optional) override date, defaults to today (UTC+8)
"""
import json
import os
from datetime import datetime, timedelta, timezone

import store_config


def archive(task_id: str, source_url: str, title: str,
            fetched_at: str | None = None) -> dict:
    videos_dir = store_config.videos_dir()
    video_dir = videos_dir / "work" / task_id
    if not video_dir.is_dir():
        raise FileNotFoundError(
            f"任务目录不存在：{video_dir}\n"
            f"vdl 的 WORK_ROOT 没有指向 {videos_dir}。\n"
            f"修复：vdl config set work-root {videos_dir}"
        )

    meta_path = video_dir / "meta.json"
    meta = {
        "source_url": source_url,
        "title": title,
        "fetched_at": fetched_at or datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"video_dir": video_dir, "meta_path": meta_path}


def main():
    try:
        result = archive(
            task_id=os.environ["TASK_ID"],
            source_url=os.environ["SOURCE_URL"],
            title=os.environ["TITLE"],
            fetched_at=os.environ.get("FETCHED_AT"),
        )
    except FileNotFoundError as e:
        raise SystemExit(str(e))
    print(f"VIDEO_DIR: {result['video_dir']}")
    print(f"META_PATH: {result['meta_path']}")


if __name__ == "__main__":
    main()

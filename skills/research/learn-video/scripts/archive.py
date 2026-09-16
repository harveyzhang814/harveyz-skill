#!/usr/bin/env python3
"""Validates vdl's meta.json against the unified store's required contract
fields. Writing meta.json is vdl's job now — vdl's own database.sqlite is
the source of truth for uploader_id/channel_id/uploader_url and the display
fields scholia reads (url/uploader/upload_date/duration/mode/output_lang/ts).
See docs/superpowers/specs/2026-09-15-video-creator-index-design.md §1.3.

Parameters via environment variables:
  TASK_ID - vdl's task_id (this skill's entity primary key)
"""
import json
import os

import store_config

REQUIRED_FIELDS = ("source_url", "title", "fetched_at")


def archive(task_id: str) -> dict:
    videos_dir = store_config.videos_dir()
    video_dir = videos_dir / "work" / task_id
    if not video_dir.is_dir():
        raise FileNotFoundError(
            f"任务目录不存在：{video_dir}\n"
            f"vdl 的 WORK_ROOT 没有指向 {videos_dir}。\n"
            f"修复：vdl config set work-root {videos_dir}"
        )

    meta_path = video_dir / "meta.json"
    if not meta_path.is_file():
        raise SystemExit(
            f"meta.json 不存在：{meta_path}\n"
            f"vdl 尚未写入 meta.json——任务可能还没跑到 completed。"
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_FIELDS if not meta.get(f)]
    if missing:
        raise SystemExit(
            f"meta.json 缺少统一存储契约必填字段：{', '.join(missing)}\n{meta_path}"
        )

    return {"video_dir": video_dir, "meta_path": meta_path}


def main():
    try:
        result = archive(task_id=os.environ["TASK_ID"])
    except FileNotFoundError as e:
        raise SystemExit(str(e))
    print(f"VIDEO_DIR: {result['video_dir']}")
    print(f"META_PATH: {result['meta_path']}")


if __name__ == "__main__":
    main()

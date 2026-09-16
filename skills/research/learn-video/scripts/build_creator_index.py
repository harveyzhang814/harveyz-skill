#!/usr/bin/env python3
"""Builds <knowledgeRoot>/videos/creators.json — vdl's video entities grouped
by normalized uploader handle. Never reads registry.json: matching a handle
to "am I watching this person" is scholia's job at read time (judgment isn't
stored next to fact — see
docs/superpowers/specs/2026-09-15-video-creator-index-design.md §0, §3.3).

Usage:
  python3 build_creator_index.py build   # full rebuild, atomic write
  python3 build_creator_index.py check   # compare index vs disk, exit 1 if stale
"""
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import store_config


def _normalize_handle(uploader_id: str) -> str:
    return uploader_id.lstrip("@").strip().lower()


def build_index(work_dir: Path) -> dict:
    creators: dict[str, dict] = {}
    unresolved: dict[str, dict] = {}
    scanned = 0

    for meta_path in sorted(work_dir.glob("*/meta.json")):
        task_id = meta_path.parent.name
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        scanned += 1

        video_entry = {
            "task_id": task_id,
            "title": meta.get("title", ""),
            "upload_date": meta.get("upload_date", ""),
            "duration": meta.get("duration", ""),
        }

        uploader_id = (meta.get("uploader_id") or "").strip()
        if uploader_id:
            key = _normalize_handle(uploader_id)
            entry = creators.setdefault(key, {
                "key": key,
                "display_name": meta.get("uploader") or key,
                "channel_id": meta.get("channel_id") or "",
                "uploader_url": meta.get("uploader_url") or "",
                "videos": [],
            })
            if not entry["channel_id"] and meta.get("channel_id"):
                entry["channel_id"] = meta["channel_id"]
            if not entry["uploader_url"] and meta.get("uploader_url"):
                entry["uploader_url"] = meta["uploader_url"]
            if meta.get("uploader"):
                entry["display_name"] = meta["uploader"]
            entry["videos"].append(video_entry)
        else:
            display_name = meta.get("uploader") or meta.get("title") or task_id
            entry = unresolved.setdefault(display_name, {
                "display_name": display_name,
                "task_ids": [],
            })
            entry["task_ids"].append(task_id)

    return {
        "schema_version": 1,
        "built_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        "scanned": {"entities": scanned},
        "creators": sorted(creators.values(), key=lambda c: c["key"]),
        "unresolved": sorted(unresolved.values(), key=lambda u: u["display_name"]),
    }


def write_index(index: dict, output_path: Path) -> None:
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_path.rename(output_path)


def check_index(work_dir: Path, index_path: Path) -> tuple[bool, str]:
    disk_count = len(list(work_dir.glob("*/meta.json")))
    if not index_path.is_file():
        return False, f"STALE: 索引缺失（{index_path}），磁盘 {disk_count} 条"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    indexed_count = index.get("scanned", {}).get("entities", 0)
    if indexed_count != disk_count:
        return False, f"STALE: 索引 {indexed_count} 条 / 磁盘 {disk_count} 条"
    return True, f"OK: 索引 {indexed_count} 条，与磁盘一致"


def main():
    parser = argparse.ArgumentParser(description="构建/核对 learn-video 的 creator 索引")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build")
    sub.add_parser("check")
    args = parser.parse_args()

    videos_dir = store_config.videos_dir()
    work_dir = videos_dir / "work"
    index_path = videos_dir / "creators.json"

    if args.command == "build":
        index = build_index(work_dir)
        write_index(index, index_path)
        print(
            f"已写入 {index_path}：{len(index['creators'])} 位 creator，"
            f"{len(index['unresolved'])} 组 unresolved，"
            f"共 {index['scanned']['entities']} 条实体"
        )
    elif args.command == "check":
        ok, message = check_index(work_dir, index_path)
        print(message)
        if not ok:
            raise SystemExit(1)


if __name__ == "__main__":
    main()

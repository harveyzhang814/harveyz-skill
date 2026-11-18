#!/usr/bin/env python3
"""Markdown rendering + CLI for sync-ytchannel's digest — the YouTube
counterpart of sync-xtimeline's render_digest.py. Reads a translated report
from stdin (`feedr sync fetch youtube`'s JSON, with the orchestrating skill having
added a "translated" field to each video in report["new"][handle]) and
writes it to disk, but only when there's something to report (new videos,
freshly-established baselines, or failures).

Usage: python3 digest.py < report.json
The digest is written to <report["archive_dir"]>/digest/ (archive_dir comes
from `feedr sync fetch youtube`). Prints EMPTY, or WRITTEN: <path>.
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def has_content(report: dict) -> bool:
    return bool(report.get("new") or report.get("failures") or report.get("baselines"))


def format_date(video: dict) -> str:
    """The exact publish timestamp when the uploads feed covered this video,
    otherwise the grid's relative wording ("2 weeks ago") verbatim — never a
    date guessed from it."""
    published_at = video.get("published_at")
    if published_at:
        return published_at
    return video.get("published_text") or "日期未知"


def render_digest(report: dict) -> str:
    lines = [f"# YouTube 追更摘要 — {report['run_time']}", ""]

    for handle, videos in report.get("new", {}).items():
        lines.append(f"## @{handle}")
        for v in videos:
            text = v.get("translated") or v["title"]
            lines.append(f"- [{format_date(v)}] {text}（[原文]({v['url']})）")
        lines.append("")

    failures = report.get("failures", {})
    if failures:
        lines.append("## 失败")
        for handle, error in failures.items():
            lines.append(f"- @{handle}：{error}")
        lines.append("")

    baselines = report.get("baselines", {})
    if baselines:
        lines.append("## 已建立追踪基线")
        for handle, count in baselines.items():
            lines.append(f"- @{handle}：起始 {count} 个视频，从下次运行开始报告新增")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    report = json.load(sys.stdin)
    if not has_content(report):
        print("EMPTY")
        return

    if "archive_dir" not in report:
        print("digest.py: report 缺少 archive_dir（应来自 feedr sync fetch youtube）", file=sys.stderr)
        sys.exit(1)
    digests_dir = Path(report["archive_dir"]) / "digest"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    timestamp = run_time.strftime("%Y%m%dT%H%M%S")
    digest_path = digests_dir / f"digest-{timestamp}.md"
    digest_path.write_text(render_digest(report), encoding="utf-8")
    print(f"WRITTEN: {digest_path}")


if __name__ == "__main__":
    main()

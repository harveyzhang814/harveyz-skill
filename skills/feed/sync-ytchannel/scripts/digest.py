#!/usr/bin/env python3
"""Markdown rendering for sync-ytchannel's update log. Pure functions only —
sync_channels.py owns the file writing.

Video titles come from a third party and are only ever rendered as text; this
module never interprets them.
"""


def has_content(report: dict) -> bool:
    return bool(report.get("new") or report.get("failures") or report.get("baselines"))


def format_date(video: dict) -> str:
    """The exact publish date when the uploads feed covered this video,
    otherwise the grid's relative wording ("2 weeks ago") verbatim — never a
    date guessed from it."""
    published_at = video.get("published_at")
    if published_at:
        return published_at[:10]
    return video.get("published_text") or "日期未知"


def render_digest(report: dict) -> str:
    lines = [f"# YouTube 追更摘要 — {report['run_time']}", ""]

    for handle, videos in report.get("new", {}).items():
        lines.append(f"## @{handle}")
        for v in videos:
            lines.append(f"- [{format_date(v)}] {v['title']}（{v['url']}）")
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

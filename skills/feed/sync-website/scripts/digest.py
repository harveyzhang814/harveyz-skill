#!/usr/bin/env python3
"""Markdown rendering + CLI for sync-website's digest — mirrors
sync-ytchannel/scripts/digest.py, with one addition: a channel that was
recalibrated mid-run (see fetch_new_articles.py's docstring and
SKILL.md's run procedure) gets an explicit tag on its heading, per
docs/superpowers/specs/2026-09-02-sync-website-design.md §4.3 — without
it, a silently-changed selector extracting nav links instead of articles
would look like a normal digest.

Usage: python3 digest.py < report.json
Prints EMPTY, or WRITTEN: <path>.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from config import get_data_dir


def has_content(report: dict) -> bool:
    return bool(report.get("new") or report.get("failures") or report.get("baselines"))


def format_date(article: dict) -> str:
    """The exact timestamp when date_text parsed to one, otherwise the raw
    date_text verbatim — never a date guessed from it (spec §5)."""
    published_at = article.get("published_at")
    if published_at:
        return published_at
    return article.get("date_text") or "日期未知"


def render_digest(report: dict) -> str:
    lines = [f"# 网站追更摘要 — {report['run_time']}", ""]
    recalibrated = set(report.get("recalibrated", []))

    for handle, articles in report.get("new", {}).items():
        tag = "  [本轮重新标定过抽取规则]" if handle in recalibrated else ""
        lines.append(f"## {handle}{tag}")
        for a in articles:
            text = a.get("translated") or a["title"]
            lines.append(f"- [{format_date(a)}] {text}（[原文]({a['url']})）")
        lines.append("")

    failures = report.get("failures", {})
    if failures:
        lines.append("## 失败")
        for handle, error in failures.items():
            lines.append(f"- {handle}：{error}")
        lines.append("")

    baselines = report.get("baselines", {})
    if baselines:
        lines.append("## 已建立追踪基线")
        for handle, count in baselines.items():
            tag = "  [本轮重新标定过抽取规则]" if handle in recalibrated else ""
            lines.append(f"- {handle}{tag}：起始 {count} 篇文章，从下次运行开始报告新增")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    report = json.load(sys.stdin)
    if not has_content(report):
        print("EMPTY")
        return

    digests_dir = Path(get_data_dir()) / "digest"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    timestamp = run_time.strftime("%Y%m%dT%H%M%S")
    digest_path = digests_dir / f"digest-{timestamp}.md"
    digest_path.write_text(render_digest(report), encoding="utf-8")
    print(f"WRITTEN: {digest_path}")


if __name__ == "__main__":
    main()

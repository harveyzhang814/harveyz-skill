#!/usr/bin/env python3
"""Stage 2 for watch-x: renders a Markdown digest from a translated report
(fetch_new_tweets.py's JSON, with the orchestrating skill having added a
"translated" field to each tweet in report["new"][handle]) and writes it
to disk — but only when there's something to report (new tweets, freshly-
established baselines, or failures).

Usage: python3 render_digest.py < report.json
Prints EMPTY, or WRITTEN: <path>.
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def _data_dir() -> Path:
    env_dir = os.environ.get("HSKILL_WATCH_X_DATA_DIR")
    return Path(env_dir) if env_dir else Path.home() / ".hskill" / "watch-x"


def has_content(report: dict) -> bool:
    return bool(report.get("new") or report.get("failures") or report.get("baselines"))


def render_digest(report: dict) -> str:
    lines = [f"# X 追更摘要 — {report['run_time']}", ""]

    for handle, tweets in report.get("new", {}).items():
        lines.append(f"## @{handle}")
        for t in tweets:
            lines.append(f"- [{t['timestamp']}] {t['translated']}（[原文]({t['url']})）")
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
            lines.append(f"- @{handle}：起始 {count} 条推文，从下次运行开始报告新增")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main():
    report = json.load(sys.stdin)
    if not has_content(report):
        print("EMPTY")
        return

    digests_dir = _data_dir() / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    timestamp = run_time.strftime("%Y%m%dT%H%M%S")
    digest_path = digests_dir / f"{timestamp}--digest.md"
    digest_path.write_text(render_digest(report), encoding="utf-8")
    print(f"WRITTEN: {digest_path}")


if __name__ == "__main__":
    main()

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


def _type_suffix(t: dict, handle: str) -> str:
    """A short "（...）" tag describing what kind of activity this is,
    based on fetch_user_timeline's type classification — reliable per-type
    signals (socialContext text, a second User-Name block, "Replying to"
    text), not a guess from author_handle alone."""
    ttype = t.get("type", "post")

    if ttype == "repost":
        author_handle = (t.get("author_handle") or "").lstrip("@")
        if author_handle and author_handle != handle:
            return f"（转推自 {t.get('author_handle', '')}）"
        return "（转推）"

    if ttype == "reply":
        reply_to = t.get("reply_to_handle")
        return f"（回复 {reply_to}）" if reply_to else "（回复）"

    if ttype == "quote":
        quoted_author = t.get("quoted_author") or ""
        quoted_text = t.get("quoted_text") or ""
        if quoted_author and quoted_text:
            return f"（引用 {quoted_author}：{quoted_text}）"
        if quoted_author:
            return f"（引用 {quoted_author}）"
        return "（引用推文）"

    return ""


def render_digest(report: dict) -> str:
    lines = [f"# X 追更摘要 — {report['run_time']}", ""]

    for handle, tweets in report.get("new", {}).items():
        lines.append(f"## @{handle}")
        for t in tweets:
            suffix = _type_suffix(t, handle)
            lines.append(f"- [{t['timestamp']}] {t.get('translated') or t.get('text', '')}{suffix}（[原文]({t['url']})）")
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


def _clear_pending() -> None:
    pending_path = _data_dir() / "pending.json"
    pending_path.unlink(missing_ok=True)


def main():
    report = json.load(sys.stdin)
    if not has_content(report):
        print("EMPTY")
        _clear_pending()
        return

    digests_dir = _data_dir() / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    run_time = datetime.fromisoformat(report["run_time"])
    timestamp = run_time.strftime("%Y%m%dT%H%M%S")
    digest_path = digests_dir / f"{timestamp}--digest.md"
    digest_path.write_text(render_digest(report), encoding="utf-8")
    print(f"WRITTEN: {digest_path}")
    _clear_pending()


if __name__ == "__main__":
    main()

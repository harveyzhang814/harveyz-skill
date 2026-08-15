#!/usr/bin/env python3
"""Renders a cumulative, self-contained static HTML view of every tweet
archive_tweets.py has ever persisted, grouped by handle (alphabetical) and
sorted newest-first (by tweet_id) within each group. Reuses render_digest's
type-suffix logic so post/repost/quote/reply annotations stay consistent
between the per-run Markdown digest and this cumulative view.

Usage: python3 render_view.py
Prints EMPTY, or WRITTEN: <path>.
"""
import json
import os
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_digest import _type_suffix  # noqa: E402


def _data_dir() -> Path:
    env_dir = os.environ.get("HSKILL_SYNC_XTIMELINE_DATA_DIR")
    return Path(env_dir) if env_dir else Path.home() / ".hskill" / "sync-xtimeline"


def _tweets_dir() -> Path:
    return _data_dir() / "tweets"


def load_archives() -> dict[str, list[dict]]:
    tweets_dir = _tweets_dir()
    if not tweets_dir.exists():
        return {}
    archives = {}
    for path in sorted(tweets_dir.glob("*.json")):
        handle = path.stem
        tweets = json.loads(path.read_text(encoding="utf-8"))
        archives[handle] = sorted(tweets, key=lambda t: int(t["tweet_id"]), reverse=True)
    return archives


def render_view(archives: dict[str, list[dict]]) -> str:
    sections = []
    for handle in sorted(archives):
        items = []
        for t in archives[handle]:
            suffix = _type_suffix(t, handle)
            text = escape(t.get("translated") or t.get("text", ""))
            items.append(
                f'<li><span class="ts">{escape(t["timestamp"])}</span> '
                f'{text}{escape(suffix)} '
                f'<a href="{escape(t["url"])}">原文</a></li>'
            )
        sections.append(f'<section><h2>@{escape(handle)}</h2><ul>{"".join(items)}</ul></section>')

    body = "".join(sections) if sections else "<p>暂无归档推文。</p>"
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>X 追更历史</title>
<style>
body {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #1a1a1a; }}
h2 {{ border-bottom: 1px solid #ddd; padding-bottom: 0.3rem; }}
ul {{ list-style: none; padding: 0; }}
li {{ padding: 0.5rem 0; border-bottom: 1px solid #eee; }}
.ts {{ color: #888; font-size: 0.85rem; margin-right: 0.5rem; }}
a {{ color: #1d9bf0; text-decoration: none; }}
</style>
</head>
<body>
<h1>X 追更历史</h1>
{body}
</body>
</html>
"""


def main():
    archives = load_archives()
    if not any(archives.values()):
        print("EMPTY")
        return
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    view_path = data_dir / "view.html"
    view_path.write_text(render_view(archives), encoding="utf-8")
    print(f"WRITTEN: {view_path}")


if __name__ == "__main__":
    main()

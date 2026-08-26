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
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import get_data_dir
from render_digest import _type_suffix  # noqa: E402

# X-style palette used for avatar placeholders (no external images).
_AVATAR_COLORS = [
    "#e0245e", "#17bf63", "#794bc4", "#f45d22",
    "#1da1f2", "#ff7a59", "#ffad1f", "#0f9d58",
]

PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="color-scheme" content="dark">
<title>X 追更历史</title>
<style>
{css}
</style>
</head>
<body>
<header class="topbar">X 追更历史</header>
<main>
{body}
</main>
</body>
</html>
"""

CSS = """
:root {
  color-scheme: dark;
  --bg: #000000;
  --text: #e7e9ea;
  --secondary: #71767b;
  --border: #2f3336;
  --accent: #1d9bf0;
  --topbar-bg: rgba(0, 0, 0, 0.65);
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  max-width: 600px;
  margin: 0 auto;
  padding: 0 0 2rem;
  color: var(--text);
  background: var(--bg);
}
header.topbar {
  position: sticky; top: 0; z-index: 10;
  background: var(--topbar-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0.9rem 1rem;
  font-size: 1.15rem;
  font-weight: 800;
}
main { padding: 0 1rem; }
h2.handle {
  font-size: 1.05rem;
  font-weight: 800;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--border);
  margin-top: 1.5rem;
}
.timeline { display: flex; flex-direction: column; }
article.tweet { border-bottom: 1px solid var(--border); padding: 0.7rem 0; }
.caption { font-size: 0.8rem; font-weight: 700; color: var(--secondary); margin: 0 0 0.4rem calc(2.5rem + 0.75rem); }
.tweet-row { display: flex; gap: 0.75rem; }
.avatar {
  flex: 0 0 auto;
  width: 2.5rem; height: 2.5rem;
  border-radius: 50%;
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 1rem;
}
.tweet-main { flex: 1 1 auto; min-width: 0; padding-top: 0.05rem; }
.tweet-header { display: flex; align-items: baseline; gap: 0.35rem; flex-wrap: wrap; }
.tweet-header .name { font-weight: 800; font-size: 0.95rem; color: var(--text); }
.tweet-header .ts { color: var(--secondary); font-size: 0.9rem; text-decoration: none; }
.tweet-header .ts::before { content: "·"; margin-right: 0.35rem; }
.tweet-header .ts:hover { text-decoration: underline; }
.reply-to { color: var(--secondary); font-size: 0.9rem; margin: 0.05rem 0 0.25rem; }
.tweet-text { font-size: 0.95rem; line-height: 1.5; margin: 0.15rem 0 0.5rem; white-space: pre-wrap; }
.quote-card {
  border: 1px solid var(--border);
  border-radius: 0.9rem;
  padding: 0.6rem 0.8rem;
  margin: 0.2rem 0 0.5rem;
}
.quote-card .header { display: flex; align-items: center; gap: 0.4rem; }
.quote-card .mini-avatar {
  flex: 0 0 auto;
  width: 1.1rem; height: 1.1rem;
  border-radius: 50%;
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 0.65rem;
}
.quote-card .name { font-weight: 700; font-size: 0.85rem; color: var(--text); }
.quote-card .ts { color: var(--secondary); font-size: 0.8rem; }
.quote-card .ts::before { content: "·"; margin-right: 0.3rem; }
.quote-card .text { font-size: 0.85rem; line-height: 1.4; margin-top: 0.2rem; color: var(--text); }
.handle-meta { color: var(--secondary); font-size: 0.85rem; font-weight: 400; margin-left: 0.4rem; }
.empty { color: var(--secondary); padding: 2rem 0; }
"""


def _tweets_dir() -> Path:
    return Path(get_data_dir()) / "tweets"


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


def _format_timestamp(raw: str, now: datetime) -> str:
    """X-style absolute/relative display: minutes/hours within a day,
    "M月D日" within the current year, else "Y年M月D日". Falls back to the
    raw string for anything that isn't a parseable ISO timestamp (e.g. the
    "t1"-style placeholders used in unit tests)."""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    seconds = delta.total_seconds()
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{int(seconds // 60)}分钟"
    if seconds < 86400:
        return f"{int(seconds // 3600)}小时"
    if dt.year == now.year:
        return f"{dt.month}月{dt.day}日"
    return f"{dt.year}年{dt.month}月{dt.day}日"


def _avatar_color(handle: str) -> str:
    return _AVATAR_COLORS[sum(ord(c) for c in handle) % len(_AVATAR_COLORS)]


def _avatar_html(handle: str) -> str:
    initial = escape(handle[:1].upper()) if handle else "?"
    color = _avatar_color(handle)
    return f'<div class="avatar" style="background:{color}">{initial}</div>'

def _quote_card_html(t: dict, now: datetime) -> str:
    quoted_author = t.get("quoted_author")
    if not quoted_author:
        return ""
    quoted_text = escape(t.get("quoted_text") or "")
    quoted_ts = escape(_format_timestamp(t.get("quoted_timestamp") or "", now))
    initial = escape(quoted_author.lstrip("@")[:1].upper() or "?")
    color = _avatar_color(quoted_author)
    return (
        f'<div class="quote-card">'
        f'<div class="header">'
        f'<div class="mini-avatar" style="background:{color}">{initial}</div>'
        f'<span class="name">{escape(quoted_author)}</span>'
        f'<span class="ts">{quoted_ts}</span>'
        f'</div>'
        f'<div class="text">{quoted_text}</div>'
        f'</div>'
    )


def _caption_html(t: dict, handle: str) -> str:
    if t.get("type") == "repost":
        return f'<div class="caption">🔁 @{escape(handle)} 转推了</div>'
    return ""


def _reply_to_html(t: dict) -> str:
    if t.get("type") == "reply" and t.get("reply_to_handle"):
        return f'<div class="reply-to">回复 {escape(t["reply_to_handle"])}</div>'
    return ""


def _tweet_card_html(t: dict, handle: str, now: datetime) -> str:
    suffix = "" if t.get("type") in ("repost", "reply", "quote") else _type_suffix(t, handle)
    text = escape(t.get("translated") or t.get("text", "")) + escape(suffix)
    if t.get("type") == "repost" and t.get("author_handle"):
        header_name = t["author_handle"]
    else:
        header_name = f"@{handle}"
    return (
        f'<article class="tweet type-{escape(t.get("type", "post"))}">'
        f'{_caption_html(t, handle)}'
        f'<div class="tweet-row">'
        f'{_avatar_html(handle)}'
        f'<div class="tweet-main">'
        f'<div class="tweet-header">'
        f'<span class="name">{escape(header_name)}</span>'
        f'<a class="ts" href="{escape(t["url"])}">{escape(_format_timestamp(t["timestamp"], now))}</a>'
        f'</div>'
        f'{_reply_to_html(t)}'
        f'<div class="tweet-text">{text}</div>'
        f'{_quote_card_html(t, now)}'
        f'</div>'
        f'</div>'
        f'</article>'
    )


def render_view(archives: dict[str, list[dict]]) -> str:
    now = datetime.now(timezone.utc)
    sections = []
    for handle in sorted(archives):
        cards = "".join(_tweet_card_html(t, handle, now) for t in archives[handle])
        sections.append(
            f'<section><h2 class="handle">@{escape(handle)}'
            f'<span class="handle-meta">{len(archives[handle])} 条归档</span></h2>'
            f'<div class="timeline">{cards}</div></section>'
        )

    body = "".join(sections) if sections else '<p class="empty">暂无归档推文。</p>'
    return PAGE_TEMPLATE.format(css=CSS, body=body)


def main():
    archives = load_archives()
    if not any(archives.values()):
        print("EMPTY")
        return
    data_dir = Path(get_data_dir())
    data_dir.mkdir(parents=True, exist_ok=True)
    view_path = data_dir / "view.html"
    view_path.write_text(render_view(archives), encoding="utf-8")
    print(f"WRITTEN: {view_path}")


if __name__ == "__main__":
    main()

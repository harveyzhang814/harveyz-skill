"""把 sync-xtimeline / sync-ytchannel 各自的 watchlist.json 迁进名册。

一次性动作，但做成幂等的：已存在的渠道跳过，不抛错。重复执行不该把人卡在
半路。

不猜跨平台身份——karpathy 和 AndrejKarpathy 是同一个人这件事，是判断，
由用户跑 registry merge 决定。
"""
from pathlib import Path

from . import registry, state

_SOURCES = (
    # (旧字段名: url, 旧字段名: cursor, platform, cursor_type)
    ("profile_url", "last_seen_tweet_id", "x", "last_seen_id"),
    ("channel_url", "seen_urls", "youtube", "seen_urls"),
)


def from_watchlists(data_dir: Path, x_watchlist: list[dict] | None,
                    yt_watchlist: list[dict] | None,
                    today: str, run_time: str) -> dict:
    reg = registry.load(data_dir)
    st = state.load(data_dir)
    counts = {"creators": 0, "channels": 0, "cursors": 0}

    for entries, (url_field, cursor_field, platform, cursor_type) in zip(
            (x_watchlist, yt_watchlist), _SOURCES):
        for entry in entries or []:
            handle = entry["handle"]
            if registry.find_channel(reg, platform, handle) is not None:
                continue

            registry.add_channel(reg, entry[url_field], today)
            counts["creators"] += 1
            counts["channels"] += 1

            cursor_value = entry.get(cursor_field)
            if cursor_value is not None:
                state.set_cursor(st, platform, handle, cursor_type, cursor_value, run_time)
                counts["cursors"] += 1

    registry.save(data_dir, reg)
    state.save(data_dir, st)
    return counts

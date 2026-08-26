#!/usr/bin/env python3
"""sync-ytchannel 的增量判定，纯函数：不碰磁盘、不碰网络。关注列表现在归
roster 名册管（见 roster_client.py），这里只剩「拿游标和新抓的列表算差集」。

游标是 URL 集合而不是单个 last_seen id：X 的 snowflake tweet id 按时间
递增可以比大小，YouTube 的 video id 不透明，只能判断「见过没有」。
"""


def compute_update(seen_urls: list[str] | None, videos: list[dict]) -> tuple[str, dict | None]:
    """给定该频道已报告过的 URL 列表和刚抓到的视频（最新在前，
    fetch_channel_videos 的契约），决定本次报什么、存什么。

    seen_urls 为 None 只出现在首次成功抓取之前；那一次建立基线（全部记录、
    一条不报），而不是把整个历史片库倒进摘要。空列表跟 None 不同——那表示
    抓到过但当时一个视频都没有。
    """
    if not videos:
        return "none", None

    fetched_urls = [v["url"] for v in videos]
    if seen_urls is None:
        return "baseline", {"count": len(videos), "seen_urls": fetched_urls}

    seen_set = set(seen_urls)
    new = [v for v in videos if v["url"] not in seen_set]
    if not new:
        return "none", None
    return "new", {"videos": new, "seen_urls": [v["url"] for v in new] + seen_urls}

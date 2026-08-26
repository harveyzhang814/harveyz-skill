#!/usr/bin/env python3
"""sync-xtimeline 的增量判定，纯函数：不碰磁盘、不碰网络。关注列表现在归
roster 名册管（见 roster_client.py），这里只剩「拿游标和新抓的推文算差集」。

游标能用单个 id，是因为 X 的 snowflake tweet id 按时间单调递增可以比大小。
YouTube 的 video id 不透明，那边用的是 URL 集合。
"""


def compute_update(last_seen_tweet_id: str | None,
                   tweets: list[dict]) -> tuple[str, dict | None]:
    """给定该账号的游标和刚抓到的推文（最新在前，fetch_user_timeline 的
    契约），决定本次报什么、游标推到哪。

    游标为 None 只出现在首次成功抓取之前；那一次建立基线（记下最新 id、
    一条不报），而不是把整条历史时间线倒进摘要。
    """
    if not tweets:
        return "none", None
    if last_seen_tweet_id is None:
        return "baseline", {"count": len(tweets), "last_seen_tweet_id": tweets[0]["tweet_id"]}

    last_seen = int(last_seen_tweet_id)
    newer = [t for t in tweets if int(t["tweet_id"]) > last_seen]
    if not newer:
        return "none", None
    return "new", {"tweets": newer, "last_seen_tweet_id": newer[0]["tweet_id"]}

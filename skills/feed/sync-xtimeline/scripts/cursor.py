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

    基线取 id 数值最大的那条，不能信"列表第 0 条"——置顶推文固定排在
    最前面，不管发布得多早，直接取位置第一会把基线钉在置顶推文的旧 id
    上，下次运行就会把中间所有推文误判成新增。
    """
    if not tweets:
        return "none", None
    if last_seen_tweet_id is None:
        newest_id = str(max(int(t["tweet_id"]) for t in tweets))
        return "baseline", {"count": len(tweets), "last_seen_tweet_id": newest_id}

    last_seen = int(last_seen_tweet_id)
    newer = [t for t in tweets if int(t["tweet_id"]) > last_seen]
    if not newer:
        return "none", None
    return "new", {"tweets": newer, "last_seen_tweet_id": newer[0]["tweet_id"]}

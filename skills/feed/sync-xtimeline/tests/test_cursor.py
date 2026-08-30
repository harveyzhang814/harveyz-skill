"""compute_update 是纯函数：吃「上次见过的 tweet id」和「刚抓到的推文」，
吐「这次该报什么、游标推到哪」。不碰磁盘、不碰网络。

游标能用单个 id 是因为 X 的 snowflake tweet id 按时间单调递增，可以比大小。
YouTube 那边的 video id 不透明，所以那边用的是 URL 集合。
"""
import cursor


def _tweet(tweet_id: str) -> dict:
    return {"tweet_id": tweet_id, "text": "t"}


def test_no_tweets_reports_nothing():
    assert cursor.compute_update(None, []) == ("none", None)


def test_first_fetch_establishes_baseline():
    tweets = [_tweet("300"), _tweet("200")]
    kind, data = cursor.compute_update(None, tweets)
    assert kind == "baseline"
    assert data == {"count": 2, "last_seen_tweet_id": "300"}


def test_nothing_newer_reports_none():
    assert cursor.compute_update("300", [_tweet("300"), _tweet("200")]) == ("none", None)


def test_newer_tweets_are_reported():
    kind, data = cursor.compute_update("200", [_tweet("400"), _tweet("300"), _tweet("200")])
    assert kind == "new"
    assert [t["tweet_id"] for t in data["tweets"]] == ["400", "300"]
    assert data["last_seen_tweet_id"] == "400"


def test_ids_compare_numerically_not_lexically():
    """snowflake id 位数会变，字符串比较会把 "9" 判成大于 "10"。"""
    kind, data = cursor.compute_update("9", [_tweet("10")])
    assert kind == "new"
    assert data["last_seen_tweet_id"] == "10"


def test_baseline_ignores_pinned_tweet_at_top_of_list():
    """置顶推文固定排在列表第一条，不管它发布得多早。基线必须取全部推文里
    id 真正最大的那条，不能直接信「列表第 0 条」——否则基线会被钉在置顶
    推文的旧 id 上，下次运行会把这中间所有推文都当成"新增"报出来。"""
    tweets = [_tweet("100"), _tweet("500"), _tweet("499")]
    kind, data = cursor.compute_update(None, tweets)
    assert kind == "baseline"
    assert data == {"count": 3, "last_seen_tweet_id": "500"}

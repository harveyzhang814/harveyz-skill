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

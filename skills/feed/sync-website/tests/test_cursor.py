"""compute_update 是纯函数：吃「上次见过的 URL 列表」和「刚抓到的视频列表」，
吐「这次该报什么、该存什么」。不碰磁盘、不碰网络。

游标是 URL 集合而不是单个 last_seen id：X 的 snowflake id 按时间递增可以
比大小，YouTube 的 video id 不透明，只能判断「见过没有」。
"""
import cursor


def _video(url: str, title: str = "t") -> dict:
    return {"url": url, "title": title}


def test_no_videos_reports_nothing():
    assert cursor.compute_update(None, []) == ("none", None)


def test_first_fetch_establishes_baseline():
    """首次抓取记录全部但一条不报——否则会把整个历史片库倒进摘要。"""
    videos = [_video("https://a"), _video("https://b")]
    kind, data = cursor.compute_update(None, videos)
    assert kind == "baseline"
    assert data == {"count": 2, "seen_urls": ["https://a", "https://b"]}


def test_nothing_new_reports_none():
    assert cursor.compute_update(["https://a"], [_video("https://a")]) == ("none", None)


def test_new_video_is_reported():
    kind, data = cursor.compute_update(["https://a"], [_video("https://b"), _video("https://a")])
    assert kind == "new"
    assert data["videos"] == [_video("https://b")]
    assert data["seen_urls"] == ["https://b", "https://a"]


def test_reordered_grid_does_not_produce_false_positives():
    """频道页会置顶/重排，顺序变了不代表有新视频——集合判定不受影响。"""
    seen = ["https://a", "https://b"]
    assert cursor.compute_update(seen, [_video("https://b"), _video("https://a")]) == ("none", None)


def test_empty_seen_list_is_not_treated_as_first_fetch():
    """空列表（抓到过但一个视频都没有）和 None（从没抓过）语义不同。"""
    kind, data = cursor.compute_update([], [_video("https://a")])
    assert kind == "new"
    assert data["seen_urls"] == ["https://a"]

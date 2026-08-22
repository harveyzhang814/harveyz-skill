import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json

import pytest

import watchlist
from config import get_data_dir


def _video(video_id, title="T", published_at=None, published_text="1 day ago"):
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "published_text": published_text,
        "published_at": published_at,
    }


# -------------------------------------------------------------- handle_from_url


def test_handle_from_url_handle_form():
    assert watchlist.handle_from_url("https://www.youtube.com/@mattpocockuk") == "mattpocockuk"
    assert watchlist.handle_from_url("https://www.youtube.com/@mattpocockuk/videos") == "mattpocockuk"
    assert watchlist.handle_from_url("https://youtube.com/@mattpocockuk/") == "mattpocockuk"


def test_handle_from_url_channel_and_legacy_forms():
    assert watchlist.handle_from_url("https://www.youtube.com/channel/UCabc123") == "UCabc123"
    assert watchlist.handle_from_url("https://www.youtube.com/c/SomeName/streams") == "SomeName"
    assert watchlist.handle_from_url("https://www.youtube.com/user/SomeName") == "SomeName"


def test_handle_from_url_rejects_non_channel_urls():
    for bad in (
        "https://www.youtube.com/watch?v=abc",
        "https://www.youtube.com/",
        "https://x.com/mattpocockuk",
        "not a url",
    ):
        with pytest.raises(ValueError):
            watchlist.handle_from_url(bad)


# ----------------------------------------------------------------------- CRUD


def test_add_channel_derives_handle_and_starts_without_cursor():
    watchlist.add_channel("https://www.youtube.com/@mattpocockuk/videos")
    entries = watchlist.load_watchlist()
    assert entries == [
        {
            "handle": "mattpocockuk",
            "channel_url": "https://www.youtube.com/@mattpocockuk/videos",
            "seen_urls": None,
        }
    ]


def test_add_channel_rejects_duplicate():
    watchlist.add_channel("https://www.youtube.com/@mattpocockuk")
    with pytest.raises(ValueError, match="already watching"):
        watchlist.add_channel("https://www.youtube.com/@mattpocockuk/videos")


def test_remove_channel():
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.add_channel("https://www.youtube.com/@b")
    watchlist.remove_channel("a")
    assert [e["handle"] for e in watchlist.load_watchlist()] == ["b"]


def test_remove_channel_unknown_handle():
    with pytest.raises(ValueError, match="not watching"):
        watchlist.remove_channel("nobody")


def test_set_seen_urls_persists():
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.set_seen_urls("a", ["https://www.youtube.com/watch?v=x"])
    assert watchlist.load_watchlist()[0]["seen_urls"] == ["https://www.youtube.com/watch?v=x"]


def test_load_watchlist_missing_file_is_empty():
    assert watchlist.load_watchlist() == []


def test_save_watchlist_writes_under_data_dir():
    watchlist.add_channel("https://www.youtube.com/@a")
    path = get_data_dir() / "watchlist.json"
    assert json.loads(path.read_text(encoding="utf-8"))[0]["handle"] == "a"


# ------------------------------------------------------------- compute_update


def test_compute_update_first_run_establishes_baseline():
    entry = {"handle": "a", "channel_url": "u", "seen_urls": None}
    kind, data = watchlist.compute_update(entry, [_video("v1"), _video("v2")])
    assert kind == "baseline"
    assert data["count"] == 2
    assert data["seen_urls"] == [
        "https://www.youtube.com/watch?v=v1",
        "https://www.youtube.com/watch?v=v2",
    ]


def test_compute_update_no_videos_is_none():
    entry = {"handle": "a", "channel_url": "u", "seen_urls": None}
    assert watchlist.compute_update(entry, []) == ("none", None)


def test_compute_update_reports_only_unseen_urls():
    entry = {
        "handle": "a",
        "channel_url": "u",
        "seen_urls": ["https://www.youtube.com/watch?v=v2"],
    }
    kind, data = watchlist.compute_update(entry, [_video("v3"), _video("v2"), _video("v1")])
    assert kind == "new"
    assert [v["video_id"] for v in data["videos"]] == ["v3", "v1"]


def test_compute_update_new_cursor_keeps_new_urls_first():
    entry = {"handle": "a", "channel_url": "u", "seen_urls": ["https://www.youtube.com/watch?v=v1"]}
    _, data = watchlist.compute_update(entry, [_video("v2"), _video("v1")])
    assert data["seen_urls"] == [
        "https://www.youtube.com/watch?v=v2",
        "https://www.youtube.com/watch?v=v1",
    ]


def test_compute_update_nothing_new_is_none():
    entry = {"handle": "a", "channel_url": "u", "seen_urls": ["https://www.youtube.com/watch?v=v1"]}
    assert watchlist.compute_update(entry, [_video("v1")]) == ("none", None)


def test_compute_update_treats_empty_seen_list_as_nothing_seen():
    """An empty list is a real cursor (0 videos seen), not "never run" — so
    everything fetched is new, rather than silently re-baselining."""
    entry = {"handle": "a", "channel_url": "u", "seen_urls": []}
    kind, data = watchlist.compute_update(entry, [_video("v1")])
    assert kind == "new"
    assert [v["video_id"] for v in data["videos"]] == ["v1"]

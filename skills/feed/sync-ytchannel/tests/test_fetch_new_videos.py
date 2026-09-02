"""Only the deterministic, network-free path is covered here — per-channel
diff behaviour lives in test_cursor.py (pure, no network) and the roster
round-trip in test_roster_client.py. A full live run needs a real
YouTube-reachable network, same out-of-scope boundary as the rest of the
suite.
"""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_new_videos
import roster_client
from config import get_data_dir


def _video(video_id, title="T", published_at=None, published_text="1 day ago"):
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "published_text": published_text,
        "published_at": published_at,
    }


class _FakeRoster:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self.channels_list: list[dict] = []
        self.cursors: dict[str, list[str] | None] = {}
        self.errors: dict[str, str] = {}

    def watch(self, handle: str, url: str) -> None:
        self.channels_list.append({
            "creator_id": handle.lower(), "platform": "youtube",
            "handle": handle, "url": url,
        })
        self.cursors.setdefault(handle, None)


@pytest.fixture(autouse=True)
def fake_roster(monkeypatch, tmp_path):
    fake = _FakeRoster(tmp_path)
    monkeypatch.setattr(roster_client, "channels", lambda: list(fake.channels_list))
    monkeypatch.setattr(roster_client, "get_cursor", lambda h: fake.cursors.get(h))
    monkeypatch.setattr(
        roster_client, "set_cursor",
        lambda h, seen_urls, run_time: fake.cursors.__setitem__(h, seen_urls))
    monkeypatch.setattr(
        roster_client, "set_error",
        lambda h, error, run_time: fake.errors.__setitem__(h, error))
    return fake


@pytest.fixture
def fake_fetch(monkeypatch):
    responses: dict[str, object] = {}

    async def _fetch(channel_url, chrome_profile=None, max_videos=30):
        value = responses[channel_url]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(fetch_new_videos, "fetch_channel_videos", _fetch)
    return responses


def _pending_path() -> Path:
    return get_data_dir() / "pending.json"


def test_run_first_time_establishes_baseline_without_listing_videos(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1"), _video("v2")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert report["baselines"] == {"a": 2}
    assert "a" not in report["new"]
    assert report["cursors"]["a"] == [
        "https://www.youtube.com/watch?v=v1",
        "https://www.youtube.com/watch?v=v2",
    ]


def test_run_with_nothing_new_reports_none(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert report["new"] == {}
    assert report["baselines"] == {}


def test_run_reports_the_cursor_without_writing_it(fake_roster, fake_fetch):
    """该推到的游标值只是报出来，写盘归 archive_videos.py。"""
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [
        _video("v2", "Brand new", published_at="2026-08-20T10:00:00+00:00"),
        _video("v1", "Older"),
    ]

    report = asyncio.run(fetch_new_videos.run(None))

    assert [v["video_id"] for v in report["new"]["a"]] == ["v2"]
    assert report["cursors"]["a"] == [
        "https://www.youtube.com/watch?v=v2",
        "https://www.youtube.com/watch?v=v1",
    ]
    assert fake_roster.cursors["a"] == ["https://www.youtube.com/watch?v=v1"]


def test_nothing_new_leaves_the_channel_out_of_cursors(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1", "Older")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert "a" not in report["cursors"]


def test_videos_already_in_archive_are_still_reported(fake_roster, fake_fetch):
    """上一轮崩在归档之后、推进游标之前，游标没动，这一轮会重抓到同一批。
    照常报出来，代价只是多一份摘要；被归档过滤掉的话它们就永远不会出现在
    任何一份摘要里。"""
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    archive_path = get_data_dir() / "creators" / "a.json"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_text(json.dumps([_video("v2", "Already archived")]), encoding="utf-8")
    fake_fetch["https://www.youtube.com/@a"] = [
        _video("v2", "Already archived"),
        _video("v1", "Old"),
    ]

    report = asyncio.run(fetch_new_videos.run(None))

    assert [v["video_id"] for v in report["new"]["a"]] == ["v2"]


def test_handle_filter_only_fetches_the_requested_handles(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]
    fake_fetch["https://www.youtube.com/@b"] = [_video("v2")]

    report = asyncio.run(fetch_new_videos.run(None, ["a"]))

    assert report["baselines"] == {"a": 1}
    assert "b" not in report["baselines"]
    assert "b" not in report["failures"]


def test_handle_filter_reports_unknown_handle_as_a_failure(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    report = asyncio.run(fetch_new_videos.run(None, ["ghost"]))

    assert report["failures"] == {"ghost": "不在 roster 名册里"}
    assert report["baselines"] == {}


def test_no_handle_filter_still_fetches_the_whole_roster(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]
    fake_fetch["https://www.youtube.com/@b"] = [_video("v2")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert set(report["baselines"]) == {"a", "b"}


def test_run_isolates_per_channel_failures(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_fetch["https://www.youtube.com/@a"] = RuntimeError("consent wall")
    fake_fetch["https://www.youtube.com/@b"] = [_video("v9")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert report["failures"] == {"a": "consent wall"}
    assert report["baselines"] == {"b": 1}
    assert "a" not in report["cursors"]
    assert report["cursors"]["b"] == ["https://www.youtube.com/watch?v=v9"]


def test_failed_channel_is_recorded_on_the_roster(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = RuntimeError("consent wall")

    asyncio.run(fetch_new_videos.run(None))

    assert fake_roster.errors == {"a": "consent wall"}


def test_report_json_shape(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_roster.cursors["b"] = []
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]
    fake_fetch["https://www.youtube.com/@b"] = [_video("v2")]

    report = asyncio.run(fetch_new_videos.run(None))

    assert set(report) == {"run_time", "new", "baselines", "failures", "cursors"}
    assert report["baselines"] == {"a": 1}
    assert [v["video_id"] for v in report["new"]["b"]] == ["v2"]
    assert report["failures"] == {}
    json.dumps(report)


def test_main_prints_report_and_writes_no_pending_file(fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    fetch_new_videos.main()

    report = json.loads(capsys.readouterr().out)
    assert report["baselines"] == {"a": 1}
    assert not _pending_path().exists()


def test_leftover_pending_json_from_an_older_version_is_ignored(fake_roster, fake_fetch, capsys):
    """升级前留下的 pending.json 绝不能再被当成断点回放——那正是「一次中断
    之后每次运行都静默空转」的成因。这次运行必须照常真的发起抓取。"""
    stale_report = {
        "run_time": "2020-01-01T00:00:00+00:00",
        "new": {"a": [{"video_id": "v1", "url": "u1", "title": "T",
                        "published_text": "1 day ago", "published_at": None}]},
        "baselines": {}, "failures": {},
    }
    pending_path = _pending_path()
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(stale_report), encoding="utf-8")

    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v9")]

    fetch_new_videos.main()

    report = json.loads(capsys.readouterr().out)
    assert report != stale_report
    assert report["baselines"] == {"a": 1}


def test_run_with_empty_watchlist_is_empty(fake_roster, capsys):
    fetch_new_videos.main()
    report = json.loads(capsys.readouterr().out)
    assert report == {"run_time": report["run_time"], "new": {}, "baselines": {},
                      "failures": {}, "cursors": {}}

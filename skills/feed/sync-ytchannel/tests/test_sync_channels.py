import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json

import pytest

import roster_client
import sync_channels
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
    """In-memory stand-in for the roster CLI: the channel list plus each
    channel's cursor, with no subprocess and no real registry on disk. The
    real CLI round-trip is covered by test_roster_client.py; the real
    end-to-end path is covered by the plan's manual acceptance step."""

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
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    return fake


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace the MCP call with a per-channel canned response."""
    responses: dict[str, object] = {}

    async def _fetch(channel_url, chrome_profile=None, max_videos=30):
        value = responses[channel_url]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(sync_channels, "fetch_channel_videos", _fetch)
    return responses


def _digest_files():
    digests = get_data_dir() / "digests" / "youtube"
    return sorted(digests.glob("*.md")) if digests.exists() else []


def test_run_first_time_establishes_baseline_without_listing_videos(
        fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1"), _video("v2")]

    sync_channels.main()

    out = capsys.readouterr().out
    assert out.startswith("WRITTEN: ")
    assert fake_roster.cursors["a"] == [
        "https://www.youtube.com/watch?v=v1",
        "https://www.youtube.com/watch?v=v2",
    ]
    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "起始 2 个视频" in body
    assert "## @a" not in body


def test_run_with_nothing_new_writes_no_file(fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    sync_channels.main()

    assert capsys.readouterr().out.strip() == "EMPTY"
    assert _digest_files() == []


def test_run_reports_new_videos_and_advances_cursor(fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [
        _video("v2", "Brand new", published_at="2026-08-20T10:00:00+00:00"),
        _video("v1", "Older"),
    ]

    sync_channels.main()

    assert capsys.readouterr().out.startswith("WRITTEN: ")
    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "- [2026-08-20] Brand new（https://www.youtube.com/watch?v=v2）" in body
    assert "Older" not in body
    assert fake_roster.cursors["a"] == [
        "https://www.youtube.com/watch?v=v2",
        "https://www.youtube.com/watch?v=v1",
    ]


def test_run_isolates_per_channel_failures(fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_fetch["https://www.youtube.com/@a"] = RuntimeError("consent wall")
    fake_fetch["https://www.youtube.com/@b"] = [_video("v9")]

    sync_channels.main()

    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "- @a：consent wall" in body
    assert "- @b：起始 1 个视频" in body
    assert fake_roster.cursors["a"] is None
    assert fake_roster.cursors["b"] == ["https://www.youtube.com/watch?v=v9"]


def test_failed_channel_is_recorded_on_the_roster(fake_roster, fake_fetch):
    """失败要写进 state 的 last_error，否则 `roster registry list` 看不出
    这个渠道一直在挂。"""
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = RuntimeError("consent wall")

    sync_channels.main()

    assert fake_roster.errors == {"a": "consent wall"}


def test_run_keeps_cursor_untouched_when_digest_write_fails(
        fake_roster, fake_fetch, monkeypatch):
    """Cursors advance only after the digest is safely on disk — otherwise a
    failed write would silently swallow the very videos it was reporting."""
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.cursors["a"] = ["https://www.youtube.com/watch?v=v1"]
    fake_fetch["https://www.youtube.com/@a"] = [_video("v2"), _video("v1")]

    def _boom(report):
        raise OSError("disk full")

    monkeypatch.setattr(sync_channels, "write_digest", _boom)

    with pytest.raises(OSError):
        sync_channels.main()

    assert fake_roster.cursors["a"] == ["https://www.youtube.com/watch?v=v1"]


def test_run_with_empty_watchlist_is_empty(capsys):
    sync_channels.main()
    assert capsys.readouterr().out.strip() == "EMPTY"


def test_digest_filename_is_denote_style(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    sync_channels.main()

    name = _digest_files()[0].name
    assert name.endswith("--digest.md")
    stamp = name.split("--")[0]
    assert len(stamp) == 15 and stamp[8] == "T"


def test_digest_lands_under_the_platform_subdirectory(fake_roster, fake_fetch, capsys):
    """两个 sync skill 共用同一个 DATA_DIR，同一天两份 digest 会撞名，
    所以各落各的平台子目录。"""
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    sync_channels.main()

    written = capsys.readouterr().out.strip().removeprefix("WRITTEN: ")
    assert Path(written).parent == get_data_dir() / "digests" / "youtube"


def test_report_json_shape(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://www.youtube.com/@a")
    fake_roster.watch("b", "https://www.youtube.com/@b")
    fake_roster.cursors["b"] = []
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]
    fake_fetch["https://www.youtube.com/@b"] = [_video("v2")]

    report, _ = sync_channels.collect()

    assert set(report) == {"run_time", "new", "baselines", "failures"}
    assert report["baselines"] == {"a": 1}
    assert [v["video_id"] for v in report["new"]["b"]] == ["v2"]
    assert report["failures"] == {}
    json.dumps(report)  # must stay serializable for inspection

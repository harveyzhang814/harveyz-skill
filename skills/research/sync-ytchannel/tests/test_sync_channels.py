import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import json

import pytest

import sync_channels
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
    digests = get_data_dir() / "digests"
    return sorted(digests.glob("*.md")) if digests.exists() else []


def test_run_first_time_establishes_baseline_without_listing_videos(fake_fetch, capsys):
    watchlist.add_channel("https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1"), _video("v2")]

    sync_channels.main()

    out = capsys.readouterr().out
    assert out.startswith("WRITTEN: ")
    assert watchlist.load_watchlist()[0]["seen_urls"] == [
        "https://www.youtube.com/watch?v=v1",
        "https://www.youtube.com/watch?v=v2",
    ]
    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "起始 2 个视频" in body
    assert "## @a" not in body


def test_run_with_nothing_new_writes_no_file(fake_fetch, capsys):
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.set_seen_urls("a", ["https://www.youtube.com/watch?v=v1"])
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    sync_channels.main()

    assert capsys.readouterr().out.strip() == "EMPTY"
    assert _digest_files() == []


def test_run_reports_new_videos_and_advances_cursor(fake_fetch, capsys):
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.set_seen_urls("a", ["https://www.youtube.com/watch?v=v1"])
    fake_fetch["https://www.youtube.com/@a"] = [
        _video("v2", "Brand new", published_at="2026-08-20T10:00:00+00:00"),
        _video("v1", "Older"),
    ]

    sync_channels.main()

    assert capsys.readouterr().out.startswith("WRITTEN: ")
    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "- [2026-08-20] Brand new（https://www.youtube.com/watch?v=v2）" in body
    assert "Older" not in body
    assert watchlist.load_watchlist()[0]["seen_urls"] == [
        "https://www.youtube.com/watch?v=v2",
        "https://www.youtube.com/watch?v=v1",
    ]


def test_run_isolates_per_channel_failures(fake_fetch, capsys):
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.add_channel("https://www.youtube.com/@b")
    fake_fetch["https://www.youtube.com/@a"] = RuntimeError("consent wall")
    fake_fetch["https://www.youtube.com/@b"] = [_video("v9")]

    sync_channels.main()

    body = _digest_files()[0].read_text(encoding="utf-8")
    assert "- @a：consent wall" in body
    assert "- @b：起始 1 个视频" in body
    entries = {e["handle"]: e for e in watchlist.load_watchlist()}
    assert entries["a"]["seen_urls"] is None
    assert entries["b"]["seen_urls"] == ["https://www.youtube.com/watch?v=v9"]


def test_run_keeps_cursor_untouched_when_digest_write_fails(fake_fetch, monkeypatch):
    """Cursors advance only after the digest is safely on disk — otherwise a
    failed write would silently swallow the very videos it was reporting."""
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.set_seen_urls("a", ["https://www.youtube.com/watch?v=v1"])
    fake_fetch["https://www.youtube.com/@a"] = [_video("v2"), _video("v1")]

    def _boom(report):
        raise OSError("disk full")

    monkeypatch.setattr(sync_channels, "write_digest", _boom)

    with pytest.raises(OSError):
        sync_channels.main()

    assert watchlist.load_watchlist()[0]["seen_urls"] == ["https://www.youtube.com/watch?v=v1"]


def test_run_with_empty_watchlist_is_empty(capsys):
    sync_channels.main()
    assert capsys.readouterr().out.strip() == "EMPTY"


def test_digest_filename_is_denote_style(fake_fetch):
    watchlist.add_channel("https://www.youtube.com/@a")
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]

    sync_channels.main()

    name = _digest_files()[0].name
    assert name.endswith("--digest.md")
    stamp = name.split("--")[0]
    assert len(stamp) == 15 and stamp[8] == "T"


def test_report_json_shape(fake_fetch):
    watchlist.add_channel("https://www.youtube.com/@a")
    watchlist.add_channel("https://www.youtube.com/@b")
    watchlist.set_seen_urls("b", [])
    fake_fetch["https://www.youtube.com/@a"] = [_video("v1")]
    fake_fetch["https://www.youtube.com/@b"] = [_video("v2")]

    report, _ = sync_channels.collect()

    assert set(report) == {"run_time", "new", "baselines", "failures"}
    assert report["baselines"] == {"a": 1}
    assert [v["video_id"] for v in report["new"]["b"]] == ["v2"]
    assert report["failures"] == {}
    json.dumps(report)  # must stay serializable for inspection

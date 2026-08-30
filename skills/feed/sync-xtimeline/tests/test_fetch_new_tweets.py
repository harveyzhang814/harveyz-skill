"""Only the deterministic, network-free path is covered here — per-handle
diff behaviour lives in test_cursor.py (pure, no network) and the roster
round-trip in test_roster_client.py. A full live run needs a real logged-in
Chrome profile, same out-of-scope boundary as the rest of the xcom suite.

The two subprocess tests deliberately drive the REAL roster CLI against an
empty temp registry: monkeypatch does not cross a process boundary, so they
are the only place the script's actual roster wiring gets exercised.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_new_tweets
import roster_client

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_new_tweets.py"


@pytest.fixture
def real_roster_env(tmp_path):
    """Point a subprocess at a real, empty roster: its own config file and
    its own DATA_DIR, both under tmp_path."""
    data_dir = tmp_path / "roster-data"
    config_path = tmp_path / "roster-config.json"
    config_path.write_text(json.dumps({"DATA_DIR": str(data_dir)}), encoding="utf-8")
    return {**os.environ,
            "HSKILL_ROSTER_CONFIG": str(config_path),
            "BROWSER_FETCH_DATA_DIR": str(tmp_path / "bfm-data")}, data_dir


@pytest.fixture
def stub_roster(monkeypatch):
    """In-process stand-in for the roster: channel list + cursors."""
    channels: list[dict] = []
    cursors: dict[str, str | None] = {}
    errors: dict[str, str] = {}

    monkeypatch.setattr(roster_client, "channels", lambda: list(channels))
    monkeypatch.setattr(roster_client, "get_cursor", lambda h: cursors.get(h))
    monkeypatch.setattr(roster_client, "set_cursor",
                        lambda h, tweet_id, run_time: cursors.__setitem__(h, tweet_id))
    monkeypatch.setattr(roster_client, "set_error",
                        lambda h, error, run_time: errors.__setitem__(h, error))

    def watch(handle: str, url: str, cursor: str | None = None) -> None:
        channels.append({"creator_id": handle, "platform": "x",
                         "handle": handle, "url": url})
        cursors[handle] = cursor

    return type("Stub", (), {"watch": staticmethod(watch),
                             "cursors": cursors, "errors": errors})


def test_empty_roster_produces_empty_report(real_roster_env):
    env, _ = real_roster_env
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["new"] == {}
    assert report["baselines"] == {}
    assert report["failures"] == {}
    assert "run_time" in report


def test_pending_json_written_with_report_content(real_roster_env):
    env, data_dir = real_roster_env
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    pending_path = data_dir / "tweets" / "pending.json"
    assert pending_path.exists()
    assert json.loads(pending_path.read_text(encoding="utf-8")) == report


def test_leftover_pending_json_is_replayed_without_refetching(real_roster_env):
    """render_digest.py is the only thing that clears pending.json. If a prior
    run got through fetch (advancing cursors) but died before render_digest.py,
    the leftover file must be replayed byte-for-byte, not discarded — cursors
    have already moved past those tweets, so a fresh fetch would never
    surface them again."""
    env, data_dir = real_roster_env
    pending_dir = data_dir / "tweets"
    pending_dir.mkdir(parents=True, exist_ok=True)
    stale_report = {
        "run_time": "2020-01-01T00:00:00+00:00",
        "new": {"alice": [{"tweet_id": "1", "url": "u", "text": "hi",
                            "timestamp": "t", "author_handle": "@alice",
                            "type": "post", "reply_to_handle": None,
                            "quoted_author": None, "quoted_text": None,
                            "quoted_timestamp": None}]},
        "baselines": {},
        "failures": {},
    }
    pending_path = pending_dir / "pending.json"
    pending_path.write_text(json.dumps(stale_report), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env,
        capture_output=True, text=True, timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == stale_report
    assert json.loads(pending_path.read_text(encoding="utf-8")) == stale_report


def test_handle_filter_only_fetches_the_requested_handles(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)
    stub_roster.watch("bob", "https://x.com/bob", cursor=None)

    fetched = []

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        fetched.append(profile_url)
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None, ["alice"]))

    assert fetched == ["https://x.com/alice/all"]
    assert "alice" in report["baselines"]
    assert "bob" not in report["baselines"]
    assert "bob" not in report["failures"]


def test_handle_filter_reports_unknown_handle_as_a_failure(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None, ["ghost"]))

    assert report["failures"] == {"ghost": "不在 roster 名册里"}
    assert report["baselines"] == {}


def test_no_handle_filter_still_fetches_the_whole_roster(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)
    stub_roster.watch("bob", "https://x.com/bob", cursor=None)

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert set(report["baselines"]) == {"alice", "bob"}


def test_malformed_cursor_on_one_handle_does_not_crash_run(stub_roster, monkeypatch):
    stub_roster.watch("badcursor", "https://x.com/badcursor", cursor="not-a-number")
    stub_roster.watch("goodhandle", "https://x.com/goodhandle", cursor=None)

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert "badcursor" in report["failures"]
    assert "goodhandle" in report["baselines"]
    assert "goodhandle" not in report["failures"]


def test_failed_handle_is_recorded_on_the_roster(stub_roster, monkeypatch):
    """失败要写进 state 的 last_error，否则 `roster registry list` 看不出
    这个账号一直在挂。"""
    stub_roster.watch("badcursor", "https://x.com/badcursor", cursor="not-a-number")

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    asyncio.run(fetch_new_tweets.run(None))

    assert "badcursor" in stub_roster.errors


def test_timeline_url_appends_all_tab():
    """Bare profile URLs only show X's default Posts tab (posts + quotes) —
    /all is needed to also see reposts and replies (verified by manual
    probing against a real profile)."""
    assert fetch_new_tweets._timeline_url("https://x.com/alice") == "https://x.com/alice/all"
    assert fetch_new_tweets._timeline_url("https://x.com/alice/") == "https://x.com/alice/all"


def test_run_fetches_the_all_tab_not_the_bare_profile_url(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)

    seen_urls = []

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        seen_urls.append(profile_url)
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    asyncio.run(fetch_new_tweets.run(None))

    assert seen_urls == ["https://x.com/alice/all"]


def test_baseline_advances_the_cursor_on_the_roster(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    asyncio.run(fetch_new_tweets.run(None))

    assert stub_roster.cursors["alice"] == "100"


def test_tweets_already_in_archive_are_not_re_reported(stub_roster, monkeypatch, isolated_data_dir):
    stub_roster.watch("alice", "https://x.com/alice", cursor="50")
    archive_path = isolated_data_dir / "tweets" / "creators" / "alice.json"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_text(
        json.dumps([{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t"}]),
        encoding="utf-8",
    )

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert "alice" not in report["new"]
    assert stub_roster.cursors["alice"] == "100"


def test_only_unarchived_tweets_are_reported_when_partially_overlapping(
        stub_roster, monkeypatch, isolated_data_dir):
    stub_roster.watch("alice", "https://x.com/alice", cursor="50")
    archive_path = isolated_data_dir / "tweets" / "creators" / "alice.json"
    archive_path.parent.mkdir(parents=True)
    archive_path.write_text(
        json.dumps([{"tweet_id": "100", "url": "u100", "text": "old", "timestamp": "t"}]),
        encoding="utf-8",
    )

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [
            {"tweet_id": "101", "url": "u101", "text": "new", "timestamp": "t", "author_handle": "@alice"},
            {"tweet_id": "100", "url": "u100", "text": "old", "timestamp": "t", "author_handle": "@alice"},
        ]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert [t["tweet_id"] for t in report["new"]["alice"]] == ["101"]

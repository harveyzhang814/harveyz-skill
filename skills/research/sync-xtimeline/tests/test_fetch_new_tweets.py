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
            "BROWSER_FETCH_MCP_DATA_DIR": str(tmp_path / "bfm-data")}, data_dir


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
    pending_path = data_dir / "pending.json"
    assert pending_path.exists()
    assert json.loads(pending_path.read_text(encoding="utf-8")) == report


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

"""Only the deterministic, network-free path is covered here (empty
watchlist) — per-handle fetch/diff behavior is covered by
test_watchlist.py's compute_update tests (pure, no network) and
test_mcp_timeline_client.py's validation tests (real MCP call, no live
X login needed). A full live run needs a real logged-in Chrome profile,
same out-of-scope boundary as the rest of the xcom test suite.
"""
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_new_tweets
import watchlist

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "fetch_new_tweets.py"


def test_empty_watchlist_produces_empty_report(tmp_path):
    data_dir = tmp_path / "data"
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "HSKILL_WATCH_X_DATA_DIR": str(data_dir),
             "BROWSER_FETCH_MCP_DATA_DIR": str(tmp_path / "bfm-data")},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["new"] == {}
    assert report["baselines"] == {}
    assert report["failures"] == {}
    assert "run_time" in report


def test_pending_json_written_with_report_content(tmp_path):
    data_dir = tmp_path / "data"
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "HSKILL_WATCH_X_DATA_DIR": str(data_dir),
             "BROWSER_FETCH_MCP_DATA_DIR": str(tmp_path / "bfm-data")},
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    pending_path = data_dir / "pending.json"
    assert pending_path.exists()
    assert json.loads(pending_path.read_text(encoding="utf-8")) == report


def test_malformed_cursor_on_one_handle_does_not_crash_run(monkeypatch):
    # Bypass add_handle's normal validation to seed a malformed cursor directly.
    watchlist.save_watchlist([
        {"handle": "badcursor", "profile_url": "https://x.com/badcursor", "last_seen_tweet_id": "not-a-number"},
        {"handle": "goodhandle", "profile_url": "https://x.com/goodhandle", "last_seen_tweet_id": None},
    ])

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@x"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert "badcursor" in report["failures"]
    assert "goodhandle" in report["baselines"]
    assert "goodhandle" not in report["failures"]


def test_timeline_url_appends_all_tab():
    """Bare profile URLs only show X's default Posts tab (posts + quotes) —
    /all is needed to also see reposts and replies (verified by manual
    probing against a real profile)."""
    assert fetch_new_tweets._timeline_url("https://x.com/alice") == "https://x.com/alice/all"
    assert fetch_new_tweets._timeline_url("https://x.com/alice/") == "https://x.com/alice/all"


def test_run_fetches_the_all_tab_not_the_bare_profile_url(monkeypatch):
    watchlist.save_watchlist([
        {"handle": "alice", "profile_url": "https://x.com/alice", "last_seen_tweet_id": None},
    ])

    seen_urls = []

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        seen_urls.append(profile_url)
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    asyncio.run(fetch_new_tweets.run(None))

    assert seen_urls == ["https://x.com/alice/all"]

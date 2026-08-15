import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import watchlist

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "watchlist.py"


def _run(args: list[str], data_dir: Path) -> subprocess.CompletedProcess:
    import os

    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, "HSKILL_WATCH_X_DATA_DIR": str(data_dir)},
        capture_output=True, text=True, timeout=10,
    )


def test_load_watchlist_empty_when_no_file_exists():
    assert watchlist.load_watchlist() == []


def test_add_handle_then_load_round_trips():
    watchlist.add_handle("alice", "https://x.com/alice")
    entries = watchlist.load_watchlist()
    assert entries == [{"handle": "alice", "profile_url": "https://x.com/alice", "last_seen_tweet_id": None}]


def test_add_handle_rejects_duplicate():
    watchlist.add_handle("alice", "https://x.com/alice")
    with pytest.raises(ValueError, match="already watching"):
        watchlist.add_handle("alice", "https://x.com/alice")


def test_remove_handle_removes_entry():
    watchlist.add_handle("alice", "https://x.com/alice")
    watchlist.add_handle("bob", "https://x.com/bob")
    watchlist.remove_handle("alice")
    entries = watchlist.load_watchlist()
    assert [e["handle"] for e in entries] == ["bob"]


def test_remove_handle_rejects_unknown():
    with pytest.raises(ValueError, match="not watching"):
        watchlist.remove_handle("nobody")


def test_set_last_seen_updates_cursor():
    watchlist.add_handle("alice", "https://x.com/alice")
    watchlist.set_last_seen("alice", "1002")
    entries = watchlist.load_watchlist()
    assert entries[0]["last_seen_tweet_id"] == "1002"


def test_compute_update_no_tweets_returns_none():
    entry = {"handle": "alice", "profile_url": "u", "last_seen_tweet_id": None}
    kind, data = watchlist.compute_update(entry, [])
    assert (kind, data) == ("none", None)


def test_compute_update_first_run_establishes_baseline():
    entry = {"handle": "alice", "profile_url": "u", "last_seen_tweet_id": None}
    tweets = [{"tweet_id": "1002"}, {"tweet_id": "1001"}]
    kind, data = watchlist.compute_update(entry, tweets)
    assert kind == "baseline"
    assert data == {"count": 2, "last_seen_tweet_id": "1002"}


def test_compute_update_reports_only_newer_tweets():
    entry = {"handle": "alice", "profile_url": "u", "last_seen_tweet_id": "1001"}
    tweets = [{"tweet_id": "1003"}, {"tweet_id": "1002"}, {"tweet_id": "1001"}]
    kind, data = watchlist.compute_update(entry, tweets)
    assert kind == "new"
    assert data["last_seen_tweet_id"] == "1003"
    assert [t["tweet_id"] for t in data["tweets"]] == ["1003", "1002"]


def test_compute_update_no_newer_tweets_returns_none():
    entry = {"handle": "alice", "profile_url": "u", "last_seen_tweet_id": "1003"}
    tweets = [{"tweet_id": "1003"}, {"tweet_id": "1002"}]
    kind, data = watchlist.compute_update(entry, tweets)
    assert (kind, data) == ("none", None)


def test_cli_add_then_list(tmp_path):
    data_dir = tmp_path / "data"
    add_result = _run(["add", "alice", "https://x.com/alice"], data_dir)
    assert add_result.returncode == 0, add_result.stderr
    assert "OK" in add_result.stdout

    list_result = _run(["list"], data_dir)
    assert "@alice" in list_result.stdout
    assert "https://x.com/alice" in list_result.stdout
    assert "last_seen=(none)" in list_result.stdout


def test_cli_list_empty_prints_empty(tmp_path):
    result = _run(["list"], tmp_path / "data")
    assert result.stdout.strip() == "EMPTY"


def test_cli_remove_unknown_handle_fails(tmp_path):
    result = _run(["remove", "nobody"], tmp_path / "data")
    assert result.returncode == 1
    assert "not watching" in result.stderr

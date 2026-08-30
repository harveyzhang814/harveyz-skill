import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive_tweets import archive_tweets, _archive_path
from conftest import write_config

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive_tweets.py"


def _run(report: dict, data_dir: Path) -> subprocess.CompletedProcess:
    config_path = data_dir.parent / "config.json"
    write_config(config_path, data_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        env={**os.environ, "HSKILL_ROSTER_CONFIG": str(config_path)},
        capture_output=True, text=True, timeout=10,
    )


def test_archive_tweets_writes_new_handle_file():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1", "translated": "你好"}]},
    }
    archive_tweets(report)
    saved = json.loads(_archive_path("alice").read_text(encoding="utf-8"))
    assert saved == report["new"]["alice"]


def test_archive_tweets_appends_across_calls():
    first = {"run_time": "t", "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}]}}
    second = {"run_time": "t", "new": {"alice": [{"tweet_id": "2", "url": "u2", "text": "yo", "timestamp": "t2"}]}}
    archive_tweets(first)
    archive_tweets(second)
    saved = json.loads(_archive_path("alice").read_text(encoding="utf-8"))
    assert [t["tweet_id"] for t in saved] == ["1", "2"]


def test_archive_tweets_dedups_by_tweet_id():
    report = {"run_time": "t", "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}]}}
    archive_tweets(report)
    archive_tweets(report)
    saved = json.loads(_archive_path("alice").read_text(encoding="utf-8"))
    assert len(saved) == 1


def test_archive_tweets_keeps_handles_isolated():
    report = {
        "run_time": "t",
        "new": {
            "alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}],
            "bob": [{"tweet_id": "9", "url": "u9", "text": "yo", "timestamp": "t9"}],
        },
    }
    archive_tweets(report)
    assert [t["tweet_id"] for t in json.loads(_archive_path("alice").read_text(encoding="utf-8"))] == ["1"]
    assert [t["tweet_id"] for t in json.loads(_archive_path("bob").read_text(encoding="utf-8"))] == ["9"]


def test_archive_tweets_noop_when_report_has_no_new():
    report = {"run_time": "t", "new": {}, "baselines": {"carol": 3}, "failures": {}}
    archive_tweets(report)
    assert not _archive_path("carol").exists()


def test_cli_archives_report_from_stdin(tmp_path):
    data_dir = tmp_path / "data"
    report = {"run_time": "t", "new": {"alice": [{"tweet_id": "1", "url": "u1", "text": "hi", "timestamp": "t1"}]}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    saved = json.loads((data_dir / "tweets" / "creators" / "alice.json").read_text(encoding="utf-8"))
    assert saved == report["new"]["alice"]

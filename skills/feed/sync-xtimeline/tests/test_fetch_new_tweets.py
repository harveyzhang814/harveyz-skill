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
    # 抓取阶段不该再碰 set_cursor —— 推进游标归 archive_tweets.py。留着这个
    # stub 是为了万一它被调用，测试能看见（cursors 会被改写）而不是静默通过。
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


def test_no_pending_file_is_written(real_roster_env):
    """断点文件整个机制已经删掉：抓取阶段不落盘任何续跑状态，游标也没推进，
    所以没有需要保护的批次。"""
    env, data_dir = real_roster_env
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env,
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert "cursors" in json.loads(result.stdout)
    assert not (data_dir / "tweets" / "pending.json").exists()


def test_leftover_pending_json_from_an_older_version_is_ignored(real_roster_env):
    """升级前留下的 pending.json 绝不能再被当成断点回放——那正是「一次中断
    之后每次运行都静默空转」的成因。这次运行必须照常真的发起抓取。"""
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
    (pending_dir / "pending.json").write_text(json.dumps(stale_report), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env,
        capture_output=True, text=True, timeout=60,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report != stale_report
    assert report["run_time"] != stale_report["run_time"]


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


def test_baseline_reports_the_cursor_without_writing_it(stub_roster, monkeypatch):
    """基线该推到的游标值只是报出来，写盘归 archive_tweets.py。"""
    stub_roster.watch("alice", "https://x.com/alice", cursor=None)

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert report["cursors"]["alice"] == "100"
    assert stub_roster.cursors["alice"] is None


def test_new_tweets_report_the_cursor_without_writing_it(stub_roster, monkeypatch):
    stub_roster.watch("alice", "https://x.com/alice", cursor="50")

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert report["cursors"]["alice"] == "100"
    assert stub_roster.cursors["alice"] == "50"


def test_nothing_new_leaves_the_handle_out_of_cursors(stub_roster, monkeypatch):
    """没有新推文时游标本来就不需要动，别在报告里塞一个空推进。"""
    stub_roster.watch("alice", "https://x.com/alice", cursor="100")

    async def fake_fetch_timeline(profile_url, chrome_profile=None):
        return [{"tweet_id": "100", "url": "u", "text": "hi", "timestamp": "t", "author_handle": "@alice"}]

    monkeypatch.setattr(fetch_new_tweets, "fetch_timeline", fake_fetch_timeline)

    report = asyncio.run(fetch_new_tweets.run(None))

    assert "alice" not in report["cursors"]


def test_tweets_already_in_archive_are_still_reported(stub_roster, monkeypatch, isolated_data_dir):
    """上一轮崩在归档之后、推进游标之前，游标没动，这一轮会重抓到同一批。
    此时必须照常报出来——被归档过滤掉的话摘要会是空的，那批推文就永远不会
    出现在任何一份摘要里（静默漏报）。重复的代价只是多一份摘要。"""
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

    assert [t["tweet_id"] for t in report["new"]["alice"]] == ["100"]

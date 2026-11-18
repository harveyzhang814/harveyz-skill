import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from render_digest import has_content, render_digest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render_digest.py"


def _run(report: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        capture_output=True, text=True, timeout=10,
    )


def test_has_content_false_for_fully_empty_report():
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    assert has_content(report) is False


def test_has_content_true_when_new_tweets_present():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {"alice": [{"tweet_id": "1", "url": "u", "text": "hi", "timestamp": "t", "translated": "你好"}]},
        "baselines": {}, "failures": {},
    }
    assert has_content(report) is True


def test_render_digest_includes_translated_text_and_source_link():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "2", "url": "https://x.com/alice/status/2",
                 "text": "hello world", "timestamp": "2026-08-15T08:00:00Z", "translated": "你好世界"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "## @alice" in md
    assert "你好世界" in md
    assert "https://x.com/alice/status/2" in md
    assert "hello world" not in md  # only translated text shown, not raw English


def test_render_digest_falls_back_to_original_text_when_translated_missing():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "3", "url": "https://x.com/alice/status/3",
                 "text": "raw untranslated text", "timestamp": "2026-08-15T08:00:00Z"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)  # must not raise KeyError
    assert "raw untranslated text" in md


def test_render_digest_marks_repost_from_another_account():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "4", "url": "https://x.com/otheruser/status/4",
                 "text": "hi", "timestamp": "t", "translated": "你好",
                 "author_handle": "@otheruser", "type": "repost"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "转推自 @otheruser" in md


def test_render_digest_marks_self_repost_without_author_attribution():
    """A repost of one's own old tweet: type is still 'repost' even though
    author_handle equals the section's handle — should say "（转推）", not
    silently render as an untagged plain post."""
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "5", "url": "https://x.com/alice/status/5",
                 "text": "hi", "timestamp": "t", "translated": "你好",
                 "author_handle": "@alice", "type": "repost"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "转推自" not in md
    assert "（转推）" in md


def test_render_digest_no_type_suffix_for_plain_post():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "6", "url": "https://x.com/alice/status/6",
                 "text": "hi", "timestamp": "t", "translated": "你好",
                 "author_handle": "@alice", "type": "post"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "转推" not in md
    assert "回复" not in md
    assert "引用" not in md


def test_render_digest_marks_reply_with_target_handle():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "7", "url": "https://x.com/alice/status/7",
                 "text": "hi", "timestamp": "t", "translated": "你好",
                 "author_handle": "@alice", "type": "reply", "reply_to_handle": "@dave"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "回复 @dave" in md


def test_render_digest_marks_quote_with_quoted_content():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {
            "alice": [
                {"tweet_id": "8", "url": "https://x.com/alice/status/8",
                 "text": "hi", "timestamp": "t", "translated": "你好",
                 "author_handle": "@alice", "type": "quote",
                 "quoted_author": "@carol", "quoted_text": "Carol's original tweet"},
            ]
        },
        "baselines": {}, "failures": {},
    }
    md = render_digest(report)
    assert "引用" in md
    assert "@carol" in md
    assert "Carol's original tweet" in md


def test_render_digest_includes_failures_and_baselines_sections():
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {},
        "baselines": {"carol": 5},
        "failures": {"bob": "timeout"},
    }
    md = render_digest(report)
    assert "## 失败" in md
    assert "@bob" in md and "timeout" in md
    assert "## 已建立追踪基线" in md
    assert "@carol" in md and "5" in md


def test_cli_empty_report_prints_empty_and_writes_no_file(tmp_path):
    archive_dir = tmp_path / "feeds" / "tweets"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {},
              "archive_dir": str(archive_dir)}
    result = _run(report)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (archive_dir / "digest").exists()


def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    archive_dir = tmp_path / "feeds" / "tweets"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
        "archive_dir": str(archive_dir),
    }
    result = _run(report)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "digest-20260815T090000.md"
    assert "@carol" in written_path.read_text(encoding="utf-8")


def test_cli_digest_lands_under_archive_dir_digest(tmp_path):
    """摘要写到报告 archive_dir 下的 digest/，不读任何配置文件。"""
    archive_dir = tmp_path / "somewhere" / "feeds" / "tweets"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
        "archive_dir": str(archive_dir),
    }
    result = _run(report)
    assert result.returncode == 0, result.stderr
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.parent == archive_dir / "digest"
    assert list((archive_dir / "digest").glob("digest-*.md")) == [written_path]


def test_cli_nonempty_report_without_archive_dir_exits_1_with_message():
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {"carol": 3}, "failures": {}}
    result = _run(report)
    assert result.returncode == 1
    assert "archive_dir" in result.stderr
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""

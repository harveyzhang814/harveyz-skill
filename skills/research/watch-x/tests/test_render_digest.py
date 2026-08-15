import json
import os
import subprocess
import sys
from pathlib import Path

from render_digest import has_content, render_digest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "render_digest.py"


def _run(report: dict, data_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        env={**os.environ, "HSKILL_WATCH_X_DATA_DIR": str(data_dir)},
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
    data_dir = tmp_path / "data"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (data_dir / "digests").exists()


def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    data_dir = tmp_path / "data"
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {}, "baselines": {"carol": 3}, "failures": {},
    }
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "20260815T090000--digest.md"
    assert "@carol" in written_path.read_text(encoding="utf-8")

"""Round-trip tests for pacing_log.py's append-only JSONL audit log —
pure I/O, no timers, same tmp_path style as test_config.py."""
import json
from datetime import datetime

from browser_fetch import pacing_log


def test_append_event_writes_jsonl_line_with_event_and_fields(tmp_path):
    when = datetime(2026, 8, 18, 10, 30, 0)
    pacing_log.append_event(
        tmp_path, "cooldown", now=when, run_id="abc123", profile_url="https://x.com/someuser", waited_s=42.5
    )
    log_file = tmp_path / "timeline_pace_log-2026-08-18.jsonl"
    assert log_file.exists()
    line = log_file.read_text(encoding="utf-8").strip()
    entry = json.loads(line)
    assert entry["event"] == "cooldown"
    assert entry["run_id"] == "abc123"
    assert entry["profile_url"] == "https://x.com/someuser"
    assert entry["waited_s"] == 42.5
    assert entry["ts"] == when.isoformat(timespec="seconds")


def test_append_multiple_events_appends_lines_not_overwrite(tmp_path):
    when = datetime(2026, 8, 18, 10, 30, 0)
    pacing_log.append_event(tmp_path, "viewport", now=when, run_id="abc123", width=1400, height=900)
    pacing_log.append_event(tmp_path, "initial_dwell", now=when, run_id="abc123", dwell_s=3.2)
    log_file = tmp_path / "timeline_pace_log-2026-08-18.jsonl"
    lines = log_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["event"] == "viewport"
    assert json.loads(lines[1])["event"] == "initial_dwell"


def test_events_on_different_dates_go_to_different_files(tmp_path):
    pacing_log.append_event(tmp_path, "cooldown", now=datetime(2026, 8, 17, 23, 0, 0), run_id="a")
    pacing_log.append_event(tmp_path, "cooldown", now=datetime(2026, 8, 18, 0, 5, 0), run_id="b")
    assert (tmp_path / "timeline_pace_log-2026-08-17.jsonl").exists()
    assert (tmp_path / "timeline_pace_log-2026-08-18.jsonl").exists()
    day1 = (tmp_path / "timeline_pace_log-2026-08-17.jsonl").read_text(encoding="utf-8").strip().splitlines()
    day2 = (tmp_path / "timeline_pace_log-2026-08-18.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(day1) == 1
    assert len(day2) == 1


def test_append_event_swallows_write_failure_and_warns(tmp_path, capsys):
    when = datetime(2026, 8, 18, 10, 30, 0)
    # Make the target log path a directory instead of a file, so open(path, "a") raises IsADirectoryError.
    (tmp_path / "timeline_pace_log-2026-08-18.jsonl").mkdir()
    pacing_log.append_event(tmp_path, "cooldown", now=when, run_id="abc123")  # must not raise
    captured = capsys.readouterr()
    assert "pacing log write failed" in captured.err

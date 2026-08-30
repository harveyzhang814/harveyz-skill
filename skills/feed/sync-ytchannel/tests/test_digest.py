import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import digest
from conftest import write_config

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "digest.py"


def _video(video_id, title, published_at=None, published_text=""):
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "title": title,
        "published_text": published_text,
        "published_at": published_at,
    }


def _report(**overrides):
    report = {
        "run_time": "2026-08-22T07:00:00+00:00",
        "new": {},
        "baselines": {},
        "failures": {},
    }
    report.update(overrides)
    return report


def test_has_content_false_when_nothing_happened():
    assert digest.has_content(_report()) is False


def test_has_content_true_for_new_baselines_or_failures():
    assert digest.has_content(_report(new={"a": [_video("v1", "T")]})) is True
    assert digest.has_content(_report(baselines={"a": 30})) is True
    assert digest.has_content(_report(failures={"a": "boom"})) is True


def test_format_date_prefers_exact_timestamp():
    assert digest.format_date(_video("v", "T", published_at="2026-08-05T15:28:41+00:00")) == "2026-08-05T15:28:41+00:00"


def test_format_date_falls_back_to_relative_text():
    assert digest.format_date(_video("v", "T", published_text="2 weeks ago")) == "2 weeks ago"


def test_format_date_handles_neither():
    assert digest.format_date(_video("v", "T")) == "日期未知"


def test_render_digest_lists_translated_title_date_and_source_link():
    report = _report(new={"mattpocockuk": [
        {**_video("gaDdrDdczO4", "New Skills! v1.2", published_at="2026-08-05T15:28:41+00:00"),
         "translated": "新技能！v1.2"},
        {**_video("F3lL98Pj90o", "/wayfinder", published_text="3 weeks ago"),
         "translated": "/寻路"},
    ]})
    out = digest.render_digest(report)

    assert "# YouTube 追更摘要 — 2026-08-22T07:00:00+00:00" in out
    assert "## @mattpocockuk" in out
    assert "- [2026-08-05T15:28:41+00:00] 新技能！v1.2（[原文](https://www.youtube.com/watch?v=gaDdrDdczO4)）" in out
    assert "- [3 weeks ago] /寻路（[原文](https://www.youtube.com/watch?v=F3lL98Pj90o)）" in out
    assert "New Skills! v1.2" not in out  # 只显示译文，不显示原标题


def test_render_digest_falls_back_to_original_title_when_translated_missing():
    report = _report(new={"a": [_video("v1", "raw untranslated title")]})
    out = digest.render_digest(report)
    assert "raw untranslated title" in out


def test_render_digest_reports_baselines_and_failures():
    report = _report(baselines={"a": 30}, failures={"b": "no ytInitialData"})
    out = digest.render_digest(report)
    assert "## 已建立追踪基线" in out
    assert "- @a：起始 30 个视频，从下次运行开始报告新增" in out
    assert "## 失败" in out
    assert "- @b：no ytInitialData" in out


def test_render_digest_omits_empty_sections():
    out = digest.render_digest(_report(new={"a": [_video("v1", "T")]}))
    assert "## 失败" not in out
    assert "## 已建立追踪基线" not in out


def _run(report: dict, data_dir: Path) -> subprocess.CompletedProcess:
    config_path = data_dir.parent / "config.json"
    write_config(config_path, data_dir)
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(report),
        env={**os.environ, "HSKILL_ROSTER_CONFIG": str(config_path)},
        capture_output=True, text=True, timeout=10,
    )


def test_cli_empty_report_prints_empty_and_writes_no_file(tmp_path):
    data_dir = tmp_path / "data"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (data_dir / "youtube" / "digest").exists()


def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    data_dir = tmp_path / "data"
    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {"a": 3}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "digest-20260815T090000.md"
    assert written_path.parent == data_dir / "youtube" / "digest"


def test_cli_empty_report_removes_pending_json(tmp_path):
    data_dir = tmp_path / "data"
    pending_dir = data_dir / "youtube"
    pending_dir.mkdir(parents=True)
    pending_path = pending_dir / "pending.json"
    pending_path.write_text("{}", encoding="utf-8")

    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert not pending_path.exists()


def test_cli_written_report_removes_pending_json(tmp_path):
    data_dir = tmp_path / "data"
    pending_dir = data_dir / "youtube"
    pending_dir.mkdir(parents=True)
    pending_path = pending_dir / "pending.json"
    pending_path.write_text("{}", encoding="utf-8")

    report = {"run_time": "2026-08-15T09:00:00+00:00", "new": {}, "baselines": {"a": 3}, "failures": {}}
    result = _run(report, data_dir)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    assert not pending_path.exists()

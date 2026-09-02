import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import digest
from conftest import HSKILL_CONFIG_ENV, write_config

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "digest.py"


def _article(url, title, published_at=None, date_text=""):
    return {"url": url, "title": title, "date_text": date_text, "published_at": published_at}


def _report(**overrides):
    report = {"run_time": "2026-09-02T07:00:00+00:00", "new": {}, "baselines": {}, "failures": {}}
    report.update(overrides)
    return report


def test_has_content_false_when_nothing_happened():
    assert digest.has_content(_report()) is False


def test_has_content_true_for_new_baselines_or_failures():
    assert digest.has_content(_report(new={"a": [_article("u", "T")]})) is True
    assert digest.has_content(_report(baselines={"a": 5})) is True
    assert digest.has_content(_report(failures={"a": "boom"})) is True


def test_format_date_prefers_exact_timestamp():
    assert digest.format_date(_article("u", "T", published_at="2026-09-01T10:00:00+00:00")) == "2026-09-01T10:00:00+00:00"


def test_format_date_falls_back_to_raw_date_text():
    assert digest.format_date(_article("u", "T", date_text="3 days ago")) == "3 days ago"


def test_format_date_handles_neither():
    assert digest.format_date(_article("u", "T")) == "日期未知"


def test_render_digest_lists_translated_title_date_and_source_link():
    report = _report(new={"simonwillison-net": [
        {**_article("https://simonwillison.net/1", "Some Title", published_at="2026-09-01T10:00:00+00:00"),
         "translated": "某标题"},
    ]})
    out = digest.render_digest(report)
    assert "# 网站追更摘要 — 2026-09-02T07:00:00+00:00" in out
    assert "## simonwillison-net" in out
    assert "- [2026-09-01T10:00:00+00:00] 某标题（[原文](https://simonwillison.net/1)）" in out
    assert "Some Title" not in out


def test_render_digest_falls_back_to_original_title_when_translated_missing():
    report = _report(new={"a": [_article("u", "raw untranslated title")]})
    assert "raw untranslated title" in digest.render_digest(report)


def test_render_digest_tags_recalibrated_channels_in_new_section():
    report = _report(new={"a": [_article("u", "T")]}, recalibrated=["a"])
    out = digest.render_digest(report)
    assert "## a  [本轮重新标定过抽取规则]" in out


def test_render_digest_tags_recalibrated_channels_in_baseline_section():
    report = _report(baselines={"a": 4}, recalibrated=["a"])
    out = digest.render_digest(report)
    assert "- a  [本轮重新标定过抽取规则]：起始 4 篇文章，从下次运行开始报告新增" in out


def test_render_digest_does_not_tag_channels_not_in_recalibrated():
    report = _report(new={"a": [_article("u", "T")]}, recalibrated=["b"])
    out = digest.render_digest(report)
    assert "## a" in out
    assert "[本轮重新标定过抽取规则]" not in out


def test_render_digest_reports_failures():
    report = _report(failures={"b": "NO_RULE 标定 3 轮未过"})
    out = digest.render_digest(report)
    assert "## 失败" in out
    assert "- b：NO_RULE 标定 3 轮未过" in out


def test_render_digest_omits_empty_sections():
    out = digest.render_digest(_report(new={"a": [_article("u", "T")]}))
    assert "## 失败" not in out
    assert "## 已建立追踪基线" not in out


def _run(report: dict, root: Path) -> subprocess.CompletedProcess:
    config_path = root.parent / "config.json"
    write_config(config_path, root)
    return subprocess.run(
        [sys.executable, str(SCRIPT)], input=json.dumps(report),
        env={**os.environ, HSKILL_CONFIG_ENV: str(config_path)},
        capture_output=True, text=True, timeout=10,
    )


def test_cli_empty_report_prints_empty_and_writes_no_file(tmp_path):
    root = tmp_path / "knowledge"
    result = _run(_report(), root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "EMPTY"
    assert not (root / "feeds" / "website" / "digest").exists()


def test_cli_nonempty_report_writes_timestamped_file(tmp_path):
    root = tmp_path / "knowledge"
    result = _run(_report(baselines={"a": 3}), root)
    assert result.returncode == 0, result.stderr
    assert "WRITTEN:" in result.stdout
    written_path = Path(result.stdout.strip().split("WRITTEN: ", 1)[1])
    assert written_path.exists()
    assert written_path.name == "digest-20260902T070000.md"
    assert written_path.parent == root / "feeds" / "website" / "digest"

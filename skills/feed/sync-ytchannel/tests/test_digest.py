import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import digest


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
    assert digest.format_date(_video("v", "T", published_at="2026-08-05T15:28:41+00:00")) == "2026-08-05"


def test_format_date_falls_back_to_relative_text():
    assert digest.format_date(_video("v", "T", published_text="2 weeks ago")) == "2 weeks ago"


def test_format_date_handles_neither():
    assert digest.format_date(_video("v", "T")) == "日期未知"


def test_render_digest_lists_title_date_and_url():
    report = _report(new={"mattpocockuk": [
        _video("gaDdrDdczO4", "New Skills! v1.2", published_at="2026-08-05T15:28:41+00:00"),
        _video("F3lL98Pj90o", "/wayfinder", published_text="3 weeks ago"),
    ]})
    out = digest.render_digest(report)

    assert "# YouTube 追更摘要 — 2026-08-22T07:00:00+00:00" in out
    assert "## @mattpocockuk" in out
    assert "- [2026-08-05] New Skills! v1.2（https://www.youtube.com/watch?v=gaDdrDdczO4）" in out
    assert "- [3 weeks ago] /wayfinder（https://www.youtube.com/watch?v=F3lL98Pj90o）" in out


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

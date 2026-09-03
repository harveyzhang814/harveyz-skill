"""site_rules 目录格式的读路径 —— spec §3.1/§3.2/§3.4。
写路径在 Task 3，本文件只造目录再读。"""
import json
from pathlib import Path

import pytest

from browser_fetch import site_rules

SELECTORS = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}


def _write_dir_rule(data_dir: Path, domain: str, rule: dict, files: dict | None = None) -> Path:
    d = data_dir / "site_rules" / domain
    d.mkdir(parents=True, exist_ok=True)
    (d / "rule.json").write_text(json.dumps(rule), encoding="utf-8")
    for name, body in (files or {}).items():
        (d / name).write_text(body, encoding="utf-8")
    return d


def _selector_rule(domain="example.com", mode="selector", **extra) -> dict:
    rule = {
        "schema_version": 2, "domain": domain,
        "list_url": f"https://{domain}/", "mode": mode,
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }
    rule.update(extra)
    return rule


def test_reads_a_directory_format_selector_rule(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule())
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "selector"
    assert rule["selectors"] == SELECTORS


def test_reads_transform_source_alongside_the_rule(tmp_path):
    _write_dir_rule(
        tmp_path, "example.com",
        _selector_rule(mode="selector+transform"),
        {"transform.js": "(a) => a"},
    )
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["transform_js"] == "(a) => a"


def test_flat_legacy_file_is_read_as_a_selector_rule(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://example.com/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "selector"
    assert rule["schema_version"] == 1
    assert rule["selectors"] == SELECTORS


def test_directory_format_wins_over_a_leftover_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://stale/",
        "selectors": {}, "calibrated_at": "old", "sample": [],
    }), encoding="utf-8")
    _write_dir_rule(tmp_path, "example.com", _selector_rule())
    assert site_rules.get_rule(tmp_path, "example.com")["list_url"] == "https://example.com/"


def test_missing_rule_returns_none(tmp_path):
    assert site_rules.get_rule(tmp_path, "nope.example") is None


def test_transform_mode_without_the_js_file_is_corrupt(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(mode="selector+transform"))
    with pytest.raises(site_rules.RuleCorruptError, match="transform.js"):
        site_rules.get_rule(tmp_path, "example.com")


def test_selector_mode_with_a_stray_transform_file_is_corrupt(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(), {"transform.js": "(a) => a"})
    with pytest.raises(site_rules.RuleCorruptError, match="transform.js"):
        site_rules.get_rule(tmp_path, "example.com")


def test_unsupported_mode_is_corrupt_not_silently_downgraded(tmp_path):
    _write_dir_rule(tmp_path, "example.com", _selector_rule(mode="script"))
    with pytest.raises(site_rules.RuleCorruptError, match="mode"):
        site_rules.get_rule(tmp_path, "example.com")


def test_selector_mode_missing_selectors_is_corrupt(tmp_path):
    rule = _selector_rule()
    del rule["selectors"]
    _write_dir_rule(tmp_path, "example.com", rule)
    with pytest.raises(site_rules.RuleCorruptError, match="selectors"):
        site_rules.get_rule(tmp_path, "example.com")


def test_path_traversal_domain_still_rejected(tmp_path):
    for bad in ("../../../tmp/evil", "a/b", "a\\b"):
        with pytest.raises(ValueError):
            site_rules.get_rule(tmp_path, bad)

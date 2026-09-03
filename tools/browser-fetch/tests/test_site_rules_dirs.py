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


def test_set_rule_writes_the_directory_format(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    d = tmp_path / "site_rules" / "example.com"
    assert (d / "rule.json").exists()
    assert json.loads((d / "rule.json").read_text())["schema_version"] == 2
    assert json.loads((d / "rule.json").read_text())["mode"] == "selector"


def test_set_rule_with_transform_writes_the_js_file(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
        mode="selector+transform", transform_js="(a) => a.slice(1)",
    )
    d = tmp_path / "site_rules" / "example.com"
    assert (d / "transform.js").read_text(encoding="utf-8") == "(a) => a.slice(1)"
    assert site_rules.get_rule(tmp_path, "example.com")["transform_js"] == "(a) => a.slice(1)"


def test_transform_mode_without_source_is_rejected_at_write_time(tmp_path):
    with pytest.raises(ValueError, match="transform_js"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
            mode="selector+transform",
        )


def test_unsupported_mode_is_rejected_at_write_time(tmp_path):
    with pytest.raises(ValueError, match="mode"):
        site_rules.set_rule(
            tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
            mode="script",
        )


def test_rewriting_a_rule_drops_the_previous_transform_file(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t1",
        mode="selector+transform", transform_js="(a) => a",
    )
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t2")
    d = tmp_path / "site_rules" / "example.com"
    assert not (d / "transform.js").exists()
    assert site_rules.get_rule(tmp_path, "example.com")["mode"] == "selector"


def test_writing_migrates_away_from_a_legacy_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    flat = rules_dir / "example.com.json"
    flat.write_text(json.dumps({
        "domain": "example.com", "list_url": "https://old/",
        "selectors": {}, "calibrated_at": "old", "sample": [],
    }), encoding="utf-8")

    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")

    assert not flat.exists()
    assert (rules_dir / "example.com" / "rule.json").exists()


def test_no_tmp_or_old_directory_survives_a_successful_write(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t2")
    names = {p.name for p in (tmp_path / "site_rules").iterdir()}
    assert names == {"example.com"}


def test_list_rules_covers_both_directory_and_flat_rules(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    rules_dir = tmp_path / "site_rules"
    (rules_dir / "b.example.json").write_text(json.dumps({
        "domain": "b.example", "list_url": "https://b.example/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    assert {r["domain"] for r in site_rules.list_rules(tmp_path)} == {"a.example", "b.example"}


def test_list_rules_ignores_tmp_and_old_leftovers(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    rules_dir = tmp_path / "site_rules"
    (rules_dir / "a.example.tmp").mkdir()
    (rules_dir / "a.example.old").mkdir()
    assert {r["domain"] for r in site_rules.list_rules(tmp_path)} == {"a.example"}


def test_list_rules_skips_a_corrupt_rule_instead_of_failing_the_whole_listing(tmp_path):
    site_rules.set_rule(tmp_path, "good.example", "https://good.example/", SELECTORS, [], "t")
    _write_dir_rule(tmp_path, "bad.example", _selector_rule("bad.example", mode="script"))
    listed = site_rules.list_rules(tmp_path)
    assert {r["domain"] for r in listed} == {"good.example"}


def test_remove_rule_deletes_the_whole_directory(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t",
        mode="selector+transform", transform_js="(a) => a",
    )
    assert site_rules.remove_rule(tmp_path, "example.com") is True
    assert not (tmp_path / "site_rules" / "example.com").exists()
    assert site_rules.get_rule(tmp_path, "example.com") is None


def test_remove_rule_also_deletes_a_legacy_flat_file(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://example.com/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
    }), encoding="utf-8")
    assert site_rules.remove_rule(tmp_path, "example.com") is True
    assert site_rules.get_rule(tmp_path, "example.com") is None


def test_remove_rule_returns_false_when_nothing_to_remove(tmp_path):
    assert site_rules.remove_rule(tmp_path, "nope.example") is False


def test_flat_file_with_a_bogus_mode_is_forced_back_to_selector(tmp_path):
    rules_dir = tmp_path / "site_rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "example.com.json").write_text(json.dumps({
        "domain": "example.com", "list_url": "https://example.com/",
        "selectors": SELECTORS, "calibrated_at": "t", "sample": [],
        "mode": "script",
    }), encoding="utf-8")
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["mode"] == "selector"

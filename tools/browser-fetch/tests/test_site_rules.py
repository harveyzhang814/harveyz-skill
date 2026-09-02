"""Unit tests for site_rules.py's per-domain selector-rule store — pure
filesystem I/O, no playwright, no network. Mirrors test_config.py's style
for the sibling config.py module."""
from browser_fetch import site_rules

SELECTORS = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}


def test_get_rule_returns_none_when_unset(tmp_path):
    assert site_rules.get_rule(tmp_path, "example.com") is None


def test_set_then_get_round_trips(tmp_path):
    site_rules.set_rule(
        tmp_path, "example.com", "https://example.com/", SELECTORS,
        [{"title": "T", "url": "https://example.com/1", "date_text": "d"}],
        "2026-09-02T10:00:00+00:00",
    )
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["domain"] == "example.com"
    assert rule["list_url"] == "https://example.com/"
    assert rule["selectors"] == SELECTORS
    assert rule["calibrated_at"] == "2026-09-02T10:00:00+00:00"
    assert rule["sample"][0]["title"] == "T"


def test_set_overwrites_previous_rule_for_same_domain(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t1")
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/new", SELECTORS, [], "t2")
    rule = site_rules.get_rule(tmp_path, "example.com")
    assert rule["list_url"] == "https://example.com/new"
    assert rule["calibrated_at"] == "t2"


def test_rule_file_written_under_site_rules_subdir(tmp_path):
    site_rules.set_rule(tmp_path, "example.com", "https://example.com/", SELECTORS, [], "t")
    assert (tmp_path / "site_rules" / "example.com.json").exists()


def test_list_rules_empty_when_none_set(tmp_path):
    assert site_rules.list_rules(tmp_path) == []


def test_list_rules_returns_every_calibrated_domain(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    site_rules.set_rule(tmp_path, "b.example", "https://b.example/", SELECTORS, [], "t")
    domains = {r["domain"] for r in site_rules.list_rules(tmp_path)}
    assert domains == {"a.example", "b.example"}


def test_remove_rule_deletes_and_returns_true(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    assert site_rules.remove_rule(tmp_path, "a.example") is True
    assert site_rules.get_rule(tmp_path, "a.example") is None


def test_remove_rule_returns_false_when_nothing_to_remove(tmp_path):
    assert site_rules.remove_rule(tmp_path, "nowhere.example") is False


def test_rules_for_different_domains_are_isolated(tmp_path):
    site_rules.set_rule(tmp_path, "a.example", "https://a.example/", SELECTORS, [], "t")
    assert site_rules.get_rule(tmp_path, "b.example") is None

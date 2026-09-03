import json


def test_set_then_get_round_trips(run_cli):
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}
    proc, payload = run_cli(
        "articles-rule", "set", "example.com",
        "--selectors", json.dumps(selectors),
        "--list-url", "https://example.com/",
        "--sample", json.dumps([{"title": "T", "url": "u", "date_text": "d"}]),
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["domain"] == "example.com"
    assert "calibrated_at" in payload

    proc, payload = run_cli("articles-rule", "get", "example.com")
    assert proc.returncode == 0, proc.stderr
    assert payload["selectors"] == selectors
    assert payload["list_url"] == "https://example.com/"


def test_get_unset_domain_exits_2_with_no_rule(run_cli):
    proc, _ = run_cli("articles-rule", "get", "nowhere.example")
    assert proc.returncode == 2
    assert "NO_RULE" in proc.stderr


def test_sample_defaults_to_empty_list(run_cli):
    proc, payload = run_cli(
        "articles-rule", "set", "example.com",
        "--selectors", json.dumps({"item": "x", "title": "y", "link": "z"}),
        "--list-url", "https://example.com/",
    )
    assert proc.returncode == 0, proc.stderr
    proc, payload = run_cli("articles-rule", "get", "example.com")
    assert payload["sample"] == []


def test_list_returns_every_set_domain(run_cli):
    for domain in ("a.example", "b.example"):
        run_cli("articles-rule", "set", domain,
                "--selectors", json.dumps({"item": "x", "title": "y", "link": "z"}),
                "--list-url", f"https://{domain}/")
    proc, payload = run_cli("articles-rule", "list")
    assert proc.returncode == 0, proc.stderr
    assert {r["domain"] for r in payload["rules"]} == {"a.example", "b.example"}


def test_list_empty_when_none_set(run_cli):
    proc, payload = run_cli("articles-rule", "list")
    assert proc.returncode == 0, proc.stderr
    assert payload["rules"] == []


def test_rm_removes_then_reports_false_on_second_call(run_cli):
    run_cli("articles-rule", "set", "gone.example",
            "--selectors", json.dumps({"item": "x", "title": "y", "link": "z"}),
            "--list-url", "https://gone.example/")
    proc, payload = run_cli("articles-rule", "rm", "gone.example")
    assert proc.returncode == 0, proc.stderr
    assert payload == {"ok": True, "removed": True}
    proc, payload = run_cli("articles-rule", "rm", "gone.example")
    assert payload == {"ok": True, "removed": False}

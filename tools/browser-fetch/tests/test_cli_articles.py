import json

ARTICLE_SELECTORS = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}


def test_articles_probe_extracts_items_without_persisting_a_rule(run_cli, articles_fixture_server):
    proc, payload = run_cli(
        "articles-probe", articles_fixture_server, "--selectors", json.dumps(ARTICLE_SELECTORS),
    )
    assert proc.returncode == 0, proc.stderr
    articles = payload["articles"]
    assert len(articles) == 3
    assert articles[0]["title"] == "First post"
    assert articles[0]["url"].endswith("/posts/1")
    assert articles[0]["date_text"] == "2026-01-01"

    list_proc, list_payload = run_cli("articles-rule", "list")
    assert list_payload["rules"] == []


def test_articles_probe_drops_items_with_no_matching_link(run_cli, articles_fixture_server):
    selectors = {**ARTICLE_SELECTORS, "link": "h4 a"}  # fixture has no <h4>
    proc, payload = run_cli(
        "articles-probe", articles_fixture_server, "--selectors", json.dumps(selectors),
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["articles"] == []


def test_articles_probe_missing_date_selector_yields_empty_date_text(run_cli, articles_fixture_server):
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a"}
    proc, payload = run_cli(
        "articles-probe", articles_fixture_server, "--selectors", json.dumps(selectors),
    )
    assert proc.returncode == 0, proc.stderr
    assert all(a["date_text"] == "" for a in payload["articles"])


def test_articles_rejects_uncalibrated_domain(run_cli, articles_fixture_server):
    proc, _ = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 2
    assert "NO_RULE" in proc.stderr


def test_articles_uses_the_calibrated_rule_for_that_domain(run_cli, articles_fixture_server):
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(ARTICLE_SELECTORS),
        "--list-url", articles_fixture_server,
    )
    proc, payload = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 0, proc.stderr
    assert payload["domain"] == "127.0.0.1"
    assert len(payload["articles"]) == 3


def test_articles_rejects_file_scheme(run_cli):
    proc, _ = run_cli("articles", "file:///etc/passwd")
    assert proc.returncode == 2
    assert "only http/https allowed" in proc.stderr


def test_articles_probe_rejects_file_scheme(run_cli):
    proc, _ = run_cli("articles-probe", "file:///etc/passwd", "--selectors", "{}")
    assert proc.returncode == 2
    assert "only http/https allowed" in proc.stderr


def test_articles_output_carries_exactly_the_contract_keys(run_cli, articles_fixture_server):
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(ARTICLE_SELECTORS),
        "--list-url", articles_fixture_server,
    )
    _, payload = run_cli("articles", articles_fixture_server)
    for article in payload["articles"]:
        assert set(article) == {"title", "url", "date_text"}


def test_articles_urls_stay_absolute_after_normalization(run_cli, articles_fixture_server):
    # fixture 页面里的 href 是相对的（/posts/1），一档模板用 linkEl.href 已经
    # 解析成绝对；urljoin 幂等，所以这里断言的是"归一化没有把它弄坏"。
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(ARTICLE_SELECTORS),
        "--list-url", articles_fixture_server,
    )
    _, payload = run_cli("articles", articles_fixture_server)
    assert all(a["url"].startswith("http://127.0.0.1:") for a in payload["articles"])
    assert payload["articles"][0]["url"].endswith("/posts/1")

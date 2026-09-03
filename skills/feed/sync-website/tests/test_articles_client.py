import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_cli  # noqa: E402
import articles_client  # noqa: E402


def test_fetch_articles_builds_cli_args_and_returns_the_list(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"domain": "example.com", "articles": [{"title": "T", "url": "https://example.com/1", "date_text": "d"}]}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    articles = asyncio.run(articles_client.fetch_articles(
        "https://example.com/", chrome_profile="/tmp/P"))

    assert articles == [{"title": "T", "url": "https://example.com/1", "date_text": "d"}]
    assert seen["args"] == ("articles", "https://example.com/", "--chrome-profile", "/tmp/P")


def test_fetch_articles_omits_profile_when_absent(monkeypatch):
    seen = {}
    monkeypatch.setattr(browser_fetch_cli, "call",
                        lambda *a: (seen.update(args=a), {"domain": "e", "articles": []})[1])
    asyncio.run(articles_client.fetch_articles("https://example.com/"))
    assert "--chrome-profile" not in seen["args"]


def test_fetch_articles_raises_no_rule_error_on_no_rule(monkeypatch):
    def boom(*args):
        raise RuntimeError("NO_RULE: example.com")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(articles_client.NoRuleError, match="NO_RULE: example.com"):
        asyncio.run(articles_client.fetch_articles("https://example.com/"))


def test_fetch_articles_propagates_other_failures_unchanged(monkeypatch):
    def boom(*args):
        raise RuntimeError("timeout navigating to page")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(RuntimeError, match="timeout navigating"):
        asyncio.run(articles_client.fetch_articles("https://example.com/"))


def test_probe_articles_passes_transform_file_when_given(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"articles": []}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    asyncio.run(articles_client.probe_articles(
        "https://e.com/", {"item": "div"}, transform_file="/tmp/t.js"))
    assert "--transform-file" in seen["args"]
    assert "/tmp/t.js" in seen["args"]


def test_probe_articles_omits_transform_file_when_absent(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"articles": []}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    asyncio.run(articles_client.probe_articles("https://e.com/", {"item": "div"}))
    assert "--transform-file" not in seen["args"]


def test_set_rule_rejects_an_unsupported_mode_before_shelling_out(monkeypatch):
    def boom(*args):
        raise AssertionError("不该走到 CLI")

    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(ValueError, match="mode"):
        asyncio.run(articles_client.set_rule(
            "e.com", "https://e.com/", {"item": "div"}, [], mode="script"))

"""Only the deterministic, network-free path is covered here — per-channel
diff behaviour lives in test_cursor.py (pure), the roster round-trip in
test_roster_client.py, and the NO_RULE→needs_calibration routing here.
Actually resolving needs_calibration (running calibrate, re-fetching) is
the orchestrating agent's job per SKILL.md, not this script's — see
fetch_new_articles.py's module docstring."""
import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import fetch_new_articles
import roster_client
from articles_client import NoRuleError, TransformError
from config import get_data_dir


def _article(url, title="T", date_text="1 day ago"):
    return {"url": url, "title": title, "date_text": date_text}


class _FakeRoster:
    def __init__(self):
        self.channels_list: list[dict] = []
        self.cursors: dict[str, list[str] | None] = {}
        self.errors: dict[str, str] = {}

    def watch(self, handle: str, url: str) -> None:
        self.channels_list.append({
            "creator_id": handle.lower(), "platform": "website",
            "handle": handle, "url": url,
        })
        self.cursors.setdefault(handle, None)


@pytest.fixture(autouse=True)
def fake_roster(monkeypatch):
    fake = _FakeRoster()
    monkeypatch.setattr(roster_client, "channels", lambda: list(fake.channels_list))
    monkeypatch.setattr(roster_client, "get_cursor", lambda h: fake.cursors.get(h))
    monkeypatch.setattr(
        roster_client, "set_cursor",
        lambda h, seen_urls, run_time: fake.cursors.__setitem__(h, seen_urls))
    monkeypatch.setattr(
        roster_client, "set_error",
        lambda h, error, run_time: fake.errors.__setitem__(h, error))
    return fake


@pytest.fixture
def fake_fetch(monkeypatch):
    responses: dict[str, object] = {}

    async def _fetch(list_url, chrome_profile=None):
        value = responses[list_url]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(fetch_new_articles, "fetch_articles", _fetch)
    return responses


def test_first_fetch_establishes_baseline_without_listing_articles(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = [_article("https://a.example/1"), _article("https://a.example/2")]

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["baselines"] == {"a": 2}
    assert "a" not in report["new"]
    assert report["cursors"]["a"] == ["https://a.example/1", "https://a.example/2"]


def test_new_article_is_reported(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_roster.cursors["a"] = ["https://a.example/1"]
    fake_fetch["https://a.example/"] = [_article("https://a.example/2"), _article("https://a.example/1")]

    report = asyncio.run(fetch_new_articles.run(None))

    assert [a["url"] for a in report["new"]["a"]] == ["https://a.example/2"]
    assert report["cursors"]["a"] == ["https://a.example/2", "https://a.example/1"]


def test_no_rule_error_routes_to_needs_calibration_not_failures(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = NoRuleError("NO_RULE: a.example")

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["needs_calibration"] == {"a": "https://a.example/"}
    assert report["failures"] == {}
    assert "a" not in report["cursors"]


def test_empty_articles_result_also_routes_to_needs_calibration(fake_roster, fake_fetch):
    """A calibrated rule that now extracts zero items (site changed under
    it) is indistinguishable in effect from never having been calibrated —
    both need a human/model to look at the page again."""
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = []

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["needs_calibration"] == {"a": "https://a.example/"}
    assert "a" not in report["failures"]


def test_transform_error_routes_to_needs_calibration_not_failures(fake_roster, fake_fetch):
    """spec §6: a throwing/timing-out tier-2 transform is treated like any
    other extraction failure — self-heal, not a permanent failures entry."""
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = TransformError("TRANSFORM_ERROR: Error: boom")

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["needs_calibration"] == {"a": "https://a.example/"}
    assert report["failures"] == {}
    assert "a" not in report["cursors"]
    assert fake_roster.errors == {}


def test_other_exceptions_still_route_to_failures(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = RuntimeError("navigation timeout")

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["failures"] == {"a": "navigation timeout"}
    assert report["needs_calibration"] == {}
    assert fake_roster.errors == {"a": "navigation timeout"}


def test_run_isolates_per_channel_outcomes(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_roster.watch("b", "https://b.example/")
    fake_fetch["https://a.example/"] = NoRuleError("NO_RULE: a.example")
    fake_fetch["https://b.example/"] = [_article("https://b.example/1")]

    report = asyncio.run(fetch_new_articles.run(None))

    assert report["needs_calibration"] == {"a": "https://a.example/"}
    assert report["baselines"] == {"b": 1}


def test_handle_filter_only_fetches_the_requested_handles(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_roster.watch("b", "https://b.example/")
    fake_fetch["https://a.example/"] = [_article("https://a.example/1")]
    fake_fetch["https://b.example/"] = [_article("https://b.example/1")]

    report = asyncio.run(fetch_new_articles.run(None, ["a"]))

    assert report["baselines"] == {"a": 1}
    assert "b" not in report["baselines"]


def test_handle_filter_reports_unknown_handle_as_a_failure(fake_roster, fake_fetch):
    report = asyncio.run(fetch_new_articles.run(None, ["ghost"]))
    assert report["failures"] == {"ghost": "不在 roster 名册里"}


def test_report_json_shape(fake_roster, fake_fetch):
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = [_article("https://a.example/1")]

    report = asyncio.run(fetch_new_articles.run(None))

    assert set(report) == {"run_time", "new", "baselines", "failures", "needs_calibration", "cursors"}
    json.dumps(report)


def test_main_prints_report(fake_roster, fake_fetch, capsys):
    fake_roster.watch("a", "https://a.example/")
    fake_fetch["https://a.example/"] = [_article("https://a.example/1")]

    fetch_new_articles.main()

    report = json.loads(capsys.readouterr().out)
    assert report["baselines"] == {"a": 1}

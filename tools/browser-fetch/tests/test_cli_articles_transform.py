"""二档 transform 的隔离求值 —— spec §2。

这套分级的支点：transform 必须拿不到目标站的 DOM 与 cookie，否则它跟三档
能力相同，"二档可自动、三档要人批"就没有实质差别。这里的三条隔离断言是
那条设计主张的可证伪形式。
"""
import asyncio
import json

import pytest

from browser_fetch import core

# core._get_context caches Playwright connections/contexts at module scope
# (by design — see core.py), keyed only by context key, with no per-test
# teardown. pytest-asyncio's default is a fresh event loop per test
# function; reusing a cached connection under a second, later-created loop
# hangs forever (its reader/writer tasks died with the first loop; nothing
# resolves the second loop's futures). Sharing one event loop across this
# file's async tests keeps that cache usage consistent with the loop it was
# created under, matching how a single CLI invocation uses one event loop
# for its whole lifetime.

ARTICLES = [
    {"title": "a", "url": "https://example.com/1", "date_text": "d1"},
    {"title": "b", "url": "https://example.com/2", "date_text": "d2"},
]
LIST_URL = "https://example.com/blog"


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_receives_the_articles_array():
    out = await core._run_transform(ARTICLES, "(items) => items.slice(1)", LIST_URL)
    assert [a["title"] for a in out] == ["b"]


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_output_goes_through_normalization():
    js = "(items) => items.map(i => ({...i, title: '  x  y  ', url: '/rel'}))"
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "x y"
    assert out[0]["url"] == "https://example.com/rel"


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_cannot_read_target_site_cookies():
    # about:blank navigated to directly (no opener) has an opaque origin in
    # Chromium, so document.cookie doesn't just read empty — it throws
    # SecurityError (spec: cookie access is disallowed for cookie-averse /
    # opaque-origin documents). That's a stronger form of "no cookie
    # access" than the brief's `document.cookie || 'EMPTY'` anticipated
    # (which assumed a falsy empty-string read); the try/catch here adapts
    # to that real, deterministic browser behavior while keeping the same
    # assertion — the transform still ends up with no target-site cookie.
    js = (
        "(items) => { let c; try { c = document.cookie; } catch (e) { c = ''; } "
        "return [{title: c || 'EMPTY', url: 'https://x/1', date_text: ''}]; }"
    )
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "EMPTY"


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_does_not_run_on_the_target_page():
    js = "(items) => [{title: location.href, url: 'https://x/1', date_text: ''}]"
    out = await core._run_transform(ARTICLES, js, LIST_URL)
    assert out[0]["title"] == "about:blank"


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_returning_a_non_array_yields_no_articles():
    out = await core._run_transform(ARTICLES, "(items) => 42", LIST_URL)
    assert out == []


def test_transform_rule_is_applied_on_the_production_path(run_cli, articles_fixture_server, tmp_path):
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items.slice(0, 1)", encoding="utf-8")
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}

    proc, _ = run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(selectors),
        "--list-url", articles_fixture_server,
        "--mode", "selector+transform",
        "--transform-file", str(transform),
    )
    assert proc.returncode == 0, proc.stderr

    proc, payload = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 1  # selector 抽 3 条，transform 砍到 1 条


def test_probe_can_try_a_transform_without_persisting_anything(run_cli, articles_fixture_server, tmp_path):
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items.slice(0, 2)", encoding="utf-8")
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}

    proc, payload = run_cli(
        "articles-probe", articles_fixture_server,
        "--selectors", json.dumps(selectors),
        "--transform-file", str(transform),
    )
    assert proc.returncode == 0, proc.stderr
    assert len(payload["articles"]) == 2

    _, listing = run_cli("articles-rule", "list")
    assert listing["rules"] == []


def test_a_corrupt_rule_fails_the_run_instead_of_downgrading(run_cli, articles_fixture_server, tmp_path):
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}
    transform = tmp_path / "t.js"
    transform.write_text("(items) => items", encoding="utf-8")
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(selectors),
        "--list-url", articles_fixture_server,
        "--mode", "selector+transform",
        "--transform-file", str(transform),
    )
    # 手工删掉 transform.js，模拟规则目录被破坏
    (tmp_path / "data" / "site_rules" / "127.0.0.1" / "transform.js").unlink()

    proc, _ = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 1
    assert "transform.js" in proc.stderr


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_that_never_resolves_times_out(monkeypatch):
    # spec §6: a transform that fails (throws, or here times out) is an
    # extraction failure, not a bare asyncio internal — it must carry the
    # TRANSFORM_ERROR: prefix so sync-website's fetch_new_articles.py can
    # route it to self-heal instead of a permanent failure bucket.
    monkeypatch.setattr(core, "TRANSFORM_TIMEOUT_S", 0.1)
    js = "(items) => new Promise(() => {})"
    with pytest.raises(RuntimeError, match="^TRANSFORM_ERROR:"):
        await core._run_transform(ARTICLES, js, LIST_URL)


@pytest.mark.asyncio(loop_scope="module")
async def test_transform_that_throws_is_tagged_with_transform_error_prefix():
    js = "(items) => { throw new Error('boom'); }"
    with pytest.raises(RuntimeError, match="^TRANSFORM_ERROR:") as exc_info:
        await core._run_transform(ARTICLES, js, LIST_URL)
    assert "boom" in str(exc_info.value)


def test_transform_error_surfaces_on_the_production_path(run_cli, articles_fixture_server, tmp_path):
    """End-to-end: a throwing transform.js exits 1 with a TRANSFORM_ERROR:
    prefix on stderr, distinguishable from NO_RULE and other failures —
    sync-website's articles_client.py string-matches this prefix to route
    the channel to self-heal (spec §6) instead of a permanent failure."""
    selectors = {"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"}
    transform = tmp_path / "t.js"
    transform.write_text("(items) => { throw new Error('boom'); }", encoding="utf-8")
    run_cli(
        "articles-rule", "set", "127.0.0.1",
        "--selectors", json.dumps(selectors),
        "--list-url", articles_fixture_server,
        "--mode", "selector+transform",
        "--transform-file", str(transform),
    )

    proc, _ = run_cli("articles", articles_fixture_server)
    assert proc.returncode == 1
    assert "TRANSFORM_ERROR:" in proc.stderr

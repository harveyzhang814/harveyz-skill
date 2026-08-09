import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.async_api import async_playwright

from browser_fetch_mcp.extractors import EXTRACT_JS, wechat_publish_date_from_ct

SERVER_MODULE = "browser_fetch_mcp.server"


def _server_params(data_dir: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
    )


async def _call_fetch_article(session, **kwargs):
    result = await session.call_tool("fetch_article", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_article_generic_real_network(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://en.wikipedia.org/wiki/Model_Context_Protocol",
                output_dir=str(output_dir),
                output_format="json",
            )
    assert payload["site"] == "generic"
    assert len(payload["blocks"]) > 5
    assert "Model Context Protocol" in payload["title"]
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0


async def test_fetch_article_arxiv_real_network(tmp_path):
    """Real arXiv HTML paper page. If this specific ID has been withdrawn
    or lacks an HTML render by the time this runs, swap in any current
    arxiv.org/html/<id> URL — check https://arxiv.org/list/cs.AI/recent."""
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://arxiv.org/html/2608.06020",
                output_dir=str(output_dir),
                output_format="json",
            )
    assert payload["site"] == "arxiv"
    assert len(payload["blocks"]) > 5


async def test_fetch_article_x_dot_com_without_chrome_profile_is_rejected(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
            )
    assert result.is_error is True


async def test_fetch_article_rejects_file_scheme(tmp_path):
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="file:///etc/passwd",
                output_dir=str(output_dir),
            )
    assert result.is_error is True


async def test_fetch_article_thin_retry_triggers_with_chrome_profile_no_matching_cookies(tmp_path):
    """example.com is naturally thin (well under 20 blocks / 3000 chars).
    With an empty (non-real) chrome_profile dir, the retry attempt runs
    but finds no cookies, so cookies_injected stays 0 — this only checks
    that the retry path executes and doesn't crash, not that it recovers
    real content (that needs a real logged-in Chrome profile, out of
    scope for an automated test)."""
    empty_profile = tmp_path / "EmptyProfile"
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
                chrome_profile=str(empty_profile),
            )
    assert payload["thin_retry_used"] is True
    assert payload["cookies_injected"] == 0


async def _evaluate_extraction(site: str, html: str, tmp_path: Path) -> dict:
    """Test-only helper: load `html` via page.set_content() (NOT the
    production page.goto() path — this exists purely to feed a synthetic
    DOM into the extraction JS for fixture-based correctness testing) and
    run the site's extraction JS against it."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        result = await page.evaluate(EXTRACT_JS[site])
        await browser.close()
    return result


_WECHAT_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<head>
  <title>WeChat Test Article</title>
  <script>var ct = "1719763200";</script>
</head>
<body>
  <h1 id="activity-name">WeChat Test Article</h1>
  <a id="js_name">Test Official Account</a>
  <div id="js_content" style="visibility: hidden; opacity: 0;">
    <p>First paragraph with sufficient content to be captured by the wechat extraction JS under test here.</p>
    <p>Second paragraph providing additional body text for the content extraction verification test here.</p>
    <section><img data-src="https://mmbiz.qpic.cn/test/640?wx_fmt=png" alt="pic"></section>
  </div>
</body>
</html>
"""


async def test_extract_js_wechat_reads_hidden_content_via_fixture(tmp_path):
    result = await _evaluate_extraction("wechat", _WECHAT_FIXTURE_HTML, tmp_path)
    assert result["title"] == "WeChat Test Article"
    assert result["author"] == "Test Official Account"
    assert len(result["blocks"]) == 2
    assert "First paragraph" in result["blocks"][0]["content"]
    assert len(result["imageBlocks"]) == 1
    assert result["imageBlocks"][0]["src"] == "https://mmbiz.qpic.cn/test/640?wx_fmt=png"

    publish_date = wechat_publish_date_from_ct(result["ct"])
    assert publish_date == "2024-07-01"


_ARXIV_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Test Paper Title</title></head>
<body>
<main>
  <h1>Test Paper Title</h1>
  <p>This is the abstract paragraph with enough characters to pass the ten character minimum length check.</p>
  <table class="ltx_tabular">
    <tr><th>Metric</th><th>Score</th></tr>
    <tr><td>Accuracy</td><td>0.95</td></tr>
  </table>
  <table class="ltx_equation ltx_eqn_table">
    <tr><td>x = y + z</td></tr>
  </table>
</main>
</body>
</html>
"""


async def test_extract_js_arxiv_converts_data_table_but_skips_equation_table(tmp_path):
    result = await _evaluate_extraction("arxiv", _ARXIV_FIXTURE_HTML, tmp_path)
    assert result["title"] == "Test Paper Title"
    table_blocks = [b for b in result["blocks"] if b["tag"] == "table"]
    assert len(table_blocks) == 1
    assert "Accuracy" in table_blocks[0]["content"]
    assert "0.95" in table_blocks[0]["content"]
    assert "x = y + z" not in "".join(b["content"] for b in result["blocks"])


async def _set_default_chrome_profile(session, profile_dir: Path):
    result = await session.call_tool(
        "set_default_chrome_profile", {"profile_path": str(profile_dir)}
    )
    assert result.is_error is not True


async def test_fetch_article_x_dot_com_falls_back_to_persisted_default(tmp_path):
    """No chrome_profile passed, but a default is configured — fetch_article
    must get PAST the 'chrome_profile is required' check and reach the
    auth-cookie check instead (which then fails for this empty profile,
    proving resolution happened rather than an early required-param error)."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
            )
    assert result.is_error is True
    assert "No x.com session cookies" in result.content[0].text
    assert "is required" not in result.content[0].text


async def test_fetch_article_explicit_chrome_profile_wins_over_configured_default(tmp_path):
    """An explicitly-passed chrome_profile must be used as-is, never
    overridden by a configured default."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    explicit_profile = tmp_path / "ExplicitProfile"
    explicit_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            result, _ = await _call_fetch_article(
                session,
                url="https://x.com/someuser/status/123",
                output_dir=str(output_dir),
                chrome_profile=str(explicit_profile),
            )
    assert result.is_error is True
    assert f"No x.com session cookies in {explicit_profile}" in result.content[0].text


async def test_fetch_article_thin_retry_uses_persisted_default_when_omitted(tmp_path):
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
            )
    assert payload["thin_retry_used"] is True
    assert payload["cookies_injected"] == 0


async def test_fetch_article_non_thin_result_ignores_configured_default(tmp_path):
    """A configured default must NOT force cookie use on content that
    isn't thin — the per-site opportunistic-retry policy is unchanged."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            await _set_default_chrome_profile(session, default_profile)

            _, payload = await _call_fetch_article(
                session,
                url="https://en.wikipedia.org/wiki/Model_Context_Protocol",
                output_dir=str(output_dir),
            )
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0


async def test_fetch_article_default_output_format_writes_origin_path(tmp_path):
    """output_format defaults to 'path' — fetch_article must assemble and
    write Origin/article.md itself and return a slim metadata dict with
    no blocks/image_blocks keys."""
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_article(
                session,
                url="https://example.com",
                output_dir=str(output_dir),
            )
    assert "blocks" not in payload
    assert "image_blocks" not in payload
    origin_path = Path(payload["origin_path"])
    assert origin_path.exists()
    assert origin_path.name == "article.md"
    assert origin_path.parent.name == "Origin"
    content = origin_path.read_text(encoding="utf-8")
    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "# Example Domain" in content


async def test_fetch_article_invalid_output_format_raises(tmp_path):
    """Uses an unroutable domain to prove output_format validation happens
    BEFORE any network activity — if the check ran after dispatch/network,
    this would hang or raise a network error instead of a clean validation
    error. Note: since output_format is now typed as Literal["path", "json"],
    the MCP schema layer rejects "bogus" before fetch_article's body (and
    its internal ValueError check) ever runs, so the error text below comes
    from pydantic's schema validation rather than our ValueError message —
    an even earlier fail-fast point than the in-function check."""
    output_dir = tmp_path / "out"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_article(
                session,
                url="https://this-domain-does-not-exist-invalid-format-test.invalid",
                output_dir=str(output_dir),
                output_format="bogus",
            )
    assert result.is_error is True
    assert "output_format" in result.content[0].text
    assert "'path' or 'json'" in result.content[0].text

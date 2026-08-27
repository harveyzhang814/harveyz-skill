from pathlib import Path

from playwright.async_api import async_playwright

from browser_fetch.extractors import EXTRACT_JS, wechat_publish_date_from_ct


def _set_default_chrome_profile(run_cli, profile_dir: Path):
    proc, _ = run_cli("profile", "set", str(profile_dir))
    assert proc.returncode == 0, proc.stderr


def test_fetch_article_generic_real_network(run_cli, tmp_path):
    output_dir = tmp_path / "out"
    proc, payload = run_cli(
        "article", "https://en.wikipedia.org/wiki/Model_Context_Protocol",
        "--out", str(output_dir), "--format", "json",
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["site"] == "generic"
    assert len(payload["blocks"]) > 5
    assert "Model Context Protocol" in payload["title"]
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0
    assert payload["block_count"] > 5
    assert payload["char_count"] > 0
    assert payload["content_thin"] is False
    assert isinstance(payload["code_block_count"], int)
    assert payload["image_count"] > 0


def test_fetch_article_arxiv_real_network(run_cli, tmp_path):
    """Real arXiv HTML paper page. If this specific ID has been withdrawn
    or lacks an HTML render by the time this runs, swap in any current
    arxiv.org/html/<id> URL — check https://arxiv.org/list/cs.AI/recent."""
    output_dir = tmp_path / "out"
    proc, payload = run_cli(
        "article", "https://arxiv.org/html/2608.06020",
        "--out", str(output_dir), "--format", "json",
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["site"] == "arxiv"
    assert len(payload["blocks"]) > 5


def test_fetch_article_x_dot_com_without_chrome_profile_is_rejected(run_cli, tmp_path):
    output_dir = tmp_path / "out"
    proc, _ = run_cli(
        "article", "https://x.com/someuser/status/123", "--out", str(output_dir),
    )
    assert proc.returncode == 2


def test_fetch_article_rejects_file_scheme(run_cli, tmp_path):
    output_dir = tmp_path / "out"
    proc, _ = run_cli("article", "file:///etc/passwd", "--out", str(output_dir))
    assert proc.returncode == 2


def test_fetch_article_thin_retry_triggers_with_chrome_profile_no_matching_cookies(run_cli, tmp_path):
    """example.com is naturally thin (well under 20 blocks / 3000 chars).
    With an empty (non-real) chrome_profile dir, the retry attempt runs
    but finds no cookies, so cookies_injected stays 0 — this only checks
    that the retry path executes and doesn't crash, not that it recovers
    real content (that needs a real logged-in Chrome profile, out of
    scope for an automated test)."""
    empty_profile = tmp_path / "EmptyProfile"
    output_dir = tmp_path / "out"
    proc, payload = run_cli(
        "article", "https://example.com", "--out", str(output_dir),
        "--chrome-profile", str(empty_profile),
    )
    assert proc.returncode == 0, proc.stderr
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


_GENERIC_HIDDEN_SECTION_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<head><title>Generic Hidden Section Test</title></head>
<body>
  <main id="main">
    <section style="translate: none; opacity: 0; visibility: hidden;">
      <h1>Generic Hidden Section Test</h1>
      <p>First paragraph with sufficient content to be captured despite the ancestor section staying hidden.</p>
      <p>Second paragraph providing additional body text for the content extraction verification test here.</p>
    </section>
  </main>
</body>
</html>
"""


async def test_extract_js_generic_reads_content_under_visibility_hidden_ancestor(tmp_path):
    """Some sites (e.g. Webflow pages using GSAP/ScrollTrigger reveal
    animations) leave their whole article under a section with inline
    visibility:hidden because the reveal animation never runs headless.
    innerText returns "" for anything under a visibility:hidden ancestor
    in Chromium, so _EXTRACT_JS_GENERIC must fall back to textContent —
    same root cause as the WECHAT #js_content case above."""
    result = await _evaluate_extraction(
        "generic", _GENERIC_HIDDEN_SECTION_FIXTURE_HTML, tmp_path
    )
    assert result["title"] == "Generic Hidden Section Test"
    assert len(result["blocks"]) == 3  # h1 + 2 paragraphs
    assert "First paragraph" in result["blocks"][1]["content"]
    assert "Second paragraph" in result["blocks"][2]["content"]


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


def test_fetch_article_x_dot_com_falls_back_to_persisted_default(run_cli, tmp_path):
    """No chrome_profile passed, but a default is configured — fetch_article
    must get PAST the 'chrome_profile is required' check and reach the
    auth-cookie check instead (which then fails for this empty profile,
    proving resolution happened rather than an early required-param error)."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    _set_default_chrome_profile(run_cli, default_profile)

    proc, _ = run_cli(
        "article", "https://x.com/someuser/status/123", "--out", str(output_dir),
    )
    assert proc.returncode == 2
    assert "No x.com session cookies" in proc.stderr
    assert "is required" not in proc.stderr


def test_fetch_article_explicit_chrome_profile_wins_over_configured_default(run_cli, tmp_path):
    """An explicitly-passed chrome_profile must be used as-is, never
    overridden by a configured default."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    explicit_profile = tmp_path / "ExplicitProfile"
    explicit_profile.mkdir()
    output_dir = tmp_path / "out"
    _set_default_chrome_profile(run_cli, default_profile)

    proc, _ = run_cli(
        "article", "https://x.com/someuser/status/123", "--out", str(output_dir),
        "--chrome-profile", str(explicit_profile),
    )
    assert proc.returncode == 2
    assert f"No x.com session cookies in {explicit_profile}" in proc.stderr


def test_fetch_article_thin_retry_uses_persisted_default_when_omitted(run_cli, tmp_path):
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    _set_default_chrome_profile(run_cli, default_profile)

    proc, payload = run_cli(
        "article", "https://example.com", "--out", str(output_dir),
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["thin_retry_used"] is True
    assert payload["cookies_injected"] == 0


def test_fetch_article_non_thin_result_ignores_configured_default(run_cli, tmp_path):
    """A configured default must NOT force cookie use on content that
    isn't thin — the per-site opportunistic-retry policy is unchanged."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    output_dir = tmp_path / "out"
    _set_default_chrome_profile(run_cli, default_profile)

    proc, payload = run_cli(
        "article", "https://en.wikipedia.org/wiki/Model_Context_Protocol",
        "--out", str(output_dir),
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["thin_retry_used"] is False
    assert payload["cookies_injected"] == 0


def test_fetch_article_default_output_format_writes_origin_path(run_cli, tmp_path):
    """output_format defaults to 'path' — fetch_article must assemble and
    write Origin/<title>.md itself and return a slim metadata dict with
    no blocks/image_blocks keys."""
    output_dir = tmp_path / "out"
    proc, payload = run_cli("article", "https://example.com", "--out", str(output_dir))
    assert proc.returncode == 0, proc.stderr
    assert "blocks" not in payload
    assert "image_blocks" not in payload
    origin_path = Path(payload["origin_path"])
    assert origin_path.exists()
    assert origin_path.name == "Example Domain.md"
    assert origin_path.parent.name == "Origin"
    content = origin_path.read_text(encoding="utf-8")
    assert "source_url: https://example.com" in content
    assert 'origin_title: "Example Domain"' in content
    assert "# Example Domain" in content


def test_fetch_article_invalid_output_format_raises(run_cli, tmp_path):
    """Uses an unroutable domain to prove output_format validation happens
    BEFORE any network activity — if the check ran after dispatch/network,
    this would hang or raise a network error instead of a clean validation
    error.

    Gap vs. the old MCP test: the original asserted the exact ValueError
    message from fetch_article's own `output_format not in ("path", "json")`
    check, reached because MCP's pydantic schema layer still let "bogus"
    through as a plain string. The CLI's `--format` flag is declared with
    `choices=("path", "json")` (Task 4), so argparse itself rejects "bogus"
    before core.fetch_article ever runs — one layer earlier than the old
    schema-validation short-circuit this test's docstring already called
    out. Both layers agree on the *behavior* (reject before network, exit
    non-zero, mention path/json), so the assertions below check that
    equivalent behavior via argparse's own message instead of the old
    literal text ("output_format" / "'path' or 'json'"), since that literal
    text is no longer what actually gets emitted."""
    output_dir = tmp_path / "out"
    proc, _ = run_cli(
        "article", "https://this-domain-does-not-exist-invalid-format-test.invalid",
        "--out", str(output_dir), "--format", "bogus",
    )
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "invalid choice" in proc.stderr
    assert "'path'" in proc.stderr
    assert "'json'" in proc.stderr


def test_fetch_article_generic_thin_content_reports_content_thin_true(run_cli, tmp_path):
    """example.com's body is a single short paragraph — well under is_thin's
    20-block/3000-char thresholds, so this deterministically exercises the
    content_thin=True path without needing auth or a flaky real-world page."""
    output_dir = tmp_path / "out"
    proc, payload = run_cli(
        "article", "https://example.com", "--out", str(output_dir), "--format", "json",
    )
    assert proc.returncode == 0, proc.stderr
    assert payload["content_thin"] is True
    assert payload["block_count"] < 20
    assert payload["char_count"] < 3000

from playwright.async_api import async_playwright

from browser_fetch_mcp.extractors import EXTRACT_JS_XCOM_TIMELINE

_TIMELINE_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/1001"><time datetime="2026-08-14T10:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">First tweet text from Alice with enough length to be real content.</div>
</article>
<article data-testid="tweet">
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/1002"><time datetime="2026-08-14T11:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">Second tweet text from Alice, also long enough to be real content.</div>
</article>
<article data-testid="tweet">
  <div data-testid="Ad Account"></div>
  <div data-testid="tweetText">Promoted: buy our product now! (no permalink, must be skipped)</div>
</article>
</body>
</html>
"""


async def _evaluate_timeline_js(html: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        result = await page.evaluate(EXTRACT_JS_XCOM_TIMELINE)
        await browser.close()
    return result


async def test_extract_js_xcom_timeline_collects_cards_and_skips_promoted():
    result = await _evaluate_timeline_js(_TIMELINE_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 2

    assert tweets[0]["tweetId"] == "1001"
    assert tweets[0]["url"] == "https://x.com/alice/status/1001"
    assert tweets[0]["timestamp"] == "2026-08-14T10:00:00.000Z"
    assert tweets[0]["authorHandle"] == "@alice"
    assert "First tweet text from Alice" in tweets[0]["text"]

    assert tweets[1]["tweetId"] == "1002"
    assert "Second tweet text from Alice" in tweets[1]["text"]

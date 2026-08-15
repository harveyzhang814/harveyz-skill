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

    for t in tweets:
        assert t["type"] == "post"
        assert t["replyToHandle"] is None
        assert t["quotedAuthor"] is None
        assert t["quotedText"] is None
        assert t["quotedTimestamp"] is None


_REPOST_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="socialContext">Bob Example reposted</div>
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/2001"><time datetime="2026-08-14T12:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">Original tweet text from Alice that got reposted by Bob.</div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_classifies_repost():
    result = await _evaluate_timeline_js(_REPOST_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    t = tweets[0]
    assert t["type"] == "repost"
    assert t["authorHandle"] == "@alice"
    assert "Original tweet text from Alice" in t["text"]
    assert t["replyToHandle"] is None
    assert t["quotedAuthor"] is None


_QUOTE_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/3001"><time datetime="2026-08-14T13:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">Alice's own commentary quoting Carol's tweet below.</div>
  <div role="link" tabindex="0">
    <div data-testid="User-Name"><div>Carol Example</div><div>@carol</div></div>
    <time datetime="2026-08-13T09:00:00.000Z">Aug 13</time>
    <div data-testid="tweetText">Carol's original tweet text being quoted.</div>
  </div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_classifies_quote_and_extracts_quoted_content():
    result = await _evaluate_timeline_js(_QUOTE_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    t = tweets[0]
    assert t["type"] == "quote"
    assert t["authorHandle"] == "@alice"
    assert "Alice's own commentary" in t["text"]
    assert t["url"] == "https://x.com/alice/status/3001"
    assert t["quotedAuthor"] == "@carol"
    assert "Carol's original tweet text" in t["quotedText"]
    assert t["quotedTimestamp"] == "2026-08-13T09:00:00.000Z"
    assert t["replyToHandle"] is None


_REPLY_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div>Replying to @dave</div>
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/4001"><time datetime="2026-08-14T14:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">Alice's reply text to Dave.</div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_classifies_reply():
    result = await _evaluate_timeline_js(_REPLY_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    t = tweets[0]
    assert t["type"] == "reply"
    assert t["replyToHandle"] == "@dave"
    assert t["authorHandle"] == "@alice"
    assert "Alice's reply text" in t["text"]
    assert t["quotedAuthor"] is None


_REPOST_OF_REPLY_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="socialContext">Bob Example reposted</div>
  <div>Replying to @dave</div>
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/5001"><time datetime="2026-08-14T15:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText">A reply that also got reposted.</div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_repost_takes_priority_over_reply():
    """A repost of a reply should classify as 'repost' (the reason it's
    showing up on this timeline), not 'reply'."""
    result = await _evaluate_timeline_js(_REPOST_OF_REPLY_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    assert tweets[0]["type"] == "repost"

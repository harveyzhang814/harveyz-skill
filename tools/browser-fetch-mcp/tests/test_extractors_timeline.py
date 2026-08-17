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


_MULTILINE_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/6001"><time datetime="2026-08-14T16:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText" style="white-space: pre-wrap">First   line of the tweet.

Second paragraph after a blank line.</div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_preserves_line_breaks_in_text():
    """A multi-paragraph tweet must keep its line breaks. X embeds a real
    tweet's paragraph breaks as literal \\n characters inside the tweetText
    element's own text node (rendered via white-space: pre-wrap) — verified
    against a real tweet (trq212/2086931647468097932). Collapsing all
    whitespace (including \\n) to a single space, or reading via innerText
    (which also swallows a plain text node's \\n unless the ancestor
    survives layout), loses that paragraph structure."""
    result = await _evaluate_timeline_js(_MULTILINE_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    text = tweets[0]["text"]
    assert "\n" in text
    assert text == "First line of the tweet.\n\nSecond paragraph after a blank line."


_MENTION_DIV_FIXTURE_HTML = """\
<!DOCTYPE html>
<html>
<body>
<article data-testid="tweet">
  <div data-testid="User-Name"><div>Alice Example</div><div>@alice</div></div>
  <a href="/alice/status/7001"><time datetime="2026-08-14T17:00:00.000Z">Aug 14</time></a>
  <div data-testid="tweetText"><span>credit to </span><div class="css-g5y9jx r-xoduu5"><span><a href="/bob" role="link">@bob</a></span></div><span> for the idea, it works great</span></div>
</article>
</body>
</html>
"""


async def test_extract_js_xcom_timeline_does_not_break_line_around_mention_div():
    """X wraps each @mention in its own <div> for unrelated layout reasons.
    innerText synthesizes a line break around every block-level child
    (including that div), which would wrongly split an otherwise single-line
    tweet around each mention (see the trq212 'django (@simonw), flask
    (@mitsuhiko)...' repro) — textContent must be used instead, since it's a
    plain concatenation with no synthesized breaks."""
    result = await _evaluate_timeline_js(_MENTION_DIV_FIXTURE_HTML)
    tweets = result["tweets"]
    assert len(tweets) == 1
    assert tweets[0]["text"] == "credit to @bob for the idea, it works great"


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

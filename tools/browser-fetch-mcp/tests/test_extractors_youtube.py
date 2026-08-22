import json

import pytest
from playwright.async_api import async_playwright

from browser_fetch_mcp.extractors import (
    EXTRACT_JS_YOUTUBE_CHANNEL,
    build_channel_video_list,
    is_youtube_channel_url,
    normalize_youtube_channel_url,
    parse_youtube_rss,
    youtube_feed_url,
)


# ---------------------------------------------------------------- URL routing


def test_is_youtube_channel_url_accepts_handle_and_channel_forms():
    assert is_youtube_channel_url("https://www.youtube.com/@mattpocockuk")
    assert is_youtube_channel_url("https://www.youtube.com/@mattpocockuk/videos")
    assert is_youtube_channel_url("https://youtube.com/channel/UCswG6FSbgZjbWtdf_hMLaow")
    assert is_youtube_channel_url("https://m.youtube.com/c/SomeChannel")
    assert is_youtube_channel_url("https://www.youtube.com/user/SomeChannel")


def test_is_youtube_channel_url_rejects_non_channel_urls():
    assert not is_youtube_channel_url("https://www.youtube.com/watch?v=abc123")
    assert not is_youtube_channel_url("https://www.youtube.com/")
    assert not is_youtube_channel_url("https://x.com/mattpocockuk")
    assert not is_youtube_channel_url("https://notyoutube.com/@someone")
    assert not is_youtube_channel_url("ftp://www.youtube.com/@someone")


def test_normalize_youtube_channel_url_appends_videos_tab():
    assert (
        normalize_youtube_channel_url("https://www.youtube.com/@mattpocockuk")
        == "https://www.youtube.com/@mattpocockuk/videos"
    )
    assert (
        normalize_youtube_channel_url("https://www.youtube.com/@mattpocockuk/")
        == "https://www.youtube.com/@mattpocockuk/videos"
    )


def test_normalize_youtube_channel_url_replaces_other_tabs_and_drops_query():
    assert (
        normalize_youtube_channel_url("https://www.youtube.com/@mattpocockuk/videos")
        == "https://www.youtube.com/@mattpocockuk/videos"
    )
    assert (
        normalize_youtube_channel_url("https://www.youtube.com/@mattpocockuk/featured")
        == "https://www.youtube.com/@mattpocockuk/videos"
    )
    assert (
        normalize_youtube_channel_url("https://www.youtube.com/@mattpocockuk/streams?view=0")
        == "https://www.youtube.com/@mattpocockuk/videos"
    )


def test_normalize_youtube_channel_url_rejects_non_channel_url():
    with pytest.raises(ValueError):
        normalize_youtube_channel_url("https://www.youtube.com/watch?v=abc123")


# ------------------------------------------------------------------ RSS dates

_RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
      xmlns:media="http://search.yahoo.com/mrss/"
      xmlns="http://www.w3.org/2005/Atom">
  <yt:channelId>UCswG6FSbgZjbWtdf_hMLaow</yt:channelId>
  <title>Matt Pocock</title>
  <entry>
    <yt:videoId>gaDdrDdczO4</yt:videoId>
    <title>New Skills! v1.2</title>
    <published>2026-08-06T15:00:11+00:00</published>
  </entry>
  <entry>
    <yt:videoId>F3lL98Pj90o</yt:videoId>
    <title>/wayfinder</title>
    <published>2026-07-30T14:12:00+00:00</published>
  </entry>
</feed>
"""


def test_parse_youtube_rss_maps_video_id_to_published():
    assert parse_youtube_rss(_RSS_XML) == {
        "gaDdrDdczO4": "2026-08-06T15:00:11+00:00",
        "F3lL98Pj90o": "2026-07-30T14:12:00+00:00",
    }


def test_parse_youtube_rss_returns_empty_on_garbage():
    assert parse_youtube_rss("") == {}
    assert parse_youtube_rss("<html>404 not found</html>") == {}


def test_youtube_feed_url_from_channel_id():
    assert (
        youtube_feed_url("UCswG6FSbgZjbWtdf_hMLaow")
        == "https://www.youtube.com/feeds/videos.xml?channel_id=UCswG6FSbgZjbWtdf_hMLaow"
    )
    assert youtube_feed_url("") is None


def test_parse_youtube_rss_skips_entries_missing_fields():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <entry><yt:videoId>onlyid</yt:videoId></entry>
  <entry><published>2026-01-01T00:00:00+00:00</published></entry>
  <entry><yt:videoId>good</yt:videoId><published>2026-01-02T00:00:00+00:00</published></entry>
</feed>
"""
    assert parse_youtube_rss(xml) == {"good": "2026-01-02T00:00:00+00:00"}


# ------------------------------------------------------- in-page JS extractor


def _lockup(video_id, title, meta_parts, content_type="LOCKUP_CONTENT_TYPE_VIDEO"):
    return {
        "lockupViewModel": {
            "contentId": video_id,
            "contentType": content_type,
            "metadata": {
                "lockupMetadataViewModel": {
                    "title": {"content": title},
                    "metadata": {
                        "contentMetadataViewModel": {
                            "metadataRows": [
                                {"metadataParts": [{"text": {"content": p}} for p in meta_parts]}
                            ]
                        }
                    },
                }
            },
        }
    }


def _fixture_html(initial_data: dict) -> str:
    return (
        "<!DOCTYPE html><html><head><script>var ytInitialData = "
        + json.dumps(initial_data)
        + ";</script></head><body></body></html>"
    )


_CHANNEL_DATA = {
    "metadata": {
        "channelMetadataRenderer": {
            "externalId": "UCswG6FSbgZjbWtdf_hMLaow",
            "title": "Matt Pocock",
        }
    },
    "contents": {
        "twoColumnBrowseResultsRenderer": {
            "tabs": [
                {
                    "tabRenderer": {
                        "title": "Videos",
                        "selected": True,
                        "content": {
                            "richGridRenderer": {
                                "contents": [
                                    {"richItemRenderer": {"content": _lockup(
                                        "gaDdrDdczO4", "New Skills! v1.2", ["129K views", "2 weeks ago"])}},
                                    {"richItemRenderer": {"content": _lockup(
                                        "F3lL98Pj90o", "/wayfinder", ["292K views", "3 weeks ago"])}},
                                    {"richItemRenderer": {"content": _lockup(
                                        "shortsid01", "A Short", ["1M views", "1 day ago"],
                                        content_type="LOCKUP_CONTENT_TYPE_SHORTS")}},
                                    {"continuationItemRenderer": {}},
                                ]
                            }
                        },
                    }
                }
            ]
        }
    },
}


async def _evaluate(html: str) -> dict:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="domcontentloaded")
        result = await page.evaluate(EXTRACT_JS_YOUTUBE_CHANNEL)
        await browser.close()
    return result


async def test_extract_js_youtube_channel_collects_videos_in_page_order():
    result = await _evaluate(_fixture_html(_CHANNEL_DATA))

    assert result["channelId"] == "UCswG6FSbgZjbWtdf_hMLaow"
    assert result["channelTitle"] == "Matt Pocock"

    videos = result["videos"]
    assert [v["videoId"] for v in videos] == ["gaDdrDdczO4", "F3lL98Pj90o"]
    assert videos[0]["url"] == "https://www.youtube.com/watch?v=gaDdrDdczO4"
    assert videos[0]["title"] == "New Skills! v1.2"
    assert videos[0]["publishedText"] == "2 weeks ago"
    assert videos[1]["publishedText"] == "3 weeks ago"


async def test_extract_js_youtube_channel_deduplicates_repeated_lockups():
    data = json.loads(json.dumps(_CHANNEL_DATA))
    grid = data["contents"]["twoColumnBrowseResultsRenderer"]["tabs"][0]["tabRenderer"]["content"][
        "richGridRenderer"
    ]["contents"]
    grid.append({"richItemRenderer": {"content": _lockup(
        "gaDdrDdczO4", "New Skills! v1.2", ["129K views", "2 weeks ago"])}})

    result = await _evaluate(_fixture_html(data))
    assert [v["videoId"] for v in result["videos"]] == ["gaDdrDdczO4", "F3lL98Pj90o"]


async def test_extract_js_youtube_channel_falls_back_to_last_metadata_part():
    """publishedText is located by the "ago" marker; when the locale renders
    something else, the last metadata part is still the date-ish one."""
    data = {
        "contents": {"richGridRenderer": {"contents": [
            {"richItemRenderer": {"content": _lockup("vid1", "Titre", ["129 k vues", "il y a 2 semaines"])}}
        ]}}
    }
    result = await _evaluate(_fixture_html(data))
    assert result["videos"][0]["publishedText"] == "il y a 2 semaines"


async def test_extract_js_youtube_channel_skips_entries_without_title():
    data = {
        "contents": {"richGridRenderer": {"contents": [
            {"richItemRenderer": {"content": {"lockupViewModel": {
                "contentId": "vid1", "contentType": "LOCKUP_CONTENT_TYPE_VIDEO"}}}},
            {"richItemRenderer": {"content": _lockup("vid2", "Real Title", ["1 view", "1 day ago"])}},
        ]}}
    }
    result = await _evaluate(_fixture_html(data))
    assert [v["videoId"] for v in result["videos"]] == ["vid2"]


async def test_extract_js_youtube_channel_reports_missing_initial_data():
    result = await _evaluate("<!DOCTYPE html><html><body>consent wall</body></html>")
    assert result["error"]
    assert result.get("videos") in (None, [])


# ------------------------------------------------------------ result assembly

_RAW_VIDEOS = [
    {"videoId": "gaDdrDdczO4", "url": "https://www.youtube.com/watch?v=gaDdrDdczO4",
     "title": "New Skills! v1.2", "publishedText": "2 weeks ago"},
    {"videoId": "F3lL98Pj90o", "url": "https://www.youtube.com/watch?v=F3lL98Pj90o",
     "title": "/wayfinder", "publishedText": "3 weeks ago"},
]


def test_build_channel_video_list_attaches_exact_dates_from_feed():
    videos = build_channel_video_list(_RAW_VIDEOS, parse_youtube_rss(_RSS_XML), max_videos=30)
    assert videos == [
        {
            "video_id": "gaDdrDdczO4",
            "url": "https://www.youtube.com/watch?v=gaDdrDdczO4",
            "title": "New Skills! v1.2",
            "published_text": "2 weeks ago",
            "published_at": "2026-08-06T15:00:11+00:00",
        },
        {
            "video_id": "F3lL98Pj90o",
            "url": "https://www.youtube.com/watch?v=F3lL98Pj90o",
            "title": "/wayfinder",
            "published_text": "3 weeks ago",
            "published_at": "2026-07-30T14:12:00+00:00",
        },
    ]


def test_build_channel_video_list_leaves_published_at_none_when_feed_misses_video():
    videos = build_channel_video_list(_RAW_VIDEOS, {}, max_videos=30)
    assert [v["published_at"] for v in videos] == [None, None]
    assert [v["published_text"] for v in videos] == ["2 weeks ago", "3 weeks ago"]


def test_build_channel_video_list_truncates_to_max_videos():
    videos = build_channel_video_list(_RAW_VIDEOS, {}, max_videos=1)
    assert [v["video_id"] for v in videos] == ["gaDdrDdczO4"]

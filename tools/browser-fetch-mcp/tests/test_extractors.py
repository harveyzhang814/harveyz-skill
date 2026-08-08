import pytest

from browser_fetch_mcp.extractors import (
    EXTRACT_JS,
    dispatch_site,
    extract_wechat_publish_date,
    is_thin,
)


@pytest.mark.parametrize(
    "url,expected_site",
    [
        ("https://example.com/some-article", "generic"),
        ("https://blog.example.com/post/1", "generic"),
        ("https://mp.weixin.qq.com/s/abc123", "wechat"),
        ("https://arxiv.org/html/2312.11805", "arxiv"),
        ("https://arxiv.org/abs/2312.11805", "generic"),  # no /html/ in path
    ],
)
def test_dispatch_site_routes_by_hostname(url, expected_site):
    assert dispatch_site(url) == expected_site


@pytest.mark.parametrize(
    "url",
    [
        "https://x.com/someuser/status/123",
        "https://www.x.com/someuser/status/123",
        "https://twitter.com/someuser/status/123",
        "https://www.twitter.com/someuser/status/123",
    ],
)
def test_dispatch_site_routes_x_dot_com_to_xcom(url):
    assert dispatch_site(url) == "xcom"


def test_dispatch_site_rejects_only_exact_hostname_not_substring():
    """A lookalike hostname must not be misrouted to wechat's extractor —
    exact match only, no substring matching."""
    assert dispatch_site("https://notmp.weixin.qq.com.evil.com/s/abc") == "generic"


def test_is_thin_true_below_block_count_threshold():
    result = {"blocks": [{"tag": "p", "content": "x" * 500} for _ in range(19)]}
    assert is_thin(result) is True


def test_is_thin_false_at_block_count_threshold_with_enough_chars():
    result = {"blocks": [{"tag": "p", "content": "x" * 200} for _ in range(20)]}
    assert is_thin(result) is False


def test_is_thin_true_below_char_threshold_even_with_many_blocks():
    result = {"blocks": [{"tag": "p", "content": "x"} for _ in range(25)]}
    assert is_thin(result) is True


def test_extract_wechat_publish_date_parses_ct_variable():
    html = '<html><head><script>var ct = "1719763200";</script></head></html>'
    # 1719763200 -> 2024-07-01 in UTC+8
    assert extract_wechat_publish_date(html) == "2024-07-01"


def test_extract_wechat_publish_date_missing_returns_empty():
    assert extract_wechat_publish_date("<html></html>") == ""


def test_extract_js_dict_has_all_three_sites():
    assert set(EXTRACT_JS.keys()) == {"generic", "wechat", "arxiv"}
    for js in EXTRACT_JS.values():
        assert isinstance(js, str) and js.strip().startswith("()")

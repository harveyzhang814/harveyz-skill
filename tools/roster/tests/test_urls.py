import pytest

from roster import urls


@pytest.mark.parametrize("url,expected", [
    ("https://youtube.com/@AndrejKarpathy", ("youtube", "AndrejKarpathy")),
    ("https://www.youtube.com/@AndrejKarpathy/videos", ("youtube", "AndrejKarpathy")),
    ("https://m.youtube.com/channel/UCabc123", ("youtube", "UCabc123")),
    ("https://youtube.com/c/somename", ("youtube", "somename")),
    ("https://youtube.com/user/olduser", ("youtube", "olduser")),
    ("https://x.com/karpathy", ("x", "karpathy")),
    ("https://x.com/@karpathy", ("x", "karpathy")),
    ("https://twitter.com/karpathy", ("x", "karpathy")),
    ("https://x.com/karpathy/", ("x", "karpathy")),
])
def test_parse_channel_url(url, expected):
    assert urls.parse_channel_url(url) == expected


@pytest.mark.parametrize("url", [
    "https://youtube.com/watch?v=abc123",
    "https://example.com/karpathy",
    "not a url",
    "https://x.com/",
])
def test_parse_channel_url_rejects(url):
    with pytest.raises(ValueError):
        urls.parse_channel_url(url)


@pytest.mark.parametrize("text,expected", [
    ("AndrejKarpathy", "andrejkarpathy"),
    ("Andrej Karpathy", "andrej-karpathy"),
    ("Two Minute Papers!", "two-minute-papers"),
    ("__weird__name__", "weird-name"),
])
def test_slugify(text, expected):
    assert urls.slugify(text) == expected


def test_channel_key():
    assert urls.channel_key("x", "karpathy") == "x:karpathy"

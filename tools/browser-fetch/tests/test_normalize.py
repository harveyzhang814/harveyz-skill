"""normalize_articles 的单元测试 —— 纯函数，不碰浏览器不碰磁盘。
这层是 spec §7.3 的"结构上绕不过去"：三档 JS 返回什么都要过它。"""
from browser_fetch.normalize import normalize_articles

LIST_URL = "https://example.com/blog"


def test_absolute_url_passes_through_unchanged():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": "d"}]
    assert normalize_articles(items, LIST_URL)[0]["url"] == "https://example.com/a"


def test_relative_url_is_resolved_against_list_url():
    items = [{"title": "T", "url": "/posts/1", "date_text": ""}]
    assert normalize_articles(items, LIST_URL)[0]["url"] == "https://example.com/posts/1"


def test_whitespace_in_title_and_date_is_collapsed():
    items = [{"title": "  a\n\t b  ", "url": "https://example.com/a", "date_text": " x \n y "}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out["title"] == "a b"
    assert out["date_text"] == "x y"


def test_items_without_a_url_are_dropped():
    items = [
        {"title": "keep", "url": "https://example.com/a", "date_text": ""},
        {"title": "drop", "url": "", "date_text": ""},
        {"title": "drop too", "url": "   ", "date_text": ""},
    ]
    out = normalize_articles(items, LIST_URL)
    assert [a["title"] for a in out] == ["keep"]


def test_missing_keys_become_empty_strings():
    items = [{"url": "https://example.com/a"}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out == {"title": "", "url": "https://example.com/a", "date_text": ""}


def test_non_dict_entries_are_dropped():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": ""}, "junk", None, 42]
    assert len(normalize_articles(items, LIST_URL)) == 1


def test_non_string_field_values_become_empty_strings():
    items = [{"title": 123, "url": "https://example.com/a", "date_text": {"x": 1}}]
    out = normalize_articles(items, LIST_URL)[0]
    assert out["title"] == ""
    assert out["date_text"] == ""


def test_output_has_exactly_the_three_contract_keys():
    items = [{"title": "T", "url": "https://example.com/a", "date_text": "d", "extra": "gone"}]
    assert set(normalize_articles(items, LIST_URL)[0]) == {"title", "url", "date_text"}

"""build_articles_js is a pure string-builder — no playwright involved
here. The behavioral test (does the JS actually extract the right things
from a real page) lives in test_cli_articles.py, which runs it through a
local HTTP fixture server."""
import json

from browser_fetch.extractors import build_articles_js


def test_embeds_each_selector_as_a_json_string_literal():
    js = build_articles_js({"item": "div.entry", "title": "h3 a", "link": "h3 a", "date": "p.date"})
    assert f"const itemSel = {json.dumps('div.entry')};" in js
    assert f"const titleSel = {json.dumps('h3 a')};" in js
    assert f"const dateSel = {json.dumps('p.date')};" in js


def test_missing_date_selector_defaults_to_empty_string():
    js = build_articles_js({"item": "div.entry", "title": "h3 a", "link": "h3 a"})
    assert 'const dateSel = "";' in js


def test_selector_containing_a_quote_stays_a_safe_json_literal():
    """json.dumps, not raw string interpolation — a selector with a double
    quote in it (e.g. an attribute-value CSS selector) must not be able to
    break out of the JS string literal it's embedded in."""
    tricky = 'div[data-x="y"]'
    js = build_articles_js({"item": tricky, "title": "h3", "link": "a", "date": ""})
    assert f"const itemSel = {json.dumps(tricky)};" in js
    assert js.count('const itemSel = ') == 1

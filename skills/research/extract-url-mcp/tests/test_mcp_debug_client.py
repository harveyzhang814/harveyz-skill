"""Real network, real browser-fetch-mcp subprocess tests for the debug MCP
client used by extract-url-mcp's self-optimization subagent to iterate
candidate extraction logic against a real page (fetch_page for static HTML
inspection, evaluate_js for testing candidate extraction JS).

Run: python3 -m pytest skills/research/extract-url-mcp/tests/ -v
(ambient system Python — matches how mcp_fetch_client.py itself runs)
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from mcp_debug_client import call_evaluate_js, call_fetch_page  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_FETCH_MCP_DATA_DIR", str(tmp_path / "data"))


def test_call_fetch_page_returns_html():
    payload = asyncio.run(call_fetch_page("https://example.com"))
    assert payload["status"] == 200
    assert "Example Domain" in payload["html"]


def test_call_evaluate_js_returns_js_result():
    payload = asyncio.run(call_evaluate_js("https://example.com", "() => document.title"))
    assert payload["result"] == "Example Domain"


def test_call_evaluate_js_rejects_invalid_scheme():
    with pytest.raises(RuntimeError):
        asyncio.run(call_evaluate_js("ftp://example.com", "() => document.title"))

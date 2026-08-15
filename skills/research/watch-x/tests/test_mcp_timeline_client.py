"""Real browser-fetch-mcp subprocess, real MCP stdio protocol — no mocks.
Only covers the deterministic validation-error paths that don't need a
real, logged-in X session (same scope as clip-url's xcom-adjacent tests).

Run: python3 -m pytest skills/research/watch-x/tests/ -v
"""
import asyncio

import pytest

from mcp_timeline_client import fetch_timeline


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("BROWSER_FETCH_MCP_DATA_DIR", str(tmp_path / "data"))


def test_fetch_timeline_without_chrome_profile_raises():
    with pytest.raises(RuntimeError, match="chrome_profile is required"):
        asyncio.run(fetch_timeline("https://x.com/someuser"))


def test_fetch_timeline_rejects_non_xcom_url():
    with pytest.raises(RuntimeError, match="only supports x.com/twitter.com URLs"):
        asyncio.run(fetch_timeline("https://example.com/someuser", chrome_profile="/tmp/fake-profile"))

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_cli  # noqa: E402
import mcp_timeline_client  # noqa: E402


def test_fetch_timeline_builds_cli_args(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"tweets": [{"tweet_id": "1"}]}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    import asyncio
    tweets = asyncio.run(mcp_timeline_client.fetch_timeline(
        "https://x.com/someone", chrome_profile="/tmp/P", max_tweets=5))

    assert tweets == [{"tweet_id": "1"}]
    assert seen["args"] == (
        "timeline", "https://x.com/someone", "--max", "5", "--chrome-profile", "/tmp/P")


def test_fetch_timeline_omits_profile_when_absent(monkeypatch):
    seen = {}
    monkeypatch.setattr(browser_fetch_cli, "call",
                        lambda *a: (seen.update(args=a), {"tweets": []})[1])
    import asyncio
    asyncio.run(mcp_timeline_client.fetch_timeline("https://x.com/someone"))
    assert "--chrome-profile" not in seen["args"]


def test_fetch_timeline_propagates_cli_failure(monkeypatch):
    def boom(*args):
        raise RuntimeError("timeline failed: cookie 失效")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    import asyncio
    with pytest.raises(RuntimeError, match="cookie 失效"):
        asyncio.run(mcp_timeline_client.fetch_timeline("https://x.com/someone"))

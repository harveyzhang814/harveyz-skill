import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_cli  # noqa: E402
import mcp_channel_client  # noqa: E402


def test_fetch_channel_videos_builds_cli_args(monkeypatch):
    seen = {}

    def fake_call(*args):
        seen["args"] = args
        return {"videos": [{"title": "T", "url": "https://youtu.be/x"}]}

    monkeypatch.setattr(browser_fetch_cli, "call", fake_call)
    videos = asyncio.run(mcp_channel_client.fetch_channel_videos(
        "https://www.youtube.com/@x", chrome_profile="/tmp/P", max_videos=7))

    assert videos == [{"title": "T", "url": "https://youtu.be/x"}]
    assert seen["args"] == (
        "channel", "https://www.youtube.com/@x", "--max", "7", "--chrome-profile", "/tmp/P")


def test_fetch_channel_videos_omits_profile_when_absent(monkeypatch):
    seen = {}
    monkeypatch.setattr(browser_fetch_cli, "call",
                        lambda *a: (seen.update(args=a), {"videos": []})[1])
    asyncio.run(mcp_channel_client.fetch_channel_videos("https://www.youtube.com/@x"))
    assert "--chrome-profile" not in seen["args"]


def test_fetch_channel_videos_propagates_cli_failure(monkeypatch):
    def boom(*args):
        raise RuntimeError("channel failed: 频道不存在")
    monkeypatch.setattr(browser_fetch_cli, "call", boom)
    with pytest.raises(RuntimeError, match="频道不存在"):
        asyncio.run(mcp_channel_client.fetch_channel_videos("https://www.youtube.com/@x"))

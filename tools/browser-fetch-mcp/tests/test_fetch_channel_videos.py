import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_MODULE = "browser_fetch_mcp.server"


def _server_params(data_dir: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", SERVER_MODULE],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
    )


async def _call(session, **kwargs):
    result = await session.call_tool("fetch_channel_videos", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_channel_videos_is_registered(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
    assert "fetch_channel_videos" in {t.name for t in tools.tools}


async def test_fetch_channel_videos_rejects_non_youtube_url(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call(session, channel_url="https://x.com/mattpocockuk")
    assert result.is_error is True
    assert "Not a YouTube channel URL" in result.content[0].text


async def test_fetch_channel_videos_rejects_watch_url(tmp_path):
    """A single video URL is not a channel — this skill never ingests one."""
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call(
                session, channel_url="https://www.youtube.com/watch?v=gaDdrDdczO4"
            )
    assert result.is_error is True
    assert "Not a YouTube channel URL" in result.content[0].text


async def test_fetch_channel_videos_rejects_file_scheme(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call(session, channel_url="file:///etc/passwd")
    assert result.is_error is True
    assert "only http/https allowed" in result.content[0].text

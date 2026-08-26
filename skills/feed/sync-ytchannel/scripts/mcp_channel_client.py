#!/usr/bin/env python3
"""MCP client wrapper for browser-fetch-mcp's fetch_channel_videos — same
stdio_client pattern as sync-xtimeline's mcp_timeline_client.py, kept as its
own copy since each skill is self-contained (see browser_fetch_mcp_locate.py's
docstring for the dev-mode/installed-mode split this depends on).
"""
import json
import os
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from browser_fetch_mcp_locate import find_browser_fetch_mcp

BROWSER_FETCH_MCP_SH = find_browser_fetch_mcp()


def _is_error(result) -> bool:
    """mcp renamed CallToolResult.isError to is_error between 1.x and 2.x, and
    this script runs against whichever version the host python happens to
    have."""
    return bool(getattr(result, "is_error", None) or getattr(result, "isError", None))


def _payload(result) -> dict:
    structured = getattr(result, "structured_content", None) or getattr(
        result, "structuredContent", None
    )
    return structured if structured else json.loads(result.content[0].text)


async def fetch_channel_videos(
    channel_url: str, chrome_profile: Optional[str] = None, max_videos: int = 30
) -> list[dict]:
    try:
        server_params = StdioServerParameters(
            command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
        )
        tool_args = {"channel_url": channel_url, "max_videos": max_videos}
        if chrome_profile:
            tool_args["chrome_profile"] = chrome_profile

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("fetch_channel_videos", tool_args)
                if _is_error(result):
                    raise RuntimeError(f"fetch_channel_videos failed: {result.content[0].text}")
                payload = _payload(result)
        return payload["videos"]
    except BaseExceptionGroup as e:
        # Unwrap anyio's TaskGroup ExceptionGroup to expose the actual error
        leaf = e
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        if isinstance(leaf, Exception):
            raise leaf
        raise

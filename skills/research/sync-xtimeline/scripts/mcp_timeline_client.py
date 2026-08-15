#!/usr/bin/env python3
"""MCP client wrapper for browser-fetch-mcp's fetch_user_timeline — same
stdio_client pattern as clip-url's mcp_fetch_client.py, kept as its own
copy since each skill is self-contained (see browser_fetch_mcp_locate.py's
docstring for the dev-mode/installed-mode split this depends on).
"""
import os
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from browser_fetch_mcp_locate import find_browser_fetch_mcp

BROWSER_FETCH_MCP_SH = find_browser_fetch_mcp()


async def fetch_timeline(
    profile_url: str, chrome_profile: Optional[str] = None, max_tweets: int = 20
) -> list[dict]:
    try:
        server_params = StdioServerParameters(
            command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
        )
        tool_args = {"profile_url": profile_url, "max_tweets": max_tweets}
        if chrome_profile:
            tool_args["chrome_profile"] = chrome_profile

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("fetch_user_timeline", tool_args)
                if result.isError:
                    raise RuntimeError(f"fetch_user_timeline failed: {result.content[0].text}")
                if result.structuredContent:
                    payload = result.structuredContent
                else:
                    import json

                    payload = json.loads(result.content[0].text)
        return payload["tweets"]
    except BaseExceptionGroup as e:
        # Unwrap anyio's TaskGroup ExceptionGroup to expose the actual error
        leaf = e
        while isinstance(leaf, BaseExceptionGroup) and leaf.exceptions:
            leaf = leaf.exceptions[0]
        if isinstance(leaf, Exception):
            raise leaf
        raise

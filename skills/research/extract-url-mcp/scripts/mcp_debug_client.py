#!/usr/bin/env python3
"""Debug MCP client for extract-url-mcp's self-optimization subagent: thin
wrappers around browser-fetch-mcp's fetch_page and evaluate_js, used to
iterate candidate extraction logic against a real page before solidifying
a fix into browser-fetch-mcp/browser_fetch_mcp/extractors.py.

Written from scratch, sibling to mcp_fetch_client.py — does not import or
reuse extract-url's scripts. Runs under the ambient system Python (same
mcp 1.28.1 camelCase note as mcp_fetch_client.py).
"""
import json
import os
from pathlib import Path
from typing import Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)


async def _call_tool(tool_name: str, tool_args: dict) -> dict:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )
    # NOTE: the error/payload is captured inside the context managers but
    # raised *after* they exit. Raising while still inside the anyio
    # TaskGroup-backed `async with` scopes gets wrapped in a
    # BaseExceptionGroup by anyio's TaskGroup.__aexit__ (observed with
    # anyio 4.13.0 under ambient system Python 3.14), which breaks plain
    # `except RuntimeError` handling for callers like the self-optimization
    # subagent.
    error_message = None
    payload = None
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, tool_args)
            if result.isError:
                error_message = f"{tool_name} failed: {result.content[0].text}"
            elif result.structuredContent:
                payload = result.structuredContent
            else:
                payload = json.loads(result.content[0].text)
    if error_message:
        raise RuntimeError(error_message)
    return payload


async def call_fetch_page(url: str, use_auth: bool = False, chrome_profile: Optional[str] = None) -> dict:
    tool_args = {"url": url, "use_auth": use_auth}
    if chrome_profile:
        tool_args["chrome_profile"] = chrome_profile
    return await _call_tool("fetch_page", tool_args)


async def call_evaluate_js(url: str, js_code: str, chrome_profile: Optional[str] = None) -> dict:
    tool_args = {"url": url, "js_code": js_code}
    if chrome_profile:
        tool_args["chrome_profile"] = chrome_profile
    return await _call_tool("evaluate_js", tool_args)

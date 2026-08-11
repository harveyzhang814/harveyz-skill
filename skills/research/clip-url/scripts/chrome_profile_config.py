#!/usr/bin/env python3
"""Thin MCP-client CLI for reading/writing browser-fetch-mcp's persisted
default Chrome profile (get_default_chrome_profile / set_default_chrome_profile
tools). Written from scratch, same stdio_client pattern as mcp_fetch_client.py
and detect_xcom_chrome_profile.py.

Usage:
  python3 chrome_profile_config.py get
  python3 chrome_profile_config.py set <profile_path>

get prints "CONFIGURED: <path>" or "NOT_CONFIGURED".
set prints "OK" on success; on failure, prints the error to stderr and
exits 1 (e.g. profile_path doesn't exist or isn't a directory).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BROWSER_FETCH_MCP_SH = (
    Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
)


async def _get() -> str:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_default_chrome_profile", {})
            if result.isError:
                raise RuntimeError(f"get_default_chrome_profile failed: {result.content[0].text}")
            payload = result.structuredContent or json.loads(result.content[0].text)
            profile_path = payload["profile_path"]
            return f"CONFIGURED: {profile_path}" if profile_path else "NOT_CONFIGURED"


async def _set(profile_path: str) -> str:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": profile_path}
            )
            if result.isError:
                raise RuntimeError(f"set_default_chrome_profile failed: {result.content[0].text}")
            return "OK"


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("get", "set"):
        print("Usage: chrome_profile_config.py get | set <profile_path>", file=sys.stderr)
        sys.exit(1)

    if sys.argv[1] == "get":
        print(asyncio.run(_get()))
        return

    if len(sys.argv) < 3:
        print("Usage: chrome_profile_config.py set <profile_path>", file=sys.stderr)
        sys.exit(1)

    try:
        print(asyncio.run(_set(sys.argv[2])))
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

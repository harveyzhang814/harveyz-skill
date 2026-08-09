#!/usr/bin/env python3
"""
Detect which Chrome profile(s) are logged into X.com (Twitter), via
browser-fetch-mcp's list_chrome_profiles MCP tool — no direct sqlite
access here anymore; the cookie-scanning logic now lives in
tools/browser-fetch-mcp/browser_fetch_mcp/profiles.py.

Usage: python3 detect_xcom_chrome_profile.py
Prints a human-readable comparison table, then one line:
  RECOMMENDED_PROFILE: <path>
or, if no profile has any of the known auth cookies:
  RECOMMENDED_PROFILE: (none found)

This script only reports candidates — it never picks one automatically
for a caller. Detection and use MUST stay separated: whoever calls this
script must show the result to a human and get explicit confirmation
before persisting a profile via chrome_profile_config.py.

NOTE ON mcp SDK VERSION: see mcp_fetch_client.py's docstring — this
script runs under the ambient system Python (mcp 1.28.1, camelCase
isError/structuredContent), same as mcp_fetch_client.py.
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

HOST_KEYS = [".x.com", ".twitter.com"]
COOKIE_NAMES = ["auth_token", "ct0", "twid"]


async def _list_profiles() -> list[dict]:
    server_params = StdioServerParameters(
        command=str(BROWSER_FETCH_MCP_SH), args=[], env=dict(os.environ)
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "list_chrome_profiles", {"host_keys": HOST_KEYS, "cookie_names": COOKIE_NAMES}
            )
            if result.isError:
                raise RuntimeError(f"list_chrome_profiles failed: {result.content[0].text}")
            payload = result.structuredContent or json.loads(result.content[0].text)
            return payload["profiles"]


def main():
    profiles = asyncio.run(_list_profiles())

    if not profiles:
        print("No Chrome profiles found.")
        print("RECOMMENDED_PROFILE: (none found)")
        return

    print(f"{'Profile':<50} {'Account':<38} {'X.com cookies found'}")
    print("-" * 110)

    recommended = None
    for p in profiles:
        email = p["account_email"] or "(not logged into Google)"
        names = p["matched_cookie_names"]
        status = ", ".join(names) if names else "(no X.com cookies)"
        marker = " <-- looks logged in" if p["looks_logged_in"] else ""
        print(f"{p['profile_path']:<50} {email:<38} {status}{marker}")
        if p["looks_logged_in"] and recommended is None:
            recommended = p["profile_path"]

    print()
    if recommended:
        print(f"RECOMMENDED_PROFILE: {recommended}")
    else:
        print("RECOMMENDED_PROFILE: (none found)")


if __name__ == "__main__":
    main()

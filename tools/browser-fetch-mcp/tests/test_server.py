import json
import os
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_MODULE = "browser_fetch_mcp.server"


def _server_params(data_dir: Path) -> StdioServerParameters:
    return StdioServerParameters(
        command="python3",
        args=["-m", SERVER_MODULE],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
    )


async def _call_fetch_page(session, **kwargs):
    result = await session.call_tool("fetch_page", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_page_anonymous(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_page(session, url="https://example.com")
            assert payload["title"] == "Example Domain"
            assert payload["status"] == 200
            assert payload["cookies_injected"] == 0


async def test_fetch_page_warm_reuse_is_faster(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            start = time.monotonic()
            await _call_fetch_page(session, url="https://example.com")
            first_call = time.monotonic() - start

            start = time.monotonic()
            await _call_fetch_page(session, url="https://example.com")
            second_call = time.monotonic() - start

            assert second_call < first_call / 2

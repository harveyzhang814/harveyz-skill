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


async def _call_evaluate_js(session, **kwargs):
    result = await session.call_tool("evaluate_js", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_evaluate_js_returns_page_evaluate_result(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_evaluate_js(
                session, url="https://example.com", js_code="() => document.title"
            )
    assert payload["result"] == "Example Domain"


async def test_evaluate_js_rejects_invalid_scheme(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_evaluate_js(
                session, url="ftp://example.com", js_code="() => document.title"
            )
    assert result.is_error is True


async def test_evaluate_js_with_chrome_profile_no_matching_cookies(tmp_path):
    """No real auth cookies available in an automated test — just confirms
    the chrome_profile code path doesn't crash and still returns a result,
    matching test_fetch_page_use_auth_no_matching_cookies's approach."""
    empty_profile = tmp_path / "EmptyProfile"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_evaluate_js(
                session,
                url="https://example.com",
                js_code="() => document.title",
                chrome_profile=str(empty_profile),
            )
    assert payload["result"] == "Example Domain"

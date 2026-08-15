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


async def _call_fetch_user_timeline(session, **kwargs):
    result = await session.call_tool("fetch_user_timeline", kwargs)
    if result.is_error:
        return result, None
    payload = result.structured_content or json.loads(result.content[0].text)
    return result, payload


async def test_fetch_user_timeline_rejects_non_xcom_url(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_user_timeline(
                session, profile_url="https://example.com/someuser"
            )
    assert result.is_error is True
    assert "only supports x.com/twitter.com URLs" in result.content[0].text


async def test_fetch_user_timeline_rejects_file_scheme(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_user_timeline(
                session, profile_url="file:///etc/passwd"
            )
    assert result.is_error is True


async def test_fetch_user_timeline_without_chrome_profile_is_rejected(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_user_timeline(
                session, profile_url="https://x.com/someuser"
            )
    assert result.is_error is True
    assert "chrome_profile is required" in result.content[0].text


async def test_fetch_user_timeline_falls_back_to_persisted_default(tmp_path):
    """No chrome_profile passed, but a default is configured — must get PAST
    the 'chrome_profile is required' check and reach the auth-cookie check
    instead (proving resolution happened), same pattern as
    test_fetch_article_x_dot_com_falls_back_to_persisted_default."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            set_result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": str(default_profile)}
            )
            assert set_result.is_error is not True

            result, _ = await _call_fetch_user_timeline(
                session, profile_url="https://x.com/someuser"
            )
    assert result.is_error is True
    assert "No x.com session cookies" in result.content[0].text
    assert "is required" not in result.content[0].text

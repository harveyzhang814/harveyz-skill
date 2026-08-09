import json
import os
import sys
import time
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


async def _call_fetch_page(session, **kwargs):
    result = await session.call_tool("fetch_page", kwargs)
    if result.isError:
        return result, None
    payload = result.structuredContent or json.loads(result.content[0].text)
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


async def test_fetch_page_use_auth_requires_chrome_profile(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result, _ = await _call_fetch_page(session, url="https://example.com", use_auth=True)
            assert result.isError is True


async def test_fetch_page_use_auth_no_matching_cookies(tmp_path):
    empty_profile = tmp_path / "EmptyProfile"
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            _, payload = await _call_fetch_page(
                session, url="https://example.com", use_auth=True, chrome_profile=str(empty_profile)
            )
            assert payload["cookies_injected"] == 0
            assert payload["status"] == 200


async def test_get_default_chrome_profile_returns_none_initially(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_default_chrome_profile", {})
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert payload["profile_path"] is None


async def test_set_default_chrome_profile_then_get_round_trips(tmp_path):
    profile_dir = tmp_path / "SomeChromeProfile"
    profile_dir.mkdir()
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            set_result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": str(profile_dir)}
            )
            assert set_result.isError is not True

            get_result = await session.call_tool("get_default_chrome_profile", {})
            payload = get_result.structuredContent or json.loads(get_result.content[0].text)
            assert payload["profile_path"] == str(profile_dir)


async def test_set_default_chrome_profile_rejects_nonexistent_path(tmp_path):
    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "set_default_chrome_profile", {"profile_path": str(tmp_path / "DoesNotExist")}
            )
            assert result.isError is True


async def test_list_chrome_profiles_via_mcp_protocol(tmp_path, monkeypatch):
    chrome_base = tmp_path / "Chrome"
    default_dir = chrome_base / "Default"
    default_dir.mkdir(parents=True)
    monkeypatch.setenv("BROWSER_FETCH_MCP_CHROME_BASE", str(chrome_base))

    async with stdio_client(_server_params(tmp_path)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                "list_chrome_profiles",
                {"host_keys": [".x.com"], "cookie_names": ["auth_token"]},
            )
            payload = result.structuredContent or json.loads(result.content[0].text)
            assert len(payload["profiles"]) == 1
            assert payload["profiles"][0]["profile_path"] == str(default_dir)
            assert payload["profiles"][0]["looks_logged_in"] is False

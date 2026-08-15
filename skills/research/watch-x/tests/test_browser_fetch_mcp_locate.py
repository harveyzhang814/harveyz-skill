from pathlib import Path

from browser_fetch_mcp_locate import find_browser_fetch_mcp


def test_find_browser_fetch_mcp_dev_mode_finds_repo_script():
    path = find_browser_fetch_mcp()
    assert path.endswith("tools/browser-fetch-mcp/browser-fetch-mcp.sh")
    assert Path(path).exists()

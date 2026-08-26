import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from browser_fetch_mcp_locate import find_browser_fetch_mcp


def test_find_browser_fetch_mcp_dev_mode_finds_repo_script():
    path = find_browser_fetch_mcp()
    assert path.endswith("tools/browser-fetch-mcp/browser-fetch-mcp.sh")
    assert Path(path).exists()

"""Locates the browser-fetch-mcp launcher for sync-ytchannel's MCP client scripts.

Two supported layouts:
- Dev mode: this skill runs from inside a harveyz-skill git checkout, where
  tools/browser-fetch-mcp/browser-fetch-mcp.sh sits four directories above
  scripts/ (skills/research/sync-ytchannel/scripts -> repo root).
- Installed mode: this skill was installed via `hskill install` (to
  ~/.claude/skills, ~/.pi/agent/skills, etc.), and browser-fetch-mcp was
  separately installed as a tool — its launcher lands at
  ~/.local/bin/browser-fetch-mcp (see tools/browser-fetch-mcp/tool.json).
"""
import shutil
import sys
from pathlib import Path


def find_browser_fetch_mcp() -> str:
    dev_path = Path(__file__).resolve().parents[4] / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
    if dev_path.exists():
        return str(dev_path)

    on_path = shutil.which("browser-fetch-mcp")
    if on_path:
        return on_path

    installed_path = Path.home() / ".local" / "bin" / "browser-fetch-mcp"
    if installed_path.exists():
        return str(installed_path)

    raise FileNotFoundError(
        "browser-fetch-mcp launcher not found. Run sync-ytchannel from a harveyz-skill "
        "git checkout, or run `hskill install` and select the browser-fetch-mcp tool."
    )


def main():
    """CLI preflight check for SKILL.md: prints FOUND/NOT_FOUND instead of
    letting the FileNotFoundError surface as a raw traceback from whichever
    client script happens to import this module first."""
    try:
        print(f"FOUND: {find_browser_fetch_mcp()}")
    except FileNotFoundError as e:
        print(f"NOT_FOUND: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

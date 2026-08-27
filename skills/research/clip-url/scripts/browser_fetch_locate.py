"""Locates the browser-fetch launcher for clip-url's client scripts.

Two supported layouts:
- Dev mode: this skill runs from inside a harveyz-skill git checkout, where
  tools/browser-fetch/browser-fetch.sh sits four directories above scripts/.
- Installed mode: this skill was installed via `hskill install` (to
  ~/.claude/skills, ~/.pi/agent/skills, etc.), and browser-fetch was
  separately installed as a tool — its launcher lands at
  ~/.local/bin/browser-fetch (see tools/browser-fetch/tool.json).
"""
import shutil
import sys
from pathlib import Path


def _dev_path() -> Path:
    return Path(__file__).resolve().parents[4] / "tools" / "browser-fetch" / "browser-fetch.sh"


def find_browser_fetch() -> str:
    dev_path = _dev_path()
    if dev_path.exists():
        return str(dev_path)

    on_path = shutil.which("browser-fetch")
    if on_path:
        return on_path

    installed_path = Path.home() / ".local" / "bin" / "browser-fetch"
    if installed_path.exists():
        return str(installed_path)

    raise FileNotFoundError(
        "browser-fetch launcher not found. Run clip-url from a harveyz-skill "
        "git checkout, or run `hskill install` and select the browser-fetch tool."
    )


def main():
    """CLI preflight check for SKILL.md: prints FOUND/NOT_FOUND instead of
    letting the FileNotFoundError surface as a raw traceback."""
    try:
        print(f"FOUND: {find_browser_fetch()}")
    except FileNotFoundError as e:
        print(f"NOT_FOUND: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

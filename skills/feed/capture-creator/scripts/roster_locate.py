"""定位 roster launcher（跟 browser_fetch_mcp_locate.py 同款，独立副本）。

两种布局：
- Dev 模式：本 skill 跑在 harveyz-skill 的 checkout 里，
  tools/roster/roster.sh 在 scripts/ 上面四层。
- 装机模式：经 hskill install 装到 ~/.claude/skills 等处，roster 作为 tool
  单独安装，launcher 落在 ~/.local/bin/roster。
"""
import shutil
import sys
from pathlib import Path


def _dev_path() -> Path:
    return Path(__file__).resolve().parents[4] / "tools" / "roster" / "roster.sh"


def find_roster() -> str:
    dev = _dev_path()
    if dev.exists():
        return str(dev)

    on_path = shutil.which("roster")
    if on_path:
        return on_path

    installed = Path.home() / ".local" / "bin" / "roster"
    if installed.exists():
        return str(installed)

    raise FileNotFoundError(
        "roster launcher 未找到。请在 harveyz-skill 的 checkout 里运行本 skill，"
        "或运行 `hskill install --tool roster`。"
    )


def main():
    try:
        print(f"FOUND: {find_roster()}")
    except FileNotFoundError as e:
        print(f"NOT_FOUND: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

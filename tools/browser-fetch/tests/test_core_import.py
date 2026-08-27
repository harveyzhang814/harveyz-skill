"""core 必须完全不依赖 mcp——这是整次改造的立足点，用断言钉住它。"""
import re
import subprocess
import sys
from pathlib import Path

TOOLS = (
    "fetch_page", "fetch_article", "fetch_user_timeline", "fetch_channel_videos",
    "evaluate_js", "list_chrome_profiles",
    "get_default_chrome_profile", "set_default_chrome_profile",
)

PROBE = """
import sys
sys.modules["mcp"] = None          # 让 `import mcp` 直接失败
import browser_fetch.core as c
missing = [n for n in {tools!r} if not hasattr(c, n)]
print("MISSING:" + ",".join(missing))
"""


def test_core_imports_without_mcp_and_exposes_all_eight_functions():
    r = subprocess.run(
        [sys.executable, "-c", PROBE.format(tools=TOOLS)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "MISSING:"


def test_core_source_has_no_mcp_imports_or_decorators():
    """只查真正的依赖形式。docstring 里引用旧设计文档名
    （…browser-fetch-mcp-xcom-extraction-design.md）是允许的，
    用整词匹配避免误报。"""
    src = (Path(__file__).resolve().parents[1] / "browser_fetch" / "core.py").read_text("utf-8")
    assert not re.search(r"^\s*(import mcp|from mcp)\b", src, re.M)
    assert "@mcp.tool" not in src
    assert "MCPServer" not in src

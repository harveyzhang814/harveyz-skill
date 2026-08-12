"""Unit tests for browser_fetch_mcp_locate.py's dev-mode / installed-mode
fallback — never touches a real browser-fetch-mcp installation."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import browser_fetch_mcp_locate  # noqa: E402
from browser_fetch_mcp_locate import find_browser_fetch_mcp  # noqa: E402


def test_prefers_dev_mode_path_when_it_exists(monkeypatch, tmp_path):
    dev_sh = tmp_path / "tools" / "browser-fetch-mcp" / "browser-fetch-mcp.sh"
    dev_sh.parent.mkdir(parents=True)
    dev_sh.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    fake_module_path = tmp_path / "skills" / "research" / "clip-url" / "scripts" / "browser_fetch_mcp_locate.py"
    monkeypatch.setattr(browser_fetch_mcp_locate, "__file__", str(fake_module_path))

    assert find_browser_fetch_mcp() == str(dev_sh)


def test_falls_back_to_path_lookup_when_dev_path_missing(monkeypatch, tmp_path):
    fake_module_path = tmp_path / "skills" / "research" / "clip-url" / "scripts" / "browser_fetch_mcp_locate.py"
    monkeypatch.setattr(browser_fetch_mcp_locate, "__file__", str(fake_module_path))
    monkeypatch.setattr(browser_fetch_mcp_locate.shutil, "which", lambda name: "/usr/local/bin/browser-fetch-mcp")

    assert find_browser_fetch_mcp() == "/usr/local/bin/browser-fetch-mcp"


def test_falls_back_to_local_bin_when_not_on_path(monkeypatch, tmp_path):
    fake_module_path = tmp_path / "skills" / "research" / "clip-url" / "scripts" / "browser_fetch_mcp_locate.py"
    monkeypatch.setattr(browser_fetch_mcp_locate, "__file__", str(fake_module_path))
    monkeypatch.setattr(browser_fetch_mcp_locate.shutil, "which", lambda name: None)

    fake_home = tmp_path / "home"
    installed = fake_home / ".local" / "bin" / "browser-fetch-mcp"
    installed.parent.mkdir(parents=True)
    installed.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    monkeypatch.setattr(browser_fetch_mcp_locate.Path, "home", classmethod(lambda cls: fake_home))

    assert find_browser_fetch_mcp() == str(installed)


def test_raises_actionable_error_when_nothing_found(monkeypatch, tmp_path):
    fake_module_path = tmp_path / "skills" / "research" / "clip-url" / "scripts" / "browser_fetch_mcp_locate.py"
    monkeypatch.setattr(browser_fetch_mcp_locate, "__file__", str(fake_module_path))
    monkeypatch.setattr(browser_fetch_mcp_locate.shutil, "which", lambda name: None)
    monkeypatch.setattr(browser_fetch_mcp_locate.Path, "home", classmethod(lambda cls: tmp_path / "empty-home"))

    with pytest.raises(FileNotFoundError, match="hskill install"):
        find_browser_fetch_mcp()

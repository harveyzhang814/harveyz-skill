"""Unit tests for config.py's persisted-default-profile read/write —
pure filesystem I/O, no MCP protocol involved."""
from pathlib import Path

from browser_fetch_mcp import config


def test_get_default_chrome_profile_returns_none_when_unconfigured(tmp_path):
    assert config.get_default_chrome_profile(tmp_path) is None


def test_set_then_get_round_trips(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/Users/x/Chrome/Default")
    assert config.get_default_chrome_profile(tmp_path) == "/Users/x/Chrome/Default"


def test_set_overwrites_previous_value(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/first/path")
    config.set_default_chrome_profile(tmp_path, "/second/path")
    assert config.get_default_chrome_profile(tmp_path) == "/second/path"


def test_config_file_written_at_expected_location(tmp_path):
    config.set_default_chrome_profile(tmp_path, "/some/path")
    assert (tmp_path / "config.json").exists()

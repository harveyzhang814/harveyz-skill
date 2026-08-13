"""Tests for chrome_profile_config.py — real browser-fetch-mcp
subprocess, real MCP stdio protocol, BROWSER_FETCH_MCP_DATA_DIR pointed
at an isolated tmp_path (never touches the real ~/.hskill config).

Run: python3 -m pytest skills/research/clip-url/tests/ -v
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "chrome_profile_config.py"


def _run(args: list[str], data_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={**os.environ, "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir)},
        capture_output=True, text=True, timeout=30,
    )


def test_get_reports_not_configured_initially(tmp_path):
    result = _run(["get"], tmp_path / "data")
    assert result.returncode == 0, result.stderr
    assert "NOT_CONFIGURED" in result.stdout


def test_set_then_get_reports_configured(tmp_path):
    data_dir = tmp_path / "data"
    profile_dir = tmp_path / "SomeProfile"
    profile_dir.mkdir()

    set_result = _run(["set", str(profile_dir)], data_dir)
    assert set_result.returncode == 0, set_result.stderr
    assert "OK" in set_result.stdout

    get_result = _run(["get"], data_dir)
    assert f"CONFIGURED: {profile_dir}" in get_result.stdout


def test_set_rejects_nonexistent_path(tmp_path):
    data_dir = tmp_path / "data"
    result = _run(["set", str(tmp_path / "DoesNotExist")], data_dir)
    assert result.returncode == 1
    assert result.stderr.strip() != ""


def _run_prompted(args: list[str], data_dir: Path, clip_url_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env={
            **os.environ,
            "BROWSER_FETCH_MCP_DATA_DIR": str(data_dir),
            "HSKILL_CLIP_URL_DATA_DIR": str(clip_url_dir),
        },
        capture_output=True, text=True, timeout=30,
    )


def test_prompted_reports_no_initially(tmp_path):
    result = _run_prompted(["prompted"], tmp_path / "data", tmp_path / "clip-url")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NO"


def test_mark_prompted_then_prompted_reports_yes(tmp_path):
    clip_url_dir = tmp_path / "clip-url"
    mark_result = _run_prompted(["mark-prompted"], tmp_path / "data", clip_url_dir)
    assert mark_result.returncode == 0, mark_result.stderr
    assert mark_result.stdout.strip() == "OK"

    prompted_result = _run_prompted(["prompted"], tmp_path / "data", clip_url_dir)
    assert prompted_result.stdout.strip() == "YES"

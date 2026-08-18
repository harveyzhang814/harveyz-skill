"""Persisted default Chrome profile — a single JSON file in the server's
data dir, {"default_chrome_profile": "<path>"}. Read/write here is pure
I/O; the caller (server.py) owns resolving `data_dir` (BROWSER_FETCH_MCP_DATA_DIR
override for tests) and validating the path before calling set().
"""
import json
from pathlib import Path
from typing import Optional


def _config_file(data_dir: Path) -> Path:
    return data_dir / "config.json"


def get_default_chrome_profile(data_dir: Path) -> Optional[str]:
    path = _config_file(data_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("default_chrome_profile")


def set_default_chrome_profile(data_dir: Path, profile_path: str) -> None:
    path = _config_file(data_dir)
    path.write_text(json.dumps({"default_chrome_profile": profile_path}), encoding="utf-8")


def _pace_file(data_dir: Path) -> Path:
    return data_dir / "timeline_pace.json"


def get_last_timeline_fetch_at(data_dir: Path) -> Optional[float]:
    path = _pace_file(data_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("last_timeline_fetch_at")


def set_last_timeline_fetch_at(data_dir: Path, ts: float) -> None:
    path = _pace_file(data_dir)
    path.write_text(json.dumps({"last_timeline_fetch_at": ts}), encoding="utf-8")

"""state.json —— 每个渠道的游标、上次运行时间、上次失败原因。

唯一写入方是抓取层（sync-* 经 `roster state` 命令组）。这份数据可重建：
删掉重跑最坏是刷一次基线、漏报一批，没有永久损失。

游标语义按平台各存各的，刻意不统一：X 的 snowflake id 单调递增可比大小，
YouTube 的 video id 不透明只能判「见过没有」。统一会逼 X 退化成 URL 集合，
白丢一个更省的表示。
"""
import json
from pathlib import Path

from . import SCHEMA_VERSION
from .urls import channel_key

CURSOR_TYPES = ("last_seen_id", "seen_urls")


def _path(data_dir: Path) -> Path:
    return Path(data_dir) / "state.json"


def load(data_dir: Path) -> dict:
    path = _path(data_dir)
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "channels": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def save(data_dir: Path, st: dict) -> None:
    path = _path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


def _entry(st: dict, platform: str, handle: str) -> dict:
    key = channel_key(platform, handle)
    return st["channels"].setdefault(
        key, {"cursor": None, "last_run": None, "last_error": None}
    )


def get_cursor(st: dict, platform: str, handle: str) -> dict | None:
    entry = st["channels"].get(channel_key(platform, handle))
    return entry["cursor"] if entry else None


def set_cursor(st: dict, platform: str, handle: str,
               cursor_type: str, value, run_time: str) -> None:
    if cursor_type not in CURSOR_TYPES:
        raise ValueError(f"未知的游标类型：{cursor_type}")
    entry = _entry(st, platform, handle)
    entry["cursor"] = {"type": cursor_type, "value": value}
    entry["last_run"] = run_time
    entry["last_error"] = None


def set_error(st: dict, platform: str, handle: str, error: str, run_time: str) -> None:
    """失败不动游标。让它倒退会导致下一次重报一批旧物料。"""
    entry = _entry(st, platform, handle)
    entry["last_run"] = run_time
    entry["last_error"] = error


def drop_channel(st: dict, platform: str, handle: str) -> None:
    st["channels"].pop(channel_key(platform, handle), None)

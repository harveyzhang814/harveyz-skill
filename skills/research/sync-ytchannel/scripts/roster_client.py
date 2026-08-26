#!/usr/bin/env python3
"""sync-ytchannel 与 roster 名册之间的桥。

只调两个命令组：`registry channels`（读渠道列表）和 `state`（读写游标）。
**绝不调 `registry add/remove/merge/rename`**——registry.json 的写入权
归 manage-roster，这里只读。画像同理，归认知层。
"""
import json
import subprocess
from pathlib import Path

from roster_locate import find_roster

PLATFORM = "youtube"


def _launcher() -> str:
    return find_roster()


def _run(*args: str) -> str:
    result = subprocess.run([_launcher(), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"roster {' '.join(args)} 失败：{result.stderr.strip()}")
    return result.stdout.strip()


def data_dir() -> Path:
    return Path(_run("data-dir"))


def channels() -> list[dict]:
    return json.loads(_run("registry", "channels", "--platform", PLATFORM))


def get_cursor(handle: str) -> list[str] | None:
    cursor = json.loads(_run("state", "get", f"{PLATFORM}:{handle}"))
    return cursor["value"] if cursor else None


def set_cursor(handle: str, seen_urls: list[str], run_time: str) -> None:
    _run("state", "set", f"{PLATFORM}:{handle}",
         "--type", "seen_urls",
         "--value-json", json.dumps(seen_urls, ensure_ascii=False),
         "--run-time", run_time)


def set_error(handle: str, error: str, run_time: str) -> None:
    _run("state", "fail", f"{PLATFORM}:{handle}", "--error", error, "--run-time", run_time)

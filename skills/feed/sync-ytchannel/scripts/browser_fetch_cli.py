"""四个 client 脚本共用的 browser-fetch CLI 调用层。

替代原先各自展开的 stdio_client + ClientSession 样板。CLI 退出码：
0 成功（stdout 一行 JSON）、2 调用方用法错、1 运行时失败——两种失败在
Python 侧统一抬成 RuntimeError，保持各 client 原有的异常契约不变。
"""
import json
import os
import subprocess

from browser_fetch_locate import find_browser_fetch

BROWSER_FETCH = find_browser_fetch()


def call(*args: str) -> dict:
    proc = subprocess.run(
        [BROWSER_FETCH, *args],
        capture_output=True, text=True, env=dict(os.environ),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"browser-fetch exited {proc.returncode}")
    return json.loads(proc.stdout)

"""四个 client 脚本共用的 `feedr fetch` CLI 调用层。

模块名沿用 browser_fetch_cli（Spec S8），底层命令已换成 `feedr fetch`。
替代原先各自展开的 stdio_client + ClientSession 样板。CLI 退出码：
0 成功（stdout 一行 JSON）、2 调用方用法错、1 运行时失败——两种失败在
Python 侧统一抬成 RuntimeError，保持各 client 原有的异常契约不变。
找不到 feedr 同样抬 RuntimeError，消息即安装提示。
"""
import json
import os
import shutil
import subprocess

INSTALL_HINT = (
    "feedr 未安装：uv tool install git+https://github.com/harveyzhang96/feedr"
    " && feedr fetch install-browser"
)


def call(*args: str) -> dict:
    feedr = shutil.which("feedr")
    if feedr is None:
        raise RuntimeError(INSTALL_HINT)
    proc = subprocess.run(
        [feedr, "fetch", *args],
        capture_output=True, text=True, env=dict(os.environ),
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"feedr fetch exited {proc.returncode}")
    return json.loads(proc.stdout)

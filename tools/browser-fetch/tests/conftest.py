"""CLI 测试统一通过真实 CLI 进程驱动。

环境构造：继承真实 os.environ，只覆盖 BROWSER_FETCH_DATA_DIR（必要时再加
BROWSER_FETCH_CHROME_BASE）。**不要覆盖 HOME** —— 本机 playwright 浏览器装在
~/Library/Caches/ms-playwright，HOME 被改指 tmp_path 后浏览器找不到，真抓取用例
会全体失败。数据隔离由 BROWSER_FETCH_DATA_DIR 单独保证：core 的 _data_dir()
只在该变量缺席时才回落到 HOME。
"""
import json
import os
import subprocess
import sys

import pytest


@pytest.fixture
def run_cli(tmp_path):
    def _run(*args, stdin=None, extra_env=None):
        env = dict(os.environ)
        env["BROWSER_FETCH_DATA_DIR"] = str(tmp_path / "data")
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(
            [sys.executable, "-m", "browser_fetch.cli", *args],
            capture_output=True, text=True, input=stdin, env=env,
        )
        payload = json.loads(proc.stdout) if proc.returncode == 0 else None
        return proc, payload
    return _run

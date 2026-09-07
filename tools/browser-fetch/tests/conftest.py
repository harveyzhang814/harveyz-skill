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


import functools
import http.server
import threading

_ARTICLES_FIXTURE_HTML = """<!doctype html>
<html><body>
<div class="entry"><h3><a href="/posts/1">First post</a></h3><p class="date">2026-01-01</p></div>
<div class="entry"><h3><a href="/posts/2">Second post</a></h3><p class="date">2026-01-02</p></div>
<div class="entry"><h3><a href="/posts/3">Third post</a></h3><p class="date">2026-01-03</p></div>
<div class="nav"><a href="/about">About</a></div>
</body></html>"""


@pytest.fixture
def articles_fixture_server(tmp_path):
    site_dir = tmp_path / "articles-fixture-site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text(_ARTICLES_FIXTURE_HTML, encoding="utf-8")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(site_dir))
    server = http.server.HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/index.html"
    finally:
        server.shutdown()
        thread.join()

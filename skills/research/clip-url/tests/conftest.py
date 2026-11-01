"""Shared test isolation for clip-url: points store_config at a fake
config.json under tmp_path for every test in this directory (autouse),
so a test file that forgets to declare its own isolation still can't read
or write the real ~/.hskill/config.json. Does not write config content —
tests that need a valid knowledgeRoot write it themselves (building on
isolated_store_config); tests exercising a missing/invalid config leave
it absent."""
import functools
import http.server
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

_BROWSER_FETCH_INSTALL_HINT = """\
{what}需要 browser-fetch（Python >= 3.11 + Playwright + Chromium），本机不可用，已跳过。
安装（在 harveyz-skill 仓库根目录）：
  cd tools/browser-fetch
  python3 -m venv .venv && .venv/bin/pip install -e .
  .venv/bin/python -m playwright install chromium
装好后重跑。探针原始输出：
{detail}"""


def _skip_unless_runs(tmp_path_factory, what, *args):
    """Run a browser-fetch probe; skip with install steps instead of erroring
    when it can't run here. Data dir is isolated so the probe never reads the
    real ~/.hskill/browser-fetch state."""
    from browser_fetch_cli import call

    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("BROWSER_FETCH_DATA_DIR", str(tmp_path_factory.mktemp("probe-data")))
        try:
            call(*args)
        except (RuntimeError, OSError) as e:
            pytest.skip(_BROWSER_FETCH_INSTALL_HINT.format(what=what, detail=str(e)[-600:]))


@pytest.fixture(scope="session")
def require_browser_fetch_cli(tmp_path_factory):
    """Launcher bootstrap + playwright import (no Chromium launch). For tests
    that only shell out to browser-fetch subcommands like `profile`."""
    _skip_unless_runs(tmp_path_factory, "browser-fetch CLI 测试", "profile", "list")


@pytest.fixture(scope="session")
def require_browser_fetch(tmp_path_factory, require_browser_fetch_cli):
    """Whole chain including a Chromium launch, probed by fetching an inline
    data: URL (no network or server). For tests that drive a real browser."""
    _skip_unless_runs(tmp_path_factory, "真浏览器测试", "page", "data:text/html,<p>ok</p>")


@pytest.fixture(autouse=True)
def isolated_store_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setenv("HSKILL_CONFIG", str(config_path))
    return config_path


_ARTICLE_HTML = """<!doctype html>
<html><head><title>Example Domain</title></head><body><main>
<h1>Example Domain</h1>
<p>This domain is for use in documentation examples without needing permission.</p>
<p>Its content is intentionally short and stable for extraction tests.</p>
<p>Each paragraph gives the generic extractor a predictable content unit.</p>
<p>The fixture never requires public DNS, TLS, or CDN access.</p>
</main></body></html>"""


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


@pytest.fixture
def local_site_urls(tmp_path, require_browser_fetch):
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    (site_dir / "article.html").write_text(_ARTICLE_HTML, encoding="utf-8")

    handler = functools.partial(_QuietHandler, directory=str(site_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        yield {
            "article": f"{base_url}/article.html",
        }
    finally:
        server.shutdown()
        thread.join()


@pytest.fixture
def local_article_url(local_site_urls):
    return local_site_urls["article"]

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
def local_site_urls(tmp_path):
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

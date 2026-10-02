"""真实 CLI/Chromium，不 mock；页面成功路径使用本地 HTTP fixture。"""


def test_page_anonymous_fetch(run_cli, local_page_url):
    proc, payload = run_cli("page", local_page_url)
    assert proc.returncode == 0, proc.stderr
    assert payload["title"] == "Local Browser Fetch Fixture"
    assert payload["status"] == 200
    assert payload["cookies_injected"] == 0


def test_page_auth_without_profile_exits_2(run_cli):
    proc, payload = run_cli("page", "https://example.com", "--auth")
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "chrome_profile is required" in proc.stderr


def test_page_auth_with_empty_profile_injects_nothing(run_cli, tmp_path, local_page_url):
    empty = tmp_path / "EmptyProfile"
    empty.mkdir()
    proc, payload = run_cli("page", local_page_url, "--auth", "--chrome-profile", str(empty))
    assert proc.returncode == 0, proc.stderr
    assert payload["cookies_injected"] == 0
    assert payload["status"] == 200


def test_eval_reads_js_from_file(run_cli, tmp_path):
    js = tmp_path / "probe.js"
    js.write_text("() => document.title", encoding="utf-8")
    proc, payload = run_cli("eval", "https://example.com", "--js-file", str(js))
    assert proc.returncode == 0, proc.stderr
    assert payload["result"] == "Example Domain"


def test_eval_reads_js_from_stdin(run_cli):
    proc, payload = run_cli("eval", "https://example.com", "--js-file", "-",
                             stdin="() => document.title")
    assert proc.returncode == 0, proc.stderr
    assert payload["result"] == "Example Domain"


def test_eval_rejects_non_http_scheme_with_exit_2(run_cli, tmp_path):
    js = tmp_path / "probe.js"
    js.write_text("() => 1", encoding="utf-8")
    proc, payload = run_cli("eval", "file:///etc/passwd", "--js-file", str(js))
    assert proc.returncode == 2
    assert proc.stdout == ""

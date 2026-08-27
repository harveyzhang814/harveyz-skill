def test_evaluate_js_returns_page_evaluate_result(run_cli, tmp_path):
    js_file = tmp_path / "probe.js"
    js_file.write_text("() => document.title", encoding="utf-8")
    proc, payload = run_cli("eval", "https://example.com", "--js-file", str(js_file))
    assert payload["result"] == "Example Domain"


def test_evaluate_js_rejects_invalid_scheme(run_cli, tmp_path):
    js_file = tmp_path / "probe.js"
    js_file.write_text("() => document.title", encoding="utf-8")
    proc, _ = run_cli("eval", "ftp://example.com", "--js-file", str(js_file))
    assert proc.returncode == 2
    assert "ftp" in proc.stderr


def test_evaluate_js_with_chrome_profile_no_matching_cookies(run_cli, tmp_path):
    """No real auth cookies available in an automated test — just confirms
    the chrome_profile code path doesn't crash and still returns a result,
    matching test_fetch_page_use_auth_no_matching_cookies's approach."""
    empty_profile = tmp_path / "EmptyProfile"
    js_file = tmp_path / "probe.js"
    js_file.write_text("() => document.title", encoding="utf-8")
    proc, payload = run_cli(
        "eval", "https://example.com", "--js-file", str(js_file),
        "--chrome-profile", str(empty_profile),
    )
    assert payload["result"] == "Example Domain"

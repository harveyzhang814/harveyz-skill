def test_fetch_user_timeline_rejects_non_xcom_url(run_cli):
    proc, _ = run_cli("timeline", "https://example.com/someuser")
    assert proc.returncode == 2
    assert "only supports x.com/twitter.com URLs" in proc.stderr


def test_fetch_user_timeline_rejects_file_scheme(run_cli):
    proc, _ = run_cli("timeline", "file:///etc/passwd")
    assert proc.returncode == 2


def test_fetch_user_timeline_without_chrome_profile_is_rejected(run_cli):
    proc, _ = run_cli("timeline", "https://x.com/someuser")
    assert proc.returncode == 2
    assert "chrome_profile is required" in proc.stderr


def test_fetch_user_timeline_falls_back_to_persisted_default(run_cli, tmp_path):
    """No chrome_profile passed, but a default is configured — must get PAST
    the 'chrome_profile is required' check and reach the auth-cookie check
    instead (proving resolution happened), same pattern as
    test_fetch_article_x_dot_com_falls_back_to_persisted_default."""
    default_profile = tmp_path / "DefaultProfile"
    default_profile.mkdir()
    set_proc, _ = run_cli("profile", "set", str(default_profile))
    assert set_proc.returncode == 0, set_proc.stderr

    proc, _ = run_cli("timeline", "https://x.com/someuser")
    assert proc.returncode == 2
    assert "No x.com session cookies" in proc.stderr
    assert "is required" not in proc.stderr

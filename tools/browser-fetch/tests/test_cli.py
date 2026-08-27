import pytest


def test_profile_get_returns_null_when_unset(run_cli):
    proc, payload = run_cli("profile", "get")
    assert proc.returncode == 0, proc.stderr
    assert payload == {"profile_path": None}


def test_profile_set_then_get_round_trips(run_cli, tmp_path):
    p = tmp_path / "SomeProfile"
    p.mkdir()
    proc, payload = run_cli("profile", "set", str(p))
    assert proc.returncode == 0, proc.stderr
    assert payload == {"ok": True}

    proc, payload = run_cli("profile", "get")
    assert payload["profile_path"] == str(p)


def test_profile_set_rejects_missing_path_with_exit_2(run_cli, tmp_path):
    proc, _ = run_cli("profile", "set", str(tmp_path / "Nope"))
    assert proc.returncode == 2
    assert proc.stdout == ""
    assert "not a directory" in proc.stderr


def test_profile_list_reports_profiles(run_cli, tmp_path):
    chrome_base = tmp_path / "Chrome"
    (chrome_base / "Default").mkdir(parents=True)
    proc, payload = run_cli(
        "profile", "list", "--host-key", ".x.com", "--cookie-name", "auth_token",
        extra_env={"BROWSER_FETCH_CHROME_BASE": str(chrome_base)},
    )
    assert proc.returncode == 0, proc.stderr
    profiles = payload["profiles"]
    assert len(profiles) == 1
    assert profiles[0]["looks_logged_in"] is False


def test_stdout_is_single_line_compact_json(run_cli):
    proc, _ = run_cli("profile", "get")
    assert proc.stdout.count("\n") == 1
    assert ", " not in proc.stdout

from pathlib import Path


def test_article_default_format_writes_file_and_returns_path(run_cli, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    proc, payload = run_cli("article", "https://example.com", "--out", str(out))
    assert proc.returncode == 0, proc.stderr
    assert "blocks" not in payload
    origin = Path(payload["origin_path"])
    assert origin.exists()
    assert origin.parent.name == "Origin"
    assert payload["title"] == "Example Domain"


def test_article_json_format_returns_blocks_and_writes_nothing(run_cli, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    proc, payload = run_cli("article", "https://example.com", "--out", str(out), "--format", "json")
    assert proc.returncode == 0, proc.stderr
    assert isinstance(payload["blocks"], list)
    assert "origin_path" not in payload
    assert not (out / "Origin").exists()


def test_article_xcom_without_profile_exits_2(run_cli, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    proc, payload = run_cli("article", "https://x.com/someone/status/1", "--out", str(out))
    assert proc.returncode == 2
    assert proc.stdout == ""


def test_timeline_without_profile_exits_2(run_cli):
    proc, payload = run_cli("timeline", "https://x.com/someone")
    assert proc.returncode == 2
    assert proc.stdout == ""


def test_channel_lists_videos(run_cli):
    proc, payload = run_cli("channel", "https://www.youtube.com/@YouTube", "--max", "5")
    assert proc.returncode == 0, proc.stderr
    videos = payload["videos"]
    assert len(videos) <= 5
    assert all("title" in v and "url" in v for v in videos)

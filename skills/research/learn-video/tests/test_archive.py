"""Unit tests for archive.py — learn-video's first piece of local logic:
copying vdl's output into <ROOT>/videos/<task_id>/ and writing meta.json."""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive import archive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive.py"


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_archive_copies_three_files_and_writes_meta(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "raw transcript")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "article body")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "summary body")

    result = archive("t1", "https://youtube.com/watch?v=t1", "My Video",
                      str(transcript), str(article), str(summary),
                      fetched_at="2026-09-01")

    assert result["video_dir"] == isolated_store_config / "videos" / "t1"
    assert result["transcript_path"].read_text(encoding="utf-8") == "raw transcript"
    assert result["article_path"].read_text(encoding="utf-8") == "article body"
    assert result["summary_path"].read_text(encoding="utf-8") == "summary body"

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta == {
        "source_url": "https://youtube.com/watch?v=t1",
        "title": "My Video",
        "fetched_at": "2026-09-01",
    }


def test_archive_layout_matches_spec_directory_structure(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "x")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "x")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "x")

    result = archive("t1", "u", "T", str(transcript), str(article), str(summary))

    assert result["transcript_path"] == isolated_store_config / "videos" / "t1" / "transcript" / "original.md"
    assert result["article_path"] == isolated_store_config / "videos" / "t1" / "writing" / "article.md"
    assert result["summary_path"] == isolated_store_config / "videos" / "t1" / "writing" / "summary.md"


def test_archive_is_idempotent_for_same_task_id(tmp_path, isolated_store_config):
    transcript = _write(tmp_path / "work" / "t1" / "transcript" / "original.md", "v1")
    article = _write(tmp_path / "work" / "t1" / "writing" / "article.md", "v1")
    summary = _write(tmp_path / "work" / "t1" / "writing" / "summary.md", "v1")
    archive("t1", "u", "T", str(transcript), str(article), str(summary), fetched_at="2026-09-01")

    transcript.write_text("v2", encoding="utf-8")
    result = archive("t1", "u", "T2", str(transcript), str(article), str(summary), fetched_at="2026-09-02")

    assert result["transcript_path"].read_text(encoding="utf-8") == "v2"
    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta["title"] == "T2"
    assert meta["fetched_at"] == "2026-09-02"


def test_cli_prints_video_dir_and_meta_path(tmp_path, isolated_store_config, monkeypatch):
    transcript = _write(tmp_path / "transcript.md", "x")
    article = _write(tmp_path / "article.md", "x")
    summary = _write(tmp_path / "summary.md", "x")
    env = {
        **os.environ,
        "TASK_ID": "t1", "SOURCE_URL": "u", "TITLE": "T",
        "TRANSCRIPT_PATH": str(transcript), "ARTICLE_PATH": str(article), "SUMMARY_PATH": str(summary),
        "FETCHED_AT": "2026-09-01",
        "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"],
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    expected_dir = isolated_store_config / "videos" / "t1"
    assert f"VIDEO_DIR: {expected_dir}" in result.stdout
    assert f"META_PATH: {expected_dir / 'meta.json'}" in result.stdout

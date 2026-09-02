"""Unit tests for archive.py — learn-video's only piece of local logic:
writing meta.json into the task directory vdl already produced at
<ROOT>/videos/work/<task_id>/."""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive import archive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive.py"


def _vdl_task_dir(root: Path, task_id: str) -> Path:
    """Stand in for what vdl leaves behind once WORK_ROOT == <ROOT>/videos."""
    task_dir = root / "videos" / "work" / task_id
    (task_dir / "transcript").mkdir(parents=True, exist_ok=True)
    (task_dir / "writing").mkdir(parents=True, exist_ok=True)
    (task_dir / "transcript" / "original_zh.md").write_text("raw", encoding="utf-8")
    (task_dir / "writing" / "article.md").write_text("body", encoding="utf-8")
    return task_dir


def test_archive_writes_meta_into_vdl_task_dir(tmp_path, isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1")

    result = archive("t1", "https://youtube.com/watch?v=t1", "My Video",
                     fetched_at="2026-09-01")

    assert result["video_dir"] == task_dir
    assert result["meta_path"] == task_dir / "meta.json"
    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta == {
        "source_url": "https://youtube.com/watch?v=t1",
        "title": "My Video",
        "fetched_at": "2026-09-01",
        # scholia reads meta.url; with no vdl DB around it falls back to the
        # source_url we were handed rather than rendering an empty link.
        "url": "https://youtube.com/watch?v=t1",
    }


def test_archive_leaves_vdl_artifacts_untouched(tmp_path, isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1")

    archive("t1", "u", "T", fetched_at="2026-09-01")

    assert (task_dir / "transcript" / "original_zh.md").read_text(encoding="utf-8") == "raw"
    assert (task_dir / "writing" / "article.md").read_text(encoding="utf-8") == "body"


def test_archive_is_idempotent_for_same_task_id(tmp_path, isolated_store_config):
    _vdl_task_dir(isolated_store_config, "t1")
    archive("t1", "u", "T", fetched_at="2026-09-01")

    result = archive("t1", "u", "T2", fetched_at="2026-09-02")

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta["title"] == "T2"
    assert meta["fetched_at"] == "2026-09-02"


def test_archive_refuses_to_create_an_orphan_meta(tmp_path, isolated_store_config):
    """WORK_ROOT drifting away from <ROOT>/videos must fail loudly rather
    than leave a meta.json in a directory holding no vdl artifacts."""
    with pytest.raises(FileNotFoundError) as excinfo:
        archive("missing", "u", "T")

    assert "vdl config set work-root" in str(excinfo.value)
    assert not (isolated_store_config / "videos" / "work" / "missing").exists()


def test_cli_prints_video_dir_and_meta_path(tmp_path, isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1")
    env = {
        **os.environ,
        "TASK_ID": "t1", "SOURCE_URL": "u", "TITLE": "T",
        "FETCHED_AT": "2026-09-01",
        "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"],
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert f"VIDEO_DIR: {task_dir}" in result.stdout
    assert f"META_PATH: {task_dir / 'meta.json'}" in result.stdout


def test_cli_exits_nonzero_when_task_dir_missing(tmp_path, isolated_store_config):
    env = {
        **os.environ,
        "TASK_ID": "nope", "SOURCE_URL": "u", "TITLE": "T",
        "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"],
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "vdl config set work-root" in result.stderr


def _vdl_db(root: Path, rows):
    """vdl's own database, which is what actually knows the uploader/duration."""
    db_path = root / "videos" / "work" / "database.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("create table tasks (id TEXT PRIMARY KEY, url TEXT, uploader TEXT, "
                 "upload_date TEXT, duration TEXT, mode TEXT, output_lang TEXT, ts TEXT)")
    conn.executemany("insert into tasks values (?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    conn.close()


def test_archive_pulls_display_fields_from_vdl_db(tmp_path, isolated_store_config):
    _vdl_task_dir(isolated_store_config, "t1")
    _vdl_db(isolated_store_config, [
        ("t1", "https://youtube.com/watch?v=t1", "Some Channel", "20260701",
         "1830", "media", "zh-CN", "2026-07-01T00:00:00Z"),
    ])

    result = archive("t1", "https://youtube.com/watch?v=t1", "My Video", fetched_at="2026-09-01")

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta["source_url"] == "https://youtube.com/watch?v=t1"
    assert meta["fetched_at"] == "2026-09-01"
    assert meta["uploader"] == "Some Channel"
    assert meta["upload_date"] == "20260701"
    assert meta["duration"] == "1830"
    assert meta["mode"] == "media"
    assert meta["output_lang"] == "zh-CN"
    assert meta["ts"] == "2026-07-01T00:00:00Z"


def test_archive_omits_display_fields_the_db_left_empty(tmp_path, isolated_store_config):
    """uploader/upload_date/duration are null for most of vdl's history. An
    absent key is honest; an empty string would render as a blank field."""
    _vdl_task_dir(isolated_store_config, "t1")
    _vdl_db(isolated_store_config, [
        ("t1", "https://youtube.com/watch?v=t1", None, "", None, "media", "zh-CN", "2026-07-01T00:00:00Z"),
    ])

    result = archive("t1", "https://youtube.com/watch?v=t1", "My Video", fetched_at="2026-09-01")

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert "uploader" not in meta
    assert "upload_date" not in meta
    assert "duration" not in meta
    assert meta["mode"] == "media"


def test_archive_survives_a_missing_vdl_db(tmp_path, isolated_store_config):
    """Enrichment is best-effort — no DB must not turn into a failed archive."""
    _vdl_task_dir(isolated_store_config, "t1")

    result = archive("t1", "u", "T", fetched_at="2026-09-01")

    meta = json.loads(result["meta_path"].read_text(encoding="utf-8"))
    assert meta["title"] == "T"
    assert meta["url"] == "u"

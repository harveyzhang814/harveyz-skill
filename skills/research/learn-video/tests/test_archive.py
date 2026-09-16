"""Unit tests for archive.py — now a pure validator: vdl already wrote
meta.json (see docs/superpowers/specs/2026-09-15-video-creator-index-design.md
§1.3), this script just checks it satisfies the unified-store contract."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive import archive  # noqa: E402

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "archive.py"


def _vdl_task_dir(root: Path, task_id: str, meta: dict | None = None) -> Path:
    """Stand in for what vdl leaves behind: task dir + artifacts + meta.json
    (vdl writes meta.json itself now — this helper mirrors that)."""
    task_dir = root / "videos" / "work" / task_id
    (task_dir / "transcript").mkdir(parents=True, exist_ok=True)
    (task_dir / "writing").mkdir(parents=True, exist_ok=True)
    (task_dir / "transcript" / "original_zh.md").write_text("raw", encoding="utf-8")
    (task_dir / "writing" / "article.md").write_text("body", encoding="utf-8")
    if meta is not None:
        (task_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    return task_dir


VALID_META = {
    "source_url": "https://youtube.com/watch?v=t1",
    "title": "My Video",
    "fetched_at": "2026-09-15",
    "uploader_id": "@alejandro_ao",
    "channel_id": "UC1oXUA7qgs0GZc_yk46K2OQ",
    "uploader_url": "https://www.youtube.com/@alejandro_ao",
}


def test_archive_accepts_meta_with_all_required_fields(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)

    result = archive("t1")

    assert result["video_dir"] == task_dir
    assert result["meta_path"] == task_dir / "meta.json"
    # archive() must not modify meta.json — it's read-only now
    assert json.loads(result["meta_path"].read_text(encoding="utf-8")) == VALID_META


@pytest.mark.parametrize("missing_field", ["source_url", "title", "fetched_at"])
def test_archive_rejects_meta_missing_a_required_field(isolated_store_config, missing_field):
    meta = {k: v for k, v in VALID_META.items() if k != missing_field}
    _vdl_task_dir(isolated_store_config, "t1", meta)

    with pytest.raises(SystemExit) as excinfo:
        archive("t1")

    assert missing_field in str(excinfo.value)


def test_archive_rejects_when_meta_json_absent(isolated_store_config):
    """vdl hasn't finished writing meta.json yet (task not 'completed')."""
    _vdl_task_dir(isolated_store_config, "t1", meta=None)

    with pytest.raises(SystemExit) as excinfo:
        archive("t1")

    assert "meta.json 不存在" in str(excinfo.value)


def test_archive_refuses_when_task_dir_missing(isolated_store_config):
    with pytest.raises(FileNotFoundError) as excinfo:
        archive("missing")

    assert "vdl config set work-root" in str(excinfo.value)


def test_archive_leaves_vdl_artifacts_untouched(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)

    archive("t1")

    assert (task_dir / "transcript" / "original_zh.md").read_text(encoding="utf-8") == "raw"
    assert (task_dir / "writing" / "article.md").read_text(encoding="utf-8") == "body"


def test_cli_prints_video_dir_and_meta_path(isolated_store_config):
    task_dir = _vdl_task_dir(isolated_store_config, "t1", VALID_META)
    env = {**os.environ, "TASK_ID": "t1", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
    assert f"VIDEO_DIR: {task_dir}" in result.stdout
    assert f"META_PATH: {task_dir / 'meta.json'}" in result.stdout


def test_cli_exits_nonzero_when_task_dir_missing(isolated_store_config):
    env = {**os.environ, "TASK_ID": "nope", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "vdl config set work-root" in result.stderr


def test_cli_exits_nonzero_when_required_field_missing(isolated_store_config):
    meta = {k: v for k, v in VALID_META.items() if k != "fetched_at"}
    _vdl_task_dir(isolated_store_config, "t1", meta)
    env = {**os.environ, "TASK_ID": "t1", "HSKILL_CONFIG": os.environ["HSKILL_CONFIG"]}
    result = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, timeout=10,
    )
    assert result.returncode != 0
    assert "fetched_at" in result.stderr

"""Unit tests for build_creator_index.py — groups vdl's meta.json entities
by normalized uploader handle into <knowledgeRoot>/videos/creators.json.
Never reads registry.json (spec §1.5, §3.3) — matching to the roster is
scholia's job, not this script's."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from build_creator_index import build_index, check_index, write_index  # noqa: E402


def _meta(root: Path, task_id: str, **fields) -> Path:
    task_dir = root / "videos" / "work" / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    meta_path = task_dir / "meta.json"
    meta_path.write_text(json.dumps(fields, ensure_ascii=False), encoding="utf-8")
    return meta_path


def test_build_groups_videos_by_normalized_handle(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="Alejandro AO", uploader_id="@alejandro_ao",
          uploader_url="https://www.youtube.com/@alejandro_ao",
          channel_id="UC1oXUA7qgs0GZc_yk46K2OQ", upload_date="2026-06-01", duration="120")
    # Same person, different case in the handle — must fold into the same key
    # (YouTube handles are case-insensitive, confirmed against Google's own
    # help docs — see spec §7.1).
    _meta(root, "t2", title="V2", uploader="Alejandro AO", uploader_id="@Alejandro_AO",
          upload_date="2026-07-01", duration="200")

    index = build_index(root / "videos" / "work")

    assert index["schema_version"] == 1
    assert index["scanned"]["entities"] == 2
    assert len(index["creators"]) == 1
    creator = index["creators"][0]
    assert creator["key"] == "alejandro_ao"
    assert creator["channel_id"] == "UC1oXUA7qgs0GZc_yk46K2OQ"
    assert creator["uploader_url"] == "https://www.youtube.com/@alejandro_ao"
    assert {v["task_id"] for v in creator["videos"]} == {"t1", "t2"}
    assert index["unresolved"] == []


def test_build_puts_missing_uploader_id_into_unresolved(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="Matt Pocock")
    _meta(root, "t2", title="V2", uploader="Matt Pocock")
    _meta(root, "t3", title="V3", uploader="Someone Else")

    index = build_index(root / "videos" / "work")

    assert index["creators"] == []
    assert len(index["unresolved"]) == 2
    matt = next(u for u in index["unresolved"] if u["display_name"] == "Matt Pocock")
    assert set(matt["task_ids"]) == {"t1", "t2"}


def test_every_scanned_entity_is_accounted_for(isolated_store_config):
    """Acceptance criterion #4: creators[].videos + unresolved[].task_ids
    total must equal the disk meta.json count — no entity may vanish."""
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    _meta(root, "t2", title="V2", uploader="B")
    _meta(root, "t3", title="V3", uploader="A", uploader_id="@a")

    index = build_index(root / "videos" / "work")

    video_count = sum(len(c["videos"]) for c in index["creators"])
    unresolved_count = sum(len(u["task_ids"]) for u in index["unresolved"])
    assert video_count + unresolved_count == index["scanned"]["entities"] == 3


def test_write_index_is_atomic_on_failure(isolated_store_config, monkeypatch):
    """Acceptance criterion #7: a failed/killed build must not corrupt or
    remove the previous creators.json."""
    root = isolated_store_config
    output_path = root / "videos" / "creators.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text('{"schema_version": 1, "old": true}', encoding="utf-8")

    def _boom(self, target):
        raise OSError("simulated crash mid-write")

    monkeypatch.setattr(Path, "rename", _boom)

    index = build_index(root / "videos" / "work")
    try:
        write_index(index, output_path)
    except OSError:
        pass

    assert json.loads(output_path.read_text(encoding="utf-8")) == {"schema_version": 1, "old": True}


def test_check_reports_ok_when_index_matches_disk(isolated_store_config):
    root = isolated_store_config
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    work_dir = root / "videos" / "work"
    output_path = root / "videos" / "creators.json"
    write_index(build_index(work_dir), output_path)

    ok, message = check_index(work_dir, output_path)
    assert ok is True
    assert message.startswith("OK:")


def test_check_reports_stale_when_disk_has_more_entities(isolated_store_config):
    root = isolated_store_config
    work_dir = root / "videos" / "work"
    output_path = root / "videos" / "creators.json"
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")
    write_index(build_index(work_dir), output_path)

    _meta(root, "t2", title="V2", uploader="B", uploader_id="@b")  # not rebuilt

    ok, message = check_index(work_dir, output_path)
    assert ok is False
    assert "STALE" in message


def test_check_reports_stale_when_index_missing(isolated_store_config):
    root = isolated_store_config
    work_dir = root / "videos" / "work"
    _meta(root, "t1", title="V1", uploader="A", uploader_id="@a")

    ok, message = check_index(work_dir, root / "videos" / "creators.json")
    assert ok is False
    assert "STALE" in message

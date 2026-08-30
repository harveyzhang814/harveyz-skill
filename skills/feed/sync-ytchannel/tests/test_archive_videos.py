import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from archive_videos import archive_videos, _archive_path


def test_archive_videos_writes_new_handle_file(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    report = {
        "run_time": "2026-08-15T09:00:00+00:00",
        "new": {"a": [{"video_id": "v1", "url": "u1", "title": "T", "translated": "译"}]},
    }
    archive_videos(report)
    saved = json.loads(_archive_path("a").read_text(encoding="utf-8"))
    assert saved == report["new"]["a"]


def test_archive_videos_appends_across_calls(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    first = {"run_time": "t", "new": {"a": [{"video_id": "v1", "url": "u1", "title": "T1"}]}}
    second = {"run_time": "t", "new": {"a": [{"video_id": "v2", "url": "u2", "title": "T2"}]}}
    archive_videos(first)
    archive_videos(second)
    saved = json.loads(_archive_path("a").read_text(encoding="utf-8"))
    assert [v["video_id"] for v in saved] == ["v1", "v2"]


def test_archive_videos_dedups_by_video_id(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    report = {"run_time": "t", "new": {"a": [{"video_id": "v1", "url": "u1", "title": "T"}]}}
    archive_videos(report)
    archive_videos(report)
    saved = json.loads(_archive_path("a").read_text(encoding="utf-8"))
    assert len(saved) == 1


def test_archive_videos_keeps_handles_isolated(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    report = {
        "run_time": "t",
        "new": {
            "a": [{"video_id": "v1", "url": "u1", "title": "T"}],
            "b": [{"video_id": "v9", "url": "u9", "title": "T9"}],
        },
    }
    archive_videos(report)
    assert [v["video_id"] for v in json.loads(_archive_path("a").read_text(encoding="utf-8"))] == ["v1"]
    assert [v["video_id"] for v in json.loads(_archive_path("b").read_text(encoding="utf-8"))] == ["v9"]


def test_archive_videos_noop_when_report_has_no_new(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    report = {"run_time": "t", "new": {}, "baselines": {"c": 3}, "failures": {}}
    archive_videos(report)
    assert not _archive_path("c").exists()


def test_archive_path_is_under_youtube_creators(tmp_path, monkeypatch):
    import roster_client
    monkeypatch.setattr(roster_client, "data_dir", lambda: tmp_path)
    assert _archive_path("a") == tmp_path / "youtube" / "creators" / "a.json"

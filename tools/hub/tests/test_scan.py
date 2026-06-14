import subprocess
from pathlib import Path
import pytest
from hub.core.db import HubDB
from hub.core.projects import scan_projects


def _make_repo(path: Path, origin: str | None = None) -> Path:
    """Create a minimal git repo under path/."""
    path.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=path, check=True, capture_output=True,
        env={**__import__("os").environ, "GIT_AUTHOR_NAME": "t",
             "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
             "GIT_COMMITTER_EMAIL": "t@t"},
    )
    if origin:
        subprocess.run(
            ["git", "remote", "add", "origin", origin],
            cwd=path, check=True, capture_output=True,
        )
    return path


def test_scan_adds_repo_using_remote_name(tmp_path):
    _make_repo(tmp_path / "repo-a", origin="https://github.com/user/my-repo.git")
    db = HubDB(db_path=tmp_path / "hub.db")
    md_path = tmp_path / "PROJECTS.md"
    result = scan_projects([str(tmp_path)], db, md_path=md_path)
    assert len(result["added"]) == 1
    assert result["added"][0]["name"] == "my-repo"
    assert result["skipped"] == []
    assert result["failed"] == []


def test_scan_fallback_to_dir_name_when_no_remote(tmp_path):
    _make_repo(tmp_path / "repo-b")  # no origin
    db = HubDB(db_path=tmp_path / "hub.db")
    md_path = tmp_path / "PROJECTS.md"
    result = scan_projects([str(tmp_path)], db, md_path=md_path)
    assert result["added"][0]["name"] == "repo-b"


def test_scan_skips_existing_project(tmp_path):
    _make_repo(tmp_path / "repo-a", origin="https://github.com/user/repo-a.git")
    db = HubDB(db_path=tmp_path / "hub.db")
    md_path = tmp_path / "PROJECTS.md"
    from hub.core.projects import add_project
    add_project(db, "repo-a", path="/old/path", md_path=md_path)
    result = scan_projects([str(tmp_path)], db, md_path=md_path)
    assert "repo-a" in result["skipped"]
    assert result["added"] == []


def test_scan_nonexistent_dir_goes_to_failed(tmp_path):
    db = HubDB(db_path=tmp_path / "hub.db")
    result = scan_projects(["/nonexistent/path/xyz"], db)
    assert result["added"] == []
    assert result["failed"][0]["reason"] == "directory not found"

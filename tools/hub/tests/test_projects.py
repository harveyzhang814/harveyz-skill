import pytest
from pathlib import Path
from hub.core.db import HubDB
from hub.core.projects import add_project, list_projects, get_project_path


@pytest.fixture
def db(tmp_path):
    return HubDB(db_path=tmp_path / "hub.db")


@pytest.fixture
def md_path(tmp_path):
    return tmp_path / "PROJECTS.md"


def test_add_project_persists(db, md_path):
    add_project(db, "video-learner", path="/home/user/video-learner", md_path=md_path)
    projects = list_projects(db)
    assert len(projects) == 1
    assert projects[0]["name"] == "video-learner"
    assert projects[0]["path"] == "/home/user/video-learner"


def test_add_project_writes_md(db, md_path):
    add_project(db, "video-learner", path="/home/user/video-learner", md_path=md_path)
    content = md_path.read_text()
    assert "video-learner" in content
    assert "/home/user/video-learner" in content


def test_add_project_upserts(db, md_path):
    add_project(db, "video-learner", path="/old", md_path=md_path)
    add_project(db, "video-learner", path="/new", md_path=md_path)
    projects = list_projects(db)
    assert len(projects) == 1
    assert projects[0]["path"] == "/new"


def test_get_project_path_found(db, md_path):
    add_project(db, "blog", path="/home/user/blog", md_path=md_path)
    assert get_project_path(db, "blog") == "/home/user/blog"


def test_get_project_path_not_found(db):
    assert get_project_path(db, "nonexistent") is None


def test_list_projects_empty(db):
    assert list_projects(db) == []

import pytest
from pathlib import Path
from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task, list_tasks, mark_done, delete_task, update_task


@pytest.fixture
def db(tmp_path):
    db = HubDB(db_path=tmp_path / "hub.db")
    add_project(db, "blog", path="/blog", md_path=tmp_path / "PROJECTS.md")
    return db


def test_add_task_returns_task(db):
    t = add_task(db, title="Write post", project="blog")
    assert t["id"] is not None
    assert t["title"] == "Write post"
    assert t["priority"] == "P2"
    assert t["status"] == "todo"
    assert t["project"] == "blog"


def test_add_task_unknown_project_raises(db):
    with pytest.raises(ValueError, match="Project 'nope' not found"):
        add_task(db, title="x", project="nope")


def test_list_tasks_all(db):
    add_task(db, title="A", project="blog")
    add_task(db, title="B", project="blog", priority="P1")
    tasks = list_tasks(db)
    assert len(tasks) == 2


def test_list_tasks_filter_project(db):
    add_task(db, title="A", project="blog")
    tasks = list_tasks(db, project="blog")
    assert len(tasks) == 1


def test_list_tasks_filter_status(db):
    t = add_task(db, title="A", project="blog")
    mark_done(db, t["id"])
    assert list_tasks(db, status="todo") == []
    assert len(list_tasks(db, status="done")) == 1


def test_mark_done_updates_status(db):
    t = add_task(db, title="A", project="blog")
    result = mark_done(db, t["id"])
    assert result["status"] == "done"


def test_mark_done_missing_id_returns_none(db):
    assert mark_done(db, 9999) is None


def test_delete_task_removes_it(db):
    t = add_task(db, title="A", project="blog")
    assert delete_task(db, t["id"]) is True
    assert list_tasks(db) == []


def test_update_task_title(db):
    t = add_task(db, title="Old", project="blog")
    updated = update_task(db, t["id"], title="New")
    assert updated["title"] == "New"


def test_update_task_priority(db):
    t = add_task(db, title="A", project="blog")
    updated = update_task(db, t["id"], priority="P1")
    assert updated["priority"] == "P1"

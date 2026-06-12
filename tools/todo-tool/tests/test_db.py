import pytest
from pathlib import Path
from todo.db import TodoDB
from todo.models import TaskCreate, TaskUpdate


@pytest.fixture
def db(tmp_path):
    return TodoDB(db_path=tmp_path / "test.db")


def test_create_task(db):
    task = db.create(TaskCreate(title="Fix bug", project="myapp"))
    assert task.id == 1
    assert task.title == "Fix bug"
    assert task.project == "myapp"
    assert task.priority == "P2"
    assert task.status == "todo"


def test_create_task_custom_priority(db):
    task = db.create(TaskCreate(title="Urgent", project="myapp", priority="P0"))
    assert task.priority == "P0"


def test_get_task(db):
    created = db.create(TaskCreate(title="T", project="p"))
    fetched = db.get(created.id)
    assert fetched.title == "T"


def test_get_missing_task(db):
    assert db.get(999) is None


def test_list_all(db):
    db.create(TaskCreate(title="T1", project="proj-a"))
    db.create(TaskCreate(title="T2", project="proj-b"))
    assert len(db.list_tasks()) == 2


def test_list_filter_project(db):
    db.create(TaskCreate(title="T1", project="proj-a"))
    db.create(TaskCreate(title="T2", project="proj-b"))
    results = db.list_tasks(project="proj-a")
    assert len(results) == 1
    assert results[0].project == "proj-a"


def test_list_filter_status(db):
    task = db.create(TaskCreate(title="T", project="p"))
    db.update(task.id, TaskUpdate(status="done"))
    assert len(db.list_tasks(status="todo")) == 0
    assert len(db.list_tasks(status="done")) == 1


def test_list_filter_priority(db):
    db.create(TaskCreate(title="High", project="p", priority="P1"))
    db.create(TaskCreate(title="Low", project="p", priority="P3"))
    results = db.list_tasks(priority="P1")
    assert len(results) == 1
    assert results[0].title == "High"


def test_update_status(db):
    task = db.create(TaskCreate(title="T", project="p"))
    updated = db.update(task.id, TaskUpdate(status="done"))
    assert updated.status == "done"


def test_update_missing_task(db):
    assert db.update(999, TaskUpdate(status="done")) is None


def test_delete_task(db):
    task = db.create(TaskCreate(title="T", project="p"))
    assert db.delete(task.id) is True
    assert db.get(task.id) is None


def test_delete_missing_task(db):
    assert db.delete(999) is False


def test_projects(db):
    db.create(TaskCreate(title="T1", project="proj-a"))
    db.create(TaskCreate(title="T2", project="proj-b"))
    db.create(TaskCreate(title="T3", project="proj-a"))
    assert db.projects() == ["proj-a", "proj-b"]


def test_get_db_path_env_var(monkeypatch, tmp_path):
    from todo.db import get_db_path
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "custom.db"))
    assert get_db_path() == tmp_path / "custom.db"


def test_get_db_path_config_file(monkeypatch, tmp_path):
    import json
    from todo.db import get_db_path
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    # Write a config.json in a fake home dir
    config_dir = tmp_path / ".local" / "share" / "todo"
    config_dir.mkdir(parents=True)
    config_path = config_dir / "config.json"
    config_path.write_text(json.dumps({"db_path": str(tmp_path / "from_config.db")}))
    monkeypatch.setattr("todo.db.Path.home", lambda: tmp_path)
    assert get_db_path() == tmp_path / "from_config.db"


def test_get_db_path_default(monkeypatch, tmp_path):
    from todo.db import get_db_path
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.setattr("todo.db.Path.home", lambda: tmp_path)
    expected = tmp_path / ".local" / "share" / "todo" / "tasks.db"
    assert get_db_path() == expected

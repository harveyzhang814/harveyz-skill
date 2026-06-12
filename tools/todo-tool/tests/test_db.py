import pytest
from todo.db import TodoDB
from todo.models import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate


@pytest.fixture
def db(tmp_path):
    return TodoDB(db_path=tmp_path / "test.db")


@pytest.fixture
def project(db):
    return db.create_project(ProjectCreate(repo_name="myapp"))


@pytest.fixture
def proj_a(db):
    return db.create_project(ProjectCreate(repo_name="proj-a"))


@pytest.fixture
def proj_b(db):
    return db.create_project(ProjectCreate(repo_name="proj-b"))


# ── Task tests ────────────────────────────────────────────────────────────────

def test_create_task(db, project):
    task = db.create(TaskCreate(title="Fix bug", project="myapp"))
    assert task.id == 1
    assert task.title == "Fix bug"
    assert task.project == "myapp"
    assert task.priority == "P2"
    assert task.status == "todo"


def test_create_task_custom_priority(db, project):
    task = db.create(TaskCreate(title="Urgent", project="myapp", priority="P0"))
    assert task.priority == "P0"


def test_create_task_unknown_project_raises(db):
    with pytest.raises(ValueError, match="not found"):
        db.create(TaskCreate(title="T", project="nope"))


def test_get_task(db, project):
    created = db.create(TaskCreate(title="T", project="myapp"))
    fetched = db.get(created.id)
    assert fetched.title == "T"
    assert fetched.project == "myapp"


def test_get_missing_task(db):
    assert db.get(999) is None


def test_list_all(db, proj_a, proj_b):
    db.create(TaskCreate(title="T1", project="proj-a"))
    db.create(TaskCreate(title="T2", project="proj-b"))
    assert len(db.list_tasks()) == 2


def test_list_filter_project(db, proj_a, proj_b):
    db.create(TaskCreate(title="T1", project="proj-a"))
    db.create(TaskCreate(title="T2", project="proj-b"))
    results = db.list_tasks(project="proj-a")
    assert len(results) == 1
    assert results[0].project == "proj-a"


def test_list_filter_status(db, project):
    task = db.create(TaskCreate(title="T", project="myapp"))
    db.update(task.id, TaskUpdate(status="done"))
    assert len(db.list_tasks(status="todo")) == 0
    assert len(db.list_tasks(status="done")) == 1


def test_list_filter_priority(db, project):
    db.create(TaskCreate(title="High", project="myapp", priority="P1"))
    db.create(TaskCreate(title="Low", project="myapp", priority="P3"))
    results = db.list_tasks(priority="P1")
    assert len(results) == 1
    assert results[0].title == "High"


def test_update_status(db, project):
    task = db.create(TaskCreate(title="T", project="myapp"))
    updated = db.update(task.id, TaskUpdate(status="done"))
    assert updated.status == "done"


def test_update_missing_task(db):
    assert db.update(999, TaskUpdate(status="done")) is None


def test_delete_task(db, project):
    task = db.create(TaskCreate(title="T", project="myapp"))
    assert db.delete(task.id) is True
    assert db.get(task.id) is None


def test_delete_missing_task(db):
    assert db.delete(999) is False


def test_projects_returns_project_objects(db, proj_a, proj_b):
    projects = db.projects()
    assert len(projects) == 2
    assert all(hasattr(p, "repo_name") for p in projects)


# ── Project tests ─────────────────────────────────────────────────────────────

def test_create_project(db):
    p = db.create_project(ProjectCreate(repo_name="myapp"))
    assert p.id == 1
    assert p.repo_name == "myapp"
    assert p.local_path is None
    assert p.created_at


def test_create_project_with_path(db):
    p = db.create_project(ProjectCreate(repo_name="myapp", local_path="/home/user/myapp"))
    assert p.local_path == "/home/user/myapp"


def test_create_project_duplicate_raises(db):
    db.create_project(ProjectCreate(repo_name="myapp"))
    with pytest.raises(Exception):
        db.create_project(ProjectCreate(repo_name="myapp"))


def test_get_project(db):
    created = db.create_project(ProjectCreate(repo_name="myapp"))
    fetched = db.get_project(created.id)
    assert fetched.repo_name == "myapp"


def test_get_project_missing(db):
    assert db.get_project(999) is None


def test_get_project_by_name(db):
    db.create_project(ProjectCreate(repo_name="myapp"))
    p = db.get_project_by_name("myapp")
    assert p is not None
    assert p.repo_name == "myapp"


def test_get_project_by_name_missing(db):
    assert db.get_project_by_name("nope") is None


def test_list_projects(db):
    db.create_project(ProjectCreate(repo_name="beta"))
    db.create_project(ProjectCreate(repo_name="alpha"))
    names = [p.repo_name for p in db.list_projects()]
    assert names == ["alpha", "beta"]


def test_update_project_path(db):
    p = db.create_project(ProjectCreate(repo_name="myapp"))
    updated = db.update_project(p.id, ProjectUpdate(local_path="/new/path"))
    assert updated.local_path == "/new/path"


def test_update_project_missing(db):
    assert db.update_project(999, ProjectUpdate(local_path="/x")) is None


def test_delete_project(db):
    p = db.create_project(ProjectCreate(repo_name="myapp"))
    assert db.delete_project(p.id) is True
    assert db.get_project(p.id) is None


def test_delete_project_missing(db):
    assert db.delete_project(999) is False


def test_delete_project_with_tasks_raises(db):
    p = db.create_project(ProjectCreate(repo_name="myapp"))
    db.create(TaskCreate(title="T", project="myapp"))
    with pytest.raises(ValueError, match="task"):
        db.delete_project(p.id)


# ── get_db_path tests ─────────────────────────────────────────────────────────

def test_get_db_path_env_var(monkeypatch, tmp_path):
    from todo.db import get_db_path
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "custom.db"))
    assert get_db_path() == tmp_path / "custom.db"


def test_get_db_path_config_file(monkeypatch, tmp_path):
    import json
    from todo.db import get_db_path
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    config_dir = tmp_path / ".local" / "share" / "todo"
    config_dir.mkdir(parents=True)
    (config_dir / "config.json").write_text(
        json.dumps({"db_path": str(tmp_path / "from_config.db")})
    )
    monkeypatch.setattr("todo.db.Path.home", lambda: tmp_path)
    assert get_db_path() == tmp_path / "from_config.db"


def test_get_db_path_default(monkeypatch, tmp_path):
    from todo.db import get_db_path
    monkeypatch.delenv("TODO_DB_PATH", raising=False)
    monkeypatch.setattr("todo.db.Path.home", lambda: tmp_path)
    assert get_db_path() == tmp_path / ".local" / "share" / "todo" / "tasks.db"

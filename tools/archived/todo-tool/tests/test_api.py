import pytest
from fastapi.testclient import TestClient
from todo.db import TodoDB
from todo.projects_index import save_project
from todo.server import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "PROJECTS.md"))
    db = TodoDB(db_path=tmp_path / "test.db")
    return TestClient(create_app(db=db))


def _add_project(client, name: str, path: str = None):
    body = {"repo_name": name}
    if path:
        body["local_path"] = path
    r = client.post("/api/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def _register_in_index(name: str, path: str, description: str = ""):
    """Write project to PROJECTS.md so the server lazy sync picks it up."""
    save_project(name, path, description)


# ── Project endpoint tests ────────────────────────────────────────────────────

def test_create_project(client):
    r = client.post("/api/projects", json={"repo_name": "myapp"})
    assert r.status_code == 201
    data = r.json()
    assert data["repo_name"] == "myapp"
    assert data["local_path"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_project_with_path(client):
    r = client.post("/api/projects", json={"repo_name": "myapp", "local_path": "/home/user/myapp"})
    assert r.status_code == 201
    assert r.json()["local_path"] == "/home/user/myapp"


def test_list_projects_returns_objects(client):
    _add_project(client, "alpha")
    _add_project(client, "beta")
    r = client.get("/api/projects")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all("repo_name" in p for p in data)
    assert sorted(p["repo_name"] for p in data) == ["alpha", "beta"]


def test_update_project(client):
    p = _add_project(client, "myapp")
    r = client.patch(f"/api/projects/{p['id']}", json={"local_path": "/new/path"})
    assert r.status_code == 200
    assert r.json()["local_path"] == "/new/path"


def test_update_project_missing(client):
    r = client.patch("/api/projects/999", json={"local_path": "/x"})
    assert r.status_code == 404


def test_delete_project(client):
    p = _add_project(client, "myapp")
    r = client.delete(f"/api/projects/{p['id']}")
    assert r.status_code == 204
    assert client.get("/api/projects").json() == []


def test_delete_project_missing(client):
    r = client.delete("/api/projects/999")
    assert r.status_code == 404


def test_delete_project_with_tasks_returns_409(client):
    _add_project(client, "myapp")
    client.post("/api/tasks", json={"title": "T", "project": "myapp"})
    p = client.get("/api/projects").json()[0]
    r = client.delete(f"/api/projects/{p['id']}")
    assert r.status_code == 409


# ── Task endpoint tests ───────────────────────────────────────────────────────

def test_create_task(client):
    _add_project(client, "myapp")
    r = client.post("/api/tasks", json={"title": "Test", "project": "myapp"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test"
    assert data["project"] == "myapp"
    assert data["priority"] == "P2"
    assert data["status"] == "todo"


def test_create_task_unknown_project_returns_422(client):
    r = client.post("/api/tasks", json={"title": "T", "project": "nope"})
    assert r.status_code == 422


def test_list_tasks(client):
    _add_project(client, "myapp")
    client.post("/api/tasks", json={"title": "T1", "project": "myapp"})
    client.post("/api/tasks", json={"title": "T2", "project": "myapp"})
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_tasks_filter_project(client):
    _add_project(client, "proj-a")
    _add_project(client, "proj-b")
    client.post("/api/tasks", json={"title": "T1", "project": "proj-a"})
    client.post("/api/tasks", json={"title": "T2", "project": "proj-b"})
    r = client.get("/api/tasks?project=proj-a")
    assert len(r.json()) == 1


def test_list_tasks_filter_status(client):
    _add_project(client, "p")
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert len(client.get("/api/tasks?status=todo").json()) == 0
    assert len(client.get("/api/tasks?status=done").json()) == 1


def test_update_task(client):
    _add_project(client, "p")
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    r = client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_update_missing_task(client):
    r = client.patch("/api/tasks/999", json={"status": "done"})
    assert r.status_code == 404


def test_delete_task(client):
    _add_project(client, "p")
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 204


def test_delete_missing_task(client):
    r = client.delete("/api/tasks/999")
    assert r.status_code == 404


def test_list_tasks_filter_priority(client):
    _add_project(client, "p")
    client.post("/api/tasks", json={"title": "High", "project": "p", "priority": "P1"})
    client.post("/api/tasks", json={"title": "Low", "project": "p", "priority": "P3"})
    r = client.get("/api/tasks?priority=P1")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "High"


def test_list_tasks_lazy_sync(client, tmp_path):
    todo_md = tmp_path / "TODO.md"
    todo_md.write_text(
        "# TODO\n\n## 🚧 待开发\n\n### 自动同步任务\n**优先级**: P2 | **日期**: 2026-01-01\n\n描述内容\n\n---\n\n## ✅ 已完成\n",
        encoding="utf-8",
    )
    _register_in_index("lazy-proj", str(tmp_path))

    r = client.get("/api/tasks")
    assert r.status_code == 200
    tasks = r.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "自动同步任务"
    assert tasks[0]["priority"] == "P2"
    assert "**ID**:" in todo_md.read_text(encoding="utf-8")
    proj = next(p for p in client.get("/api/projects").json() if p["repo_name"] == "lazy-proj")
    assert proj["last_synced_at"] is not None


def test_list_tasks_lazy_sync_idempotent(client, tmp_path):
    todo_md = tmp_path / "TODO.md"
    todo_md.write_text(
        "# TODO\n\n## 🚧 待开发\n\n### 幂等测试任务\n**优先级**: P1 | **日期**: 2026-01-01\n\n描述\n\n---\n\n## ✅ 已完成\n",
        encoding="utf-8",
    )
    _register_in_index("idem-proj", str(tmp_path))

    client.get("/api/tasks")  # first sync
    client.get("/api/tasks")  # second sync — should not duplicate
    r = client.get("/api/tasks")
    assert len(r.json()) == 1


def test_list_tasks_lazy_sync_skips_missing_todo(client, tmp_path):
    _register_in_index("no-todo-proj", str(tmp_path))
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert r.json() == []


def test_list_tasks_lazy_sync_skips_unchanged_file(client, tmp_path):
    import os
    todo_md = tmp_path / "TODO.md"
    todo_md.write_text(
        "# TODO\n\n## 🚧 待开发\n\n### 初始任务\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n\n## ✅ 已完成\n",
        encoding="utf-8",
    )
    _register_in_index("skip-proj", str(tmp_path))
    client.get("/api/tasks")  # first sync — inserts task, records mtime

    proj = next(p for p in client.get("/api/projects").json() if p["repo_name"] == "skip-proj")
    synced_at = proj["last_synced_at"]
    content = todo_md.read_text(encoding="utf-8")
    todo_md.write_text(
        content.replace("## ✅ 已完成", "### 不应出现的任务\n**优先级**: P3 | **日期**: 2026-01-02\n\n---\n\n## ✅ 已完成"),
        encoding="utf-8",
    )
    os.utime(todo_md, (synced_at - 1, synced_at - 1))  # backdate to before last sync

    r = client.get("/api/tasks")
    assert len(r.json()) == 1  # second task skipped because mtime < last_synced_at

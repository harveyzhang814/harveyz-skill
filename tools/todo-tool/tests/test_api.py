import pytest
from fastapi.testclient import TestClient
from todo.db import TodoDB
from todo.server import create_app


@pytest.fixture
def client(tmp_path):
    db = TodoDB(db_path=tmp_path / "test.db")
    return TestClient(create_app(db=db))


def test_create_task(client):
    r = client.post("/api/tasks", json={"title": "Test", "project": "myapp"})
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Test"
    assert data["project"] == "myapp"
    assert data["priority"] == "P2"
    assert data["status"] == "todo"


def test_list_tasks(client):
    client.post("/api/tasks", json={"title": "T1", "project": "myapp"})
    client.post("/api/tasks", json={"title": "T2", "project": "myapp"})
    r = client.get("/api/tasks")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_tasks_filter_project(client):
    client.post("/api/tasks", json={"title": "T1", "project": "proj-a"})
    client.post("/api/tasks", json={"title": "T2", "project": "proj-b"})
    r = client.get("/api/tasks?project=proj-a")
    assert len(r.json()) == 1


def test_list_tasks_filter_status(client):
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert len(client.get("/api/tasks?status=todo").json()) == 0
    assert len(client.get("/api/tasks?status=done").json()) == 1


def test_update_task(client):
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    r = client.patch(f"/api/tasks/{task['id']}", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_update_missing_task(client):
    r = client.patch("/api/tasks/999", json={"status": "done"})
    assert r.status_code == 404


def test_delete_task(client):
    task = client.post("/api/tasks", json={"title": "T", "project": "p"}).json()
    r = client.delete(f"/api/tasks/{task['id']}")
    assert r.status_code == 204


def test_delete_missing_task(client):
    r = client.delete("/api/tasks/999")
    assert r.status_code == 404


def test_list_projects(client):
    client.post("/api/tasks", json={"title": "T1", "project": "proj-a"})
    client.post("/api/tasks", json={"title": "T2", "project": "proj-b"})
    client.post("/api/tasks", json={"title": "T3", "project": "proj-a"})
    r = client.get("/api/projects")
    assert r.status_code == 200
    assert set(r.json()) == {"proj-a", "proj-b"}

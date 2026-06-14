import json
import os
import pytest
from typer.testing import CliRunner
from hub.cli import app


runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    monkeypatch.setenv("HUB_MD_PATH", str(tmp_path / "PROJECTS.md"))


def test_projects_list_empty_json():
    result = runner.invoke(app, ["projects", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data == {"ok": True, "data": []}


def test_projects_add_and_list_json():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    result = runner.invoke(app, ["projects", "list", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert any(p["name"] == "blog" for p in data["data"])


def test_projects_path_found():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    result = runner.invoke(app, ["projects", "path", "blog", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"] == "/tmp/blog"


def test_projects_path_not_found():
    result = runner.invoke(app, ["projects", "path", "nope", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is False
    assert "not found" in data["error"]


def test_tasks_add_and_list_json():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    runner.invoke(app, ["tasks", "add", "Write post", "--project", "blog"])
    result = runner.invoke(app, ["tasks", "list", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert any(t["title"] == "Write post" for t in data["data"])


def test_tasks_add_unknown_project_error():
    result = runner.invoke(app, ["tasks", "add", "x", "--project", "nope", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is False
    assert "not found" in data["error"]


def test_tasks_done_json():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    runner.invoke(app, ["tasks", "add", "Write post", "--project", "blog"])
    list_result = runner.invoke(app, ["tasks", "list", "--json"])
    task_id = json.loads(list_result.output)["data"][0]["id"]
    result = runner.invoke(app, ["tasks", "done", str(task_id), "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"]["status"] == "done"


def test_tasks_rm_json():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    runner.invoke(app, ["tasks", "add", "Write post", "--project", "blog"])
    list_result = runner.invoke(app, ["tasks", "list", "--json"])
    task_id = json.loads(list_result.output)["data"][0]["id"]
    result = runner.invoke(app, ["tasks", "rm", str(task_id), "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert data["data"] == {"deleted": True}


def test_tasks_list_filter_status_json():
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    runner.invoke(app, ["tasks", "add", "A", "--project", "blog"])
    list_result = runner.invoke(app, ["tasks", "list", "--json"])
    task_id = json.loads(list_result.output)["data"][0]["id"]
    runner.invoke(app, ["tasks", "done", str(task_id)])
    result = runner.invoke(app, ["tasks", "list", "--status", "todo", "--json"])
    data = json.loads(result.output)
    assert data["data"] == []

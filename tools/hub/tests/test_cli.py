import json
import os
from pathlib import Path
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


# --- git pull / git push ---

def _br(name="main", upstream="origin/main", ahead=0, behind=0,
        is_current=True, is_local_only=False):
    return {"name": name, "upstream": upstream, "ahead": ahead, "behind": behind,
            "is_current": is_current, "is_local_only": is_local_only}


def test_git_pull_not_a_git_repo(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "not a git repository" in result.output


def test_git_pull_branch_not_found(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br()])
    result = runner.invoke(app, ["git", "pull", "--branch", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_git_pull_local_only(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(upstream="", is_local_only=True)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "no upstream" in result.output


def test_git_pull_diverged(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=1)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "diverged" in result.output


def test_git_pull_already_up_to_date(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(behind=0, ahead=0)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_git_pull_success(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(behind=1, ahead=0)])
    monkeypatch.setattr("hub.cli.git.pull_branch", lambda p, b: f"✓ pulled {b}")
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code == 0
    assert "✓ pulled main" in result.output


def test_git_push_not_a_git_repo(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "not a git repository" in result.output


def test_git_push_branch_not_found(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br()])
    result = runner.invoke(app, ["git", "push", "--branch", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_git_push_local_only(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(upstream="", is_local_only=True)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "no upstream" in result.output


def test_git_push_diverged(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=1)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "diverged" in result.output


def test_git_push_already_up_to_date(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=0, behind=0)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_git_push_success(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=0)])
    monkeypatch.setattr("hub.cli.git.push_branch", lambda p, b: f"✓ pushed {b}")
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code == 0
    assert "✓ pushed main" in result.output

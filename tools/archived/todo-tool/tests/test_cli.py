import json
import pytest
from typer.testing import CliRunner
from todo.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "PROJECTS.md"))


def _add_project(name: str, path: str = None):
    args = ["project", "add", name]
    if path:
        args += ["--path", path]
    return runner.invoke(app, args)


# ── Project command tests ─────────────────────────────────────────────────────

def test_project_add():
    result = _add_project("myapp")
    assert result.exit_code == 0
    assert "myapp" in result.output


def test_project_add_with_path():
    result = _add_project("myapp", path="/home/user/myapp")
    assert result.exit_code == 0
    assert "myapp" in result.output


def test_project_list():
    _add_project("alpha", path="/path/alpha")
    _add_project("beta", path="/path/beta")
    result = runner.invoke(app, ["project", "list"])
    assert result.exit_code == 0
    assert "alpha" in result.output
    assert "beta" in result.output


def test_project_set_path():
    _add_project("myapp")
    result = runner.invoke(app, ["project", "set-path", "myapp", "/new/path"])
    assert result.exit_code == 0
    assert "/new/path" in result.output


def test_project_set_path_unknown():
    result = runner.invoke(app, ["project", "set-path", "nope", "/x"])
    assert result.exit_code == 1


# ── Task command tests ────────────────────────────────────────────────────────

def test_add_command():
    _add_project("myapp")
    result = runner.invoke(app, ["add", "My task", "--project", "myapp"])
    assert result.exit_code == 0
    assert "My task" in result.output


def test_add_command_unknown_project_fails():
    result = runner.invoke(app, ["add", "My task", "--project", "nope"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_add_command_with_priority():
    _add_project("myapp")
    result = runner.invoke(app, ["add", "Urgent", "--project", "myapp", "--priority", "P0"])
    assert result.exit_code == 0
    assert "Urgent" in result.output


def test_list_command():
    _add_project("myapp")
    _add_project("other")
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    runner.invoke(app, ["add", "Task 2", "--project", "other"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output


def test_list_filter_project():
    _add_project("myapp")
    _add_project("other")
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    runner.invoke(app, ["add", "Task 2", "--project", "other"])
    result = runner.invoke(app, ["list", "--project", "myapp"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" not in result.output


def test_list_json():
    _add_project("myapp")
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    tasks = json.loads(result.output)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task 1"


def test_done_command():
    _add_project("myapp")
    runner.invoke(app, ["add", "Task", "--project", "myapp"])
    result = runner.invoke(app, ["done", "1"])
    assert result.exit_code == 0
    assert "marked done" in result.output


def test_done_missing_task():
    result = runner.invoke(app, ["done", "999"])
    assert result.exit_code == 1


def test_show_command():
    _add_project("myapp")
    runner.invoke(app, ["add", "My task", "--project", "myapp"])
    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0
    assert "My task" in result.output
    assert "myapp" in result.output


def test_show_missing_task():
    result = runner.invoke(app, ["show", "999"])
    assert result.exit_code == 1


def test_list_done_flag():
    _add_project("myapp")
    runner.invoke(app, ["add", "Task A", "--project", "myapp"])
    runner.invoke(app, ["done", "1"])
    assert "Task A" not in runner.invoke(app, ["list"]).output
    assert "Task A" in runner.invoke(app, ["list", "--done"]).output


def test_list_priority_filter():
    _add_project("myapp")
    runner.invoke(app, ["add", "High task", "--project", "myapp", "--priority", "P1"])
    runner.invoke(app, ["add", "Low task", "--project", "myapp", "--priority", "P3"])
    result = runner.invoke(app, ["list", "--priority", "P1"])
    assert result.exit_code == 0
    assert "High task" in result.output
    assert "Low task" not in result.output


def test_config_set_and_show(tmp_path, monkeypatch):
    import pathlib
    monkeypatch.setattr("todo.cli.Path", type(
        "FakePath", (pathlib.Path,), {"home": staticmethod(lambda: tmp_path)}
    ))
    new_db = str(tmp_path / "mydb.db")
    result = runner.invoke(app, ["config", "set", "db-path", new_db])
    assert result.exit_code == 0
    assert "db-path set to" in result.output
    result2 = runner.invoke(app, ["config", "show"])
    assert result2.exit_code == 0
    assert "mydb.db" in result2.output


_TODO_CONTENT = (
    "# TODO / Backlog\n\n"
    "## 🚧 待开发\n\n"
    "### Sync 测试任务\n"
    "**优先级**: P1 | **日期**: 2026-06-12\n\n"
    "---\n\n"
    "## ✅ 已完成\n"
)


def test_sync_command_inserts_and_echoes(tmp_path):
    runner.invoke(app, ["project", "add", "sync-proj", "--path", str(tmp_path)])
    (tmp_path / "TODO.md").write_text(_TODO_CONTENT, encoding="utf-8")
    result = runner.invoke(app, ["sync", "sync-proj"])
    assert result.exit_code == 0
    assert "1 条新增" in result.output
    assert "0 条更新" in result.output


def test_sync_command_project_not_found():
    result = runner.invoke(app, ["sync", "nonexistent-xyz"])
    assert result.exit_code == 1


def test_sync_command_no_todo_md(tmp_path):
    runner.invoke(app, ["project", "add", "no-file-proj", "--path", str(tmp_path)])
    result = runner.invoke(app, ["sync", "no-file-proj"])
    assert result.exit_code == 1
    assert "TODO.md not found" in result.output


def test_sync_command_path_override(tmp_path):
    runner.invoke(app, ["project", "add", "path-proj"])  # no local_path
    (tmp_path / "TODO.md").write_text(
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### Path override 任务\n"
        "**优先级**: P2 | **日期**: 2026-06-12\n\n"
        "---\n\n"
        "## ✅ 已完成\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["sync", "path-proj", "--path", str(tmp_path)])
    assert result.exit_code == 0
    assert "1 条新增" in result.output

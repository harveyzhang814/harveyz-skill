import json
import pytest
from typer.testing import CliRunner
from todo.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "test.db"))


def test_add_command():
    result = runner.invoke(app, ["add", "My task", "--project", "myapp"])
    assert result.exit_code == 0
    assert "My task" in result.output


def test_add_command_with_priority():
    result = runner.invoke(app, ["add", "Urgent", "--project", "myapp", "--priority", "P0"])
    assert result.exit_code == 0
    assert "Urgent" in result.output


def test_list_command():
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    runner.invoke(app, ["add", "Task 2", "--project", "other"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" in result.output


def test_list_filter_project():
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    runner.invoke(app, ["add", "Task 2", "--project", "other"])
    result = runner.invoke(app, ["list", "--project", "myapp"])
    assert result.exit_code == 0
    assert "Task 1" in result.output
    assert "Task 2" not in result.output


def test_list_json():
    runner.invoke(app, ["add", "Task 1", "--project", "myapp"])
    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    tasks = json.loads(result.output)
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Task 1"


def test_done_command():
    runner.invoke(app, ["add", "Task", "--project", "myapp"])
    result = runner.invoke(app, ["done", "1"])
    assert result.exit_code == 0
    assert "marked done" in result.output


def test_done_missing_task():
    result = runner.invoke(app, ["done", "999"])
    assert result.exit_code == 1


def test_show_command():
    runner.invoke(app, ["add", "My task", "--project", "myapp"])
    result = runner.invoke(app, ["show", "1"])
    assert result.exit_code == 0
    assert "My task" in result.output
    assert "myapp" in result.output

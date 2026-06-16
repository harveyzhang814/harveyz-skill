import pytest
from pathlib import Path
from todo.db import TodoDB
from todo.models import ProjectCreate, TaskCreate


@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_DB_PATH", str(tmp_path / "tasks.db"))
    return TodoDB()


@pytest.fixture
def project(db, tmp_path):
    return db.create_project(ProjectCreate(repo_name="test-proj", local_path=str(tmp_path)))


def _write_todo(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "TODO.md"
    p.write_text(content, encoding="utf-8")
    return p


def test_sync_inserts_new_task(tmp_path, db, project):
    p = _write_todo(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 新任务标题\n"
        "**优先级**: P2 | **日期**: 2026-06-12\n\n"
        "任务描述。\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    inserted, updated = db.sync_from_file(p, project.id)
    assert inserted == 1
    assert updated == 0
    tasks = db.list_tasks(project="test-proj")
    assert len(tasks) == 1
    assert tasks[0].title == "新任务标题"
    assert tasks[0].priority == "P2"
    assert tasks[0].status == "todo"


def test_sync_writes_id_back_to_file(tmp_path, db, project):
    p = _write_todo(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### ID 写回测试\n"
        "**优先级**: P1 | **日期**: 2026-06-12\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    db.sync_from_file(p, project.id)
    assert "| **ID**:" in p.read_text(encoding="utf-8")


def test_sync_updates_existing_task(tmp_path, db, project):
    task = db.create(TaskCreate(title="旧标题", project="test-proj", priority="P2"))
    p = _write_todo(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 新标题\n"
        f"**优先级**: P1 | **日期**: 2026-06-12 | **ID**: {task.id}\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    inserted, updated = db.sync_from_file(p, project.id)
    assert inserted == 0
    assert updated == 1
    t = db.get(task.id)
    assert t.title == "新标题"
    assert t.priority == "P1"


def test_sync_done_task_updates_status(tmp_path, db, project):
    task = db.create(TaskCreate(title="完成的任务", project="test-proj", priority="P2"))
    p = _write_todo(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "## ✅ 已完成\n\n"
        "### 完成的任务\n"
        f"**优先级**: P2 | **日期**: 2026-06-12 | **ID**: {task.id}\n\n"
        "---\n"
    ))
    db.sync_from_file(p, project.id)
    assert db.get(task.id).status == "done"


def test_sync_no_writeback_when_all_have_ids(tmp_path, db, project):
    task = db.create(TaskCreate(title="已有 ID 的任务", project="test-proj", priority="P2"))
    original = (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 已有 ID 的任务\n"
        f"**优先级**: P2 | **日期**: 2026-06-12 | **ID**: {task.id}\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    )
    p = _write_todo(tmp_path, original)
    db.sync_from_file(p, project.id)
    assert p.read_text(encoding="utf-8") == original

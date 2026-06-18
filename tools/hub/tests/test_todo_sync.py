import pytest
from pathlib import Path
from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import list_tasks
from hub.core.todo_sync import parse_todo_md, sync_project, sync_all_projects


TODO_FORMAT1 = """\
# TODO / Backlog

## 🚧 待开发

### 任务 A
**优先级**: P1 | **日期**: 2026-06-14

Description of A.

---

### 任务 B
**优先级**: P3 | **日期**: 2026-06-15

---

## ✅ 已完成

### 任务 C
**优先级**: P2 | **日期**: 2026-06-13

---
"""

TODO_FORMAT2 = """\
## hub — Phase 3

### [ ] Task with checkbox
**优先级**: P2 | **日期**: 2026-06-10

---

### [x] Completed checkbox task
**优先级**: P1 | **日期**: 2026-06-11

---
"""

TODO_NO_METADATA = """\
## 🚧 待开发

### Simple task with no priority or date

---
"""


def test_parse_format1_todo_status(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT1)
    tasks = parse_todo_md(f)
    todo_tasks = [t for t in tasks if t["status"] == "todo"]
    assert len(todo_tasks) == 2
    titles = {t["title"] for t in todo_tasks}
    assert "任务 A" in titles
    assert "任务 B" in titles


def test_parse_format1_done_status(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT1)
    tasks = parse_todo_md(f)
    done_tasks = [t for t in tasks if t["status"] == "done"]
    assert len(done_tasks) == 1
    assert done_tasks[0]["title"] == "任务 C"


def test_parse_format1_priority(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT1)
    tasks = parse_todo_md(f)
    a = next(t for t in tasks if t["title"] == "任务 A")
    assert a["priority"] == "P1"
    b = next(t for t in tasks if t["title"] == "任务 B")
    assert b["priority"] == "P3"


def test_parse_format1_created_at(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT1)
    tasks = parse_todo_md(f)
    a = next(t for t in tasks if t["title"] == "任务 A")
    assert a["created_at"].startswith("2026-06-14")


def test_parse_format2_checkbox_todo(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT2)
    tasks = parse_todo_md(f)
    todo = next(t for t in tasks if "checkbox" in t["title"] and "Completed" not in t["title"])
    assert todo["status"] == "todo"


def test_parse_format2_checkbox_done(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_FORMAT2)
    tasks = parse_todo_md(f)
    done = next(t for t in tasks if "Completed" in t["title"])
    assert done["status"] == "done"


def test_parse_no_metadata_defaults(tmp_path):
    f = tmp_path / "TODO.md"
    f.write_text(TODO_NO_METADATA)
    tasks = parse_todo_md(f)
    assert len(tasks) == 1
    t = tasks[0]
    assert t["title"] == "Simple task with no priority or date"
    assert t["priority"] == "P2"
    assert t["status"] == "todo"
    assert t["created_at"] is not None


def test_parse_missing_file_returns_empty(tmp_path):
    tasks = parse_todo_md(tmp_path / "MISSING.md")
    assert tasks == []


@pytest.fixture
def db(tmp_path):
    d = HubDB(db_path=tmp_path / "hub.db")
    add_project(d, "myproject", path=str(tmp_path / "myproject"),
                md_path=tmp_path / "PROJECTS.md")
    (tmp_path / "myproject").mkdir()
    return d, tmp_path


def test_sync_project_imports_new_tasks(db):
    d, tmp_path = db
    (tmp_path / "myproject" / "TODO.md").write_text(
        "## 🚧 待开发\n\n### My task\n**优先级**: P1 | **日期**: 2026-01-01\n\n---\n"
    )
    result = sync_project(d, "myproject", str(tmp_path / "myproject"))
    assert result["imported"] == 1
    assert result["updated"] == 0
    tasks = list_tasks(d, project="myproject")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "My task"
    assert tasks[0]["priority"] == "P1"
    assert tasks[0]["status"] == "todo"


def test_sync_project_updates_existing_task(db):
    d, tmp_path = db
    # First import
    (tmp_path / "myproject" / "TODO.md").write_text(
        "## 🚧 待开发\n\n### My task\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )
    sync_project(d, "myproject", str(tmp_path / "myproject"))
    # Update TODO.md: mark done and change priority
    (tmp_path / "myproject" / "TODO.md").write_text(
        "## ✅ 已完成\n\n### My task\n**优先级**: P1 | **日期**: 2026-01-01\n\n---\n"
    )
    result = sync_project(d, "myproject", str(tmp_path / "myproject"))
    assert result["updated"] == 1
    assert result["imported"] == 0
    tasks = list_tasks(d, project="myproject")
    assert tasks[0]["status"] == "done"
    assert tasks[0]["priority"] == "P1"


def test_sync_project_missing_todo_md(db):
    d, tmp_path = db
    result = sync_project(d, "myproject", str(tmp_path / "myproject"))
    assert result == {"imported": 0, "updated": 0}


def test_sync_project_sqlite_only_task_preserved(db):
    """Tasks added via TUI (not in TODO.md) must not be removed."""
    from hub.core.tasks import add_task
    d, tmp_path = db
    add_task(d, title="TUI-only task", project="myproject")
    (tmp_path / "myproject" / "TODO.md").write_text(
        "## 🚧 待开发\n\n### From file\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )
    sync_project(d, "myproject", str(tmp_path / "myproject"))
    tasks = list_tasks(d, project="myproject")
    titles = {t["title"] for t in tasks}
    assert "TUI-only task" in titles
    assert "From file" in titles


def test_sync_all_projects_aggregates(tmp_path):
    d = HubDB(db_path=tmp_path / "hub.db")
    proj_a = tmp_path / "proj_a"
    proj_b = tmp_path / "proj_b"
    proj_a.mkdir()
    proj_b.mkdir()
    add_project(d, "proj_a", path=str(proj_a), md_path=tmp_path / "PROJECTS.md")
    add_project(d, "proj_b", path=str(proj_b), md_path=tmp_path / "PROJECTS.md")
    (proj_a / "TODO.md").write_text(
        "## 🚧 待开发\n\n### Task A1\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )
    (proj_b / "TODO.md").write_text(
        "## 🚧 待开发\n\n### Task B1\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
        "### Task B2\n**优先级**: P1 | **日期**: 2026-01-02\n\n---\n"
    )
    result = sync_all_projects(d)
    assert result["imported"] == 3
    assert result["updated"] == 0


def test_sync_all_projects_skips_no_path(tmp_path):
    d = HubDB(db_path=tmp_path / "hub.db")
    add_project(d, "nopath", path="", md_path=tmp_path / "PROJECTS.md")
    result = sync_all_projects(d)
    assert result == {"imported": 0, "updated": 0}


def test_sync_all_projects_ignores_per_project_error(tmp_path):
    """A bad project path must not crash sync_all_projects."""
    d = HubDB(db_path=tmp_path / "hub.db")
    add_project(d, "ghost", path="/nonexistent/path/xyz",
                md_path=tmp_path / "PROJECTS.md")
    result = sync_all_projects(d)
    assert result == {"imported": 0, "updated": 0}


def test_sync_project_no_change_reports_zero_updated(db):
    d, tmp_path = db
    content = "## 🚧 待开发\n\n### My task\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    (tmp_path / "myproject" / "TODO.md").write_text(content)
    sync_project(d, "myproject", str(tmp_path / "myproject"))
    # Sync again with no changes
    result = sync_project(d, "myproject", str(tmp_path / "myproject"))
    assert result["updated"] == 0
    assert result["imported"] == 0


def test_sync_project_unknown_project_name_returns_zero(tmp_path):
    d = HubDB(db_path=tmp_path / "hub.db")
    result = sync_project(d, "does-not-exist", str(tmp_path))
    assert result == {"imported": 0, "updated": 0}

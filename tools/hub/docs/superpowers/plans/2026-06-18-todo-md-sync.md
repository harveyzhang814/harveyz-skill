# TODO.md → SQLite Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one-way sync from each project's `TODO.md` into the hub SQLite DB — triggered on startup (all projects) and via `ctrl+r` in the TUI (current project only).

**Architecture:** A new `hub/core/todo_sync.py` module parses TODO.md files and upserts tasks into SQLite. `hub/__main__.py` calls `sync_all_projects` before launching the TUI. `TasksPanel` gains a `ctrl+r` binding that calls `sync_project` for the active project.

**Tech Stack:** Python 3.11+, SQLite (via existing `HubDB`), `re` (stdlib), `pathlib` (stdlib), `pytest`, `pytest-asyncio`.

## Global Constraints

- Run tests with: `.venv/bin/pytest tests/ -q` from `tools/hub/`
- All new code lives under `tools/hub/hub/`
- Follow existing patterns: `db._conn()` for DB access, `sqlite3.Row` for results
- Priority values: `P1`, `P2`, `P3` — default `P2`
- Status values: `"todo"`, `"done"`
- `created_at` stored as ISO-8601 UTC string, e.g. `"2026-06-14T00:00:00+00:00"`
- Never raise from `sync_all_projects` — swallow per-project errors silently

---

### Task 1: TODO.md parser and sync core (`hub/core/todo_sync.py`)

**Files:**
- Create: `hub/core/todo_sync.py`
- Create: `tests/test_todo_sync.py`

**Interfaces:**
- Produces:
  - `parse_todo_md(path: Path) -> list[dict]`
    Each dict: `{"title": str, "status": str, "priority": str, "created_at": str}`
  - `sync_project(db: HubDB, name: str, path: str) -> dict`
    Returns `{"imported": int, "updated": int}`
  - `sync_all_projects(db: HubDB) -> dict`
    Returns `{"imported": int, "updated": int}`

---

- [ ] **Step 1: Write failing tests for `parse_todo_md`**

Create `tests/test_todo_sync.py`:

```python
import pytest
from pathlib import Path
from hub.core.todo_sync import parse_todo_md


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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tools/hub && .venv/bin/pytest tests/test_todo_sync.py -q
```

Expected: `ImportError` or `ModuleNotFoundError` (module doesn't exist yet).

- [ ] **Step 3: Implement `hub/core/todo_sync.py`**

Create `hub/core/todo_sync.py`:

```python
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from hub.core.db import HubDB
from hub.core.projects import list_projects


def parse_todo_md(path: Path) -> list[dict]:
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    tasks: list[dict] = []
    current_section_status = "todo"
    current_task: Optional[dict] = None

    for line in text.splitlines():
        if line.startswith("## "):
            if current_task is not None:
                tasks.append(current_task)
                current_task = None
            heading = line[3:].strip()
            if "已完成" in heading or "✅" in heading:
                current_section_status = "done"
            else:
                current_section_status = "todo"

        elif line.startswith("### "):
            if current_task is not None:
                tasks.append(current_task)
            raw = line[4:].strip()
            if raw.startswith("[ ] "):
                status = "todo"
                title = raw[4:]
            elif raw.startswith("[x] ") or raw.startswith("[X] "):
                status = "done"
                title = raw[4:]
            else:
                status = current_section_status
                title = raw
            current_task = {
                "title": title.strip(),
                "status": status,
                "priority": "P2",
                "created_at": None,
            }

        elif current_task is not None:
            m = re.search(r'\*\*优先级\*\*:\s*(P\d)', line)
            if m:
                current_task["priority"] = m.group(1)
            m = re.search(r'\*\*日期\*\*:\s*(\d{4}-\d{2}-\d{2})', line)
            if m:
                current_task["created_at"] = m.group(1) + "T00:00:00+00:00"
            if line.strip() == "---":
                tasks.append(current_task)
                current_task = None

    if current_task is not None:
        tasks.append(current_task)

    now = datetime.now(timezone.utc).isoformat()
    for t in tasks:
        if t["created_at"] is None:
            t["created_at"] = now

    return tasks


def sync_project(db: HubDB, name: str, path: str) -> dict:
    todo_path = Path(path) / "TODO.md"
    tasks = parse_todo_md(todo_path)
    if not tasks:
        return {"imported": 0, "updated": 0}

    with db._conn() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return {"imported": 0, "updated": 0}
        project_id = row["id"]

    imported = 0
    updated = 0
    for t in tasks:
        result = _upsert_task(
            db, project_id,
            title=t["title"],
            status=t["status"],
            priority=t["priority"],
            created_at=t["created_at"],
        )
        if result == "imported":
            imported += 1
        else:
            updated += 1

    return {"imported": imported, "updated": updated}


def sync_all_projects(db: HubDB) -> dict:
    projects = list_projects(db)
    total = {"imported": 0, "updated": 0}
    for p in projects:
        if not p.get("path"):
            continue
        try:
            result = sync_project(db, p["name"], p["path"])
            total["imported"] += result["imported"]
            total["updated"] += result["updated"]
        except Exception:
            pass
    return total


def _upsert_task(
    db: HubDB,
    project_id: int,
    title: str,
    status: str,
    priority: str,
    created_at: str,
) -> str:
    with db._conn() as conn:
        row = conn.execute(
            "SELECT id FROM tasks WHERE project_id = ? AND title = ?",
            (project_id, title),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE tasks SET status = ?, priority = ? WHERE id = ?",
                (status, priority, row["id"]),
            )
            return "updated"
        else:
            conn.execute(
                "INSERT INTO tasks (title, project_id, priority, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (title, project_id, priority, status, created_at),
            )
            return "imported"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd tools/hub && .venv/bin/pytest tests/test_todo_sync.py -q
```

Expected: `8 passed`.

- [ ] **Step 5: Add sync_project integration tests**

Append to `tests/test_todo_sync.py`:

```python
from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import list_tasks
from hub.core.todo_sync import sync_project, sync_all_projects


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
```

- [ ] **Step 6: Run all todo_sync tests**

```bash
cd tools/hub && .venv/bin/pytest tests/test_todo_sync.py -q
```

Expected: `16 passed`.

- [ ] **Step 7: Commit**

```bash
git add hub/core/todo_sync.py tests/test_todo_sync.py
git commit -m "feat(hub): add TODO.md parser and sync core"
```

---

### Task 2: Startup sync in `hub/__main__.py`

**Files:**
- Modify: `hub/__main__.py`
- Modify: `tests/test_cli.py` (add one smoke test)

**Interfaces:**
- Consumes: `sync_all_projects(db: HubDB) -> dict` from `hub.core.todo_sync`

---

- [ ] **Step 1: Add failing test for startup sync**

Append to `tests/test_cli.py`:

```python
def test_main_syncs_todo_md_on_startup(tmp_path, monkeypatch):
    """Tasks in a project's TODO.md appear in the DB after main() runs a CLI command."""
    import sys
    import hub.core.todo_sync as sync_mod

    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    monkeypatch.setattr(sys, "argv", ["hub", "projects", "list", "--json"])

    synced = []
    real_sync = sync_mod.sync_all_projects
    def tracking_sync(db):
        synced.append(True)
        return real_sync(db)
    monkeypatch.setattr(sync_mod, "sync_all_projects", tracking_sync)

    # Pre-populate DB and TODO.md before main() runs
    from hub.core.db import HubDB
    from hub.core.projects import add_project
    db = HubDB(db_path=tmp_path / "hub.db")
    proj_path = tmp_path / "myproj"
    proj_path.mkdir()
    add_project(db, "myproj", path=str(proj_path), md_path=tmp_path / "PROJECTS.md")
    (proj_path / "TODO.md").write_text(
        "## 🚧 待开发\n\n### Startup task\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )

    import hub.__main__ as main_mod
    main_mod.main()

    assert synced, "sync_all_projects was not called by main()"
    from hub.core.tasks import list_tasks
    tasks = list_tasks(db, project="myproj")
    assert any(t["title"] == "Startup task" for t in tasks)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tools/hub && .venv/bin/pytest tests/test_cli.py::test_main_syncs_todo_md_on_startup -q
```

Expected: FAIL — `AssertionError: sync_all_projects was not called by main()`.

- [ ] **Step 3: Update `hub/__main__.py`**

Replace the contents of `hub/__main__.py` with:

```python
import sys


def _get_db():
    from hub.core.db import HubDB
    return HubDB()


def main():
    from hub.core.migrate import needs_migration, run_migration
    from hub.core.todo_sync import sync_all_projects

    db = _get_db()

    if needs_migration():
        n = run_migration(db)
        if n:
            import typer
            typer.echo(f"hub: migrated {n} tasks from todo-tool ✓")

    try:
        sync_all_projects(db)
    except Exception:
        pass

    if len(sys.argv) == 1:
        from hub.tui.app import HubApp
        HubApp(db=db).run()
        return
    from hub.cli import app
    app()


if __name__ == "__main__":
    main()
```

> **Note:** `HubApp` currently constructs its own `HubDB` internally. Check `hub/tui/app.py` — if it accepts a `db` parameter, pass it; if not, leave `HubApp().run()` unchanged (the startup sync still runs, just on a separate `HubDB` instance pointing to the same file). In either case, the `sync_all_projects(db)` call before TUI launch is what matters here.

- [ ] **Step 4: Check `hub/tui/app.py` DB construction and adapt**

```bash
cd tools/hub && grep -n "HubDB\|def __init__" hub/tui/app.py | head -20
```

If `HubApp.__init__` takes no `db` parameter, revert `HubApp(db=db).run()` to `HubApp().run()` in step 3.

- [ ] **Step 5: Run the new test**

```bash
cd tools/hub && .venv/bin/pytest tests/test_cli.py::test_main_syncs_todo_md_on_startup -q
```

Expected: PASS.

- [ ] **Step 6: Run full test suite to check for regressions**

```bash
cd tools/hub && .venv/bin/pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add hub/__main__.py tests/test_cli.py
git commit -m "feat(hub): sync all project TODO.md files on startup"
```

---

### Task 3: `ctrl+r` manual refresh in `TasksPanel`

**Files:**
- Modify: `hub/tui/panels/tasks.py`
- Modify: `tests/test_tui_tasks_panel.py`

**Interfaces:**
- Consumes:
  - `get_project_path(db: HubDB, name: str) -> str | None` from `hub.core.projects`
  - `sync_project(db: HubDB, name: str, path: str) -> dict` from `hub.core.todo_sync`

---

- [ ] **Step 1: Write failing TUI test**

Append to `tests/test_tui_tasks_panel.py`:

```python
async def test_ctrl_r_syncs_from_todo_md(tmp_path):
    """ctrl+r reads TODO.md and imports tasks into the panel."""
    from hub.core.todo_sync import sync_project as _real_sync  # noqa: F401

    db = HubDB(tmp_path / "hub.db")
    proj_path = tmp_path / "myproj"
    proj_path.mkdir()
    add_project(db, "myproj", path=str(proj_path))

    todo_md = proj_path / "TODO.md"
    todo_md.write_text(
        "## 🚧 待开发\n\n### Synced task\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("myproj")
        await pilot.pause()
        panel.focus()
        await pilot.press("ctrl+r")
        await pilot.pause()

    tasks = list_tasks(db, project="myproj")
    assert any(t["title"] == "Synced task" for t in tasks)


async def test_ctrl_r_no_path_shows_warning(tmp_path):
    """ctrl+r on a project with no path shows a warning and does not crash."""
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "nopath", path="")

    notifications = []

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("nopath")
        await pilot.pause()
        panel.focus()

        original_notify = pilot.app.notify
        pilot.app.notify = lambda msg, **kw: notifications.append(msg)

        await pilot.press("ctrl+r")
        await pilot.pause()

    assert any("path" in n.lower() or "no" in n.lower() for n in notifications)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd tools/hub && .venv/bin/pytest tests/test_tui_tasks_panel.py::test_ctrl_r_syncs_from_todo_md tests/test_tui_tasks_panel.py::test_ctrl_r_no_path_shows_warning -q
```

Expected: FAIL — binding `ctrl+r` not found.

- [ ] **Step 3: Update `hub/tui/panels/tasks.py`**

Add two imports at the top (after existing imports):

```python
from hub.core.projects import get_project_path
from hub.core.todo_sync import sync_project
```

Add `ctrl+r` to `BINDINGS`:

```python
BINDINGS = [
    Binding("ctrl+n", "new_task", "New", show=True),
    Binding("ctrl+r", "sync_from_file", "Sync", show=True),
    Binding("space", "toggle_done", "Done", show=True),
    Binding("ctrl+d", "delete_task_action", "Delete", show=True),
]
```

Add `action_sync_from_file` method (insert before `action_new_task`):

```python
def action_sync_from_file(self) -> None:
    if not self._project:
        return
    path = get_project_path(self.db, self._project)
    if not path:
        self.app.notify("No local path configured for this project", severity="warning")
        return
    result = sync_project(self.db, self._project, path)
    self._reload()
    self.app.notify(
        f"Synced: {result['imported']} imported, {result['updated']} updated"
    )
```

- [ ] **Step 4: Run new tests**

```bash
cd tools/hub && .venv/bin/pytest tests/test_tui_tasks_panel.py::test_ctrl_r_syncs_from_todo_md tests/test_tui_tasks_panel.py::test_ctrl_r_no_path_shows_warning -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run full test suite**

```bash
cd tools/hub && .venv/bin/pytest tests/ -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add hub/tui/panels/tasks.py tests/test_tui_tasks_panel.py
git commit -m "feat(hub): add ctrl+r to sync current project from TODO.md"
```

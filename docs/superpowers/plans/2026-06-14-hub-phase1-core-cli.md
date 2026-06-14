# hub Phase 1 — Core + CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `hub` — a unified project + task manager replacing p-launch and todo-tool — starting with the data layer and a fully scriptable CLI usable by agents.

**Architecture:** A shared `core/` Python library (no UI deps) handles all data access via SQLite. A `cli/` Typer layer wraps it with `--json` output for agents. The TUI (Phase 2) will import from the same `core/`. All local storage lives under `~/.hskill/`.

**Tech Stack:** Python 3.11+, sqlite3 (stdlib), Typer, pytest. No FastAPI, no Pydantic — keep it lean.

---

## File Map

```
tools/hub/
├── core/
│   ├── __init__.py          # empty
│   ├── db.py                # SQLite connection + schema init
│   ├── projects.py          # project CRUD + PROJECTS.md sync
│   └── tasks.py             # task CRUD
├── cli/
│   ├── __init__.py          # Typer app + output helpers
│   ├── projects.py          # hub projects list/add/sync/path
│   └── tasks.py             # hub tasks list/add/done/update/rm
├── tests/
│   ├── __init__.py
│   ├── test_db.py
│   ├── test_projects.py
│   ├── test_tasks.py
│   └── test_cli.py
├── __main__.py              # entry: no args → TUI stub; args → CLI
├── pyproject.toml
└── tool.json
```

---

## Task 1: Scaffold — pyproject.toml, tool.json, __main__.py

**Files:**
- Create: `tools/hub/pyproject.toml`
- Create: `tools/hub/tool.json`
- Create: `tools/hub/__main__.py`
- Create: `tools/hub/core/__init__.py`
- Create: `tools/hub/cli/__init__.py`
- Create: `tools/hub/tests/__init__.py`

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tools/hub/core tools/hub/cli tools/hub/tests
touch tools/hub/core/__init__.py tools/hub/cli/__init__.py tools/hub/tests/__init__.py
```

- [ ] **Step 2: Write pyproject.toml**

```toml
# tools/hub/pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hub"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "textual>=0.80",
]

[project.scripts]
hub = "hub.__main__:main"

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.hatch.build.targets.wheel]
packages = ["core", "cli"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 3: Write tool.json**

```json
{
  "name": "hub",
  "version": "1.0.0",
  "description": "personal developer OS — projects, git status, tasks",
  "extraPaths": ["core", "cli", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/hub/venv"],
  "configPaths": ["~/.hskill/hub"]
}
```

- [ ] **Step 4: Write __main__.py**

```python
# tools/hub/__main__.py
import sys


def main():
    if len(sys.argv) == 1:
        # No args: launch TUI (Phase 2 stub for now)
        print("hub TUI coming in Phase 2. Use 'hub --help' for CLI commands.")
        return
    from hub.cli import app
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Commit scaffold**

```bash
git add tools/hub/
git commit -m "chore(hub): scaffold project structure"
```

---

## Task 2: core/db.py — SQLite connection + schema

**Files:**
- Create: `tools/hub/core/db.py`
- Create: `tools/hub/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/hub/tests/test_db.py
import sqlite3
import pytest
from pathlib import Path
from hub.core.db import HubDB


@pytest.fixture
def db(tmp_path):
    return HubDB(db_path=tmp_path / "hub.db")


def test_db_creates_projects_table(db):
    with db._conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "projects" in tables


def test_db_creates_tasks_table(db):
    with db._conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "tasks" in tables


def test_db_foreign_keys_enabled(db):
    with db._conn() as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


def test_db_idempotent_init(db):
    # calling _init twice must not raise
    db._init()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd tools/hub && python -m pytest tests/test_db.py -v
```
Expected: `ModuleNotFoundError: No module named 'hub'`

- [ ] **Step 3: Write core/db.py**

```python
# tools/hub/core/db.py
import os
import sqlite3
from pathlib import Path


def get_db_path() -> Path:
    if env := os.environ.get("HUB_DB_PATH"):
        return Path(env)
    return Path.home() / ".hskill" / "hub" / "tasks.db"


class HubDB:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT NOT NULL UNIQUE,
                    path        TEXT,
                    description TEXT DEFAULT '',
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT NOT NULL,
                    project_id  INTEGER NOT NULL REFERENCES projects(id),
                    priority    TEXT DEFAULT 'P2',
                    status      TEXT DEFAULT 'todo',
                    created_at  TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_project ON tasks(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_status  ON tasks(status)")
```

- [ ] **Step 4: Install in dev mode and run tests**

```bash
cd tools/hub && pip install -e ".[dev]" -q
python -m pytest tests/test_db.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/hub/core/db.py tools/hub/tests/test_db.py
git commit -m "feat(hub): core/db.py — SQLite schema + connection"
```

---

## Task 3: core/projects.py — project CRUD + PROJECTS.md sync

**Files:**
- Create: `tools/hub/core/projects.py`
- Create: `tools/hub/tests/test_projects.py`

- [ ] **Step 1: Write the failing tests**

```python
# tools/hub/tests/test_projects.py
import pytest
from pathlib import Path
from hub.core.db import HubDB
from hub.core.projects import add_project, list_projects, get_project_path


@pytest.fixture
def db(tmp_path):
    return HubDB(db_path=tmp_path / "hub.db")


@pytest.fixture
def md_path(tmp_path):
    return tmp_path / "PROJECTS.md"


def test_add_project_persists(db, md_path):
    add_project(db, "video-learner", path="/home/user/video-learner", md_path=md_path)
    projects = list_projects(db)
    assert len(projects) == 1
    assert projects[0]["name"] == "video-learner"
    assert projects[0]["path"] == "/home/user/video-learner"


def test_add_project_writes_md(db, md_path):
    add_project(db, "video-learner", path="/home/user/video-learner", md_path=md_path)
    content = md_path.read_text()
    assert "video-learner" in content
    assert "/home/user/video-learner" in content


def test_add_project_upserts(db, md_path):
    add_project(db, "video-learner", path="/old", md_path=md_path)
    add_project(db, "video-learner", path="/new", md_path=md_path)
    projects = list_projects(db)
    assert len(projects) == 1
    assert projects[0]["path"] == "/new"


def test_get_project_path_found(db, md_path):
    add_project(db, "blog", path="/home/user/blog", md_path=md_path)
    assert get_project_path(db, "blog") == "/home/user/blog"


def test_get_project_path_not_found(db):
    assert get_project_path(db, "nonexistent") is None


def test_list_projects_empty(db):
    assert list_projects(db) == []
```

- [ ] **Step 2: Run to verify failure**

```bash
cd tools/hub && python -m pytest tests/test_projects.py -v
```
Expected: `ImportError: cannot import name 'add_project'`

- [ ] **Step 3: Write core/projects.py**

```python
# tools/hub/core/projects.py
import fcntl
from datetime import datetime, timezone
from pathlib import Path

_DEFAULT_MD = Path.home() / ".hskill" / "public" / "PROJECTS.md"


def _write_md(projects: list[dict], md_path: Path) -> None:
    """Write PROJECTS.md under exclusive lock."""
    md_path.parent.mkdir(parents=True, exist_ok=True)
    lock = md_path.with_suffix(".lock")
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            parts = ["# Project Index"]
            for p in projects:
                parts.append(f"\n- **{p['name']}** `{p['path'] or ''}`")
                if p.get("description"):
                    parts.append(f"  {p['description']}")
            parts.append("")
            md_path.write_text("\n".join(parts), encoding="utf-8")
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


def add_project(
    db,
    name: str,
    path: str = "",
    description: str = "",
    md_path: Path = _DEFAULT_MD,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with db._conn() as conn:
        conn.execute(
            """
            INSERT INTO projects (name, path, description, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                path        = excluded.path,
                description = CASE WHEN excluded.description != ''
                                   THEN excluded.description
                                   ELSE description END
            """,
            (name, path, description, now),
        )
    projects = list_projects(db)
    _write_md(projects, md_path)
    return next(p for p in projects if p["name"] == name)


def list_projects(db) -> list[dict]:
    with db._conn() as conn:
        rows = conn.execute(
            "SELECT name, path, description FROM projects ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


def get_project_path(db, name: str) -> str | None:
    with db._conn() as conn:
        row = conn.execute(
            "SELECT path FROM projects WHERE name = ?", (name,)
        ).fetchone()
    return row["path"] if row else None
```

- [ ] **Step 4: Run tests**

```bash
cd tools/hub && python -m pytest tests/test_projects.py -v
```
Expected: 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/hub/core/projects.py tools/hub/tests/test_projects.py
git commit -m "feat(hub): core/projects.py — CRUD + PROJECTS.md sync"
```

---

## Task 4: core/tasks.py — task CRUD

**Files:**
- Create: `tools/hub/core/tasks.py`
- Create: `tools/hub/tests/test_tasks.py`

- [ ] **Step 1: Write the failing tests**

```python
# tools/hub/tests/test_tasks.py
import pytest
from pathlib import Path
from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task, list_tasks, mark_done, delete_task, update_task


@pytest.fixture
def db(tmp_path):
    db = HubDB(db_path=tmp_path / "hub.db")
    add_project(db, "blog", path="/blog", md_path=tmp_path / "PROJECTS.md")
    return db


def test_add_task_returns_task(db):
    t = add_task(db, title="Write post", project="blog")
    assert t["id"] is not None
    assert t["title"] == "Write post"
    assert t["priority"] == "P2"
    assert t["status"] == "todo"
    assert t["project"] == "blog"


def test_add_task_unknown_project_raises(db):
    with pytest.raises(ValueError, match="Project 'nope' not found"):
        add_task(db, title="x", project="nope")


def test_list_tasks_all(db):
    add_task(db, title="A", project="blog")
    add_task(db, title="B", project="blog", priority="P1")
    tasks = list_tasks(db)
    assert len(tasks) == 2


def test_list_tasks_filter_project(db):
    add_task(db, title="A", project="blog")
    tasks = list_tasks(db, project="blog")
    assert len(tasks) == 1

def test_list_tasks_filter_status(db):
    t = add_task(db, title="A", project="blog")
    mark_done(db, t["id"])
    assert list_tasks(db, status="todo") == []
    assert len(list_tasks(db, status="done")) == 1


def test_mark_done_updates_status(db):
    t = add_task(db, title="A", project="blog")
    result = mark_done(db, t["id"])
    assert result["status"] == "done"


def test_mark_done_missing_id_returns_none(db):
    assert mark_done(db, 9999) is None


def test_delete_task_removes_it(db):
    t = add_task(db, title="A", project="blog")
    assert delete_task(db, t["id"]) is True
    assert list_tasks(db) == []


def test_update_task_title(db):
    t = add_task(db, title="Old", project="blog")
    updated = update_task(db, t["id"], title="New")
    assert updated["title"] == "New"


def test_update_task_priority(db):
    t = add_task(db, title="A", project="blog")
    updated = update_task(db, t["id"], priority="P1")
    assert updated["priority"] == "P1"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd tools/hub && python -m pytest tests/test_tasks.py -v
```
Expected: `ImportError: cannot import name 'add_task'`

- [ ] **Step 3: Write core/tasks.py**

```python
# tools/hub/core/tasks.py
from datetime import datetime, timezone
from typing import Optional


_TASK_SELECT = """
    SELECT t.id, t.title, p.name AS project, t.priority, t.status, t.created_at
    FROM tasks t JOIN projects p ON p.id = t.project_id
"""


def add_task(db, title: str, project: str, priority: str = "P2") -> dict:
    with db._conn() as conn:
        row = conn.execute(
            "SELECT id FROM projects WHERE name = ?", (project,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Project '{project}' not found. Run: hub projects add {project}")
        project_id = row["id"]
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "INSERT INTO tasks (title, project_id, priority, status, created_at) VALUES (?,?,?,?,?)",
            (title, project_id, priority, "todo", now),
        )
        task_row = conn.execute(
            _TASK_SELECT + " WHERE t.id = ?", (cur.lastrowid,)
        ).fetchone()
        if task_row is None:
            raise RuntimeError(f"DB invariant violated: task INSERT row {cur.lastrowid} not found")
        return dict(task_row)


def list_tasks(
    db,
    project: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
) -> list[dict]:
    query = _TASK_SELECT + " WHERE 1=1"
    params: list = []
    if project:
        query += " AND p.name = ?"
        params.append(project)
    if status:
        query += " AND t.status = ?"
        params.append(status)
    if priority:
        query += " AND t.priority = ?"
        params.append(priority)
    query += " ORDER BY t.created_at DESC"
    with db._conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


def mark_done(db, task_id: int) -> Optional[dict]:
    return update_task(db, task_id, status="done")


def update_task(
    db,
    task_id: int,
    title: Optional[str] = None,
    priority: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[dict]:
    fields = {k: v for k, v in {"title": title, "priority": priority, "status": status}.items() if v is not None}
    if not fields:
        tasks = list_tasks(db)
        return next((t for t in tasks if t["id"] == task_id), None)
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with db._conn() as conn:
        cur = conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            [*fields.values(), task_id],
        )
        if cur.rowcount == 0:
            return None
        row = conn.execute(_TASK_SELECT + " WHERE t.id = ?", (task_id,)).fetchone()
    return dict(row) if row else None


def delete_task(db, task_id: int) -> bool:
    with db._conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return cur.rowcount > 0
```

- [ ] **Step 4: Run tests**

```bash
cd tools/hub && python -m pytest tests/test_tasks.py -v
```
Expected: 10 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/hub/core/tasks.py tools/hub/tests/test_tasks.py
git commit -m "feat(hub): core/tasks.py — task CRUD"
```

---

## Task 5: CLI entry point + output helpers

**Files:**
- Modify: `tools/hub/cli/__init__.py`

- [ ] **Step 1: Write cli/__init__.py**

```python
# tools/hub/cli/__init__.py
import json
import sys
import typer

from hub.cli import projects as proj_cmd
from hub.cli import tasks as task_cmd

app = typer.Typer(
    name="hub",
    no_args_is_help=False,
    add_completion=False,
)
app.add_typer(proj_cmd.app, name="projects")
app.add_typer(task_cmd.app, name="tasks")


def ok(data, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": True, "data": data}))
    # human-readable output is handled by each command directly


def err(msg: str, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": False, "error": msg}))
    else:
        typer.echo(f"Error: {msg}", err=True)
    sys.exit(1)
```

- [ ] **Step 2: Commit**

```bash
git add tools/hub/cli/__init__.py
git commit -m "feat(hub): cli entry point + output helpers"
```

---

## Task 6: CLI projects commands

**Files:**
- Create: `tools/hub/cli/projects.py`
- Create: `tools/hub/tests/test_cli.py` (projects section)

- [ ] **Step 1: Write the failing tests**

```python
# tools/hub/tests/test_cli.py
import json
import os
import pytest
from pathlib import Path
from typer.testing import CliRunner
from hub.cli import app
from hub.core.db import HubDB

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


def test_projects_add_and_list_json(tmp_path):
    runner.invoke(app, ["projects", "add", "blog", "--path", "/tmp/blog"])
    result = runner.invoke(app, ["projects", "list", "--json"])
    data = json.loads(result.output)
    assert data["ok"] is True
    assert any(p["name"] == "blog" for p in data["data"])


def test_projects_path_found(tmp_path):
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
```

- [ ] **Step 2: Run to verify failure**

```bash
cd tools/hub && python -m pytest tests/test_cli.py -v
```
Expected: `ImportError` or `no such command 'projects'`

- [ ] **Step 3: Write cli/projects.py**

```python
# tools/hub/cli/projects.py
import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer

from hub.core.db import HubDB, get_db_path
from hub.core import projects as proj

app = typer.Typer(no_args_is_help=True)

_DEFAULT_MD = Path.home() / ".hskill" / "public" / "PROJECTS.md"


def _md_path() -> Path:
    if env := os.environ.get("HUB_MD_PATH"):
        return Path(env)
    return _DEFAULT_MD


def _out(data, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": True, "data": data}))


def _err(msg: str, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": False, "error": msg}))
    else:
        typer.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


@app.command("list")
def projects_list(json_out: bool = typer.Option(False, "--json")):
    """List all registered projects."""
    db = HubDB()
    projects = proj.list_projects(db)
    if json_out:
        _out(projects, json_out)
    else:
        if not projects:
            typer.echo("No projects. Use: hub projects add <name> --path <path>")
            return
        for p in projects:
            typer.echo(f"  {p['name']:<24} {p['path'] or ''}")
            if p.get("description"):
                typer.echo(f"    {p['description']}")


@app.command("add")
def projects_add(
    name: str = typer.Argument(..., help="Project name (GitHub repo name)"),
    path: str = typer.Option("", "--path", help="Local directory path"),
    description: str = typer.Option("", "--desc", help="Short description"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Register or update a project."""
    db = HubDB()
    result = proj.add_project(db, name, path=path, description=description, md_path=_md_path())
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ {name}")


@app.command("path")
def projects_path(
    name: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Print the local path for a project (for shell cd / agent use)."""
    db = HubDB()
    p = proj.get_project_path(db, name)
    if p is None:
        _err(f"Project '{name}' not found", json_out)
    if json_out:
        _out(p, json_out)
    else:
        print(p)


@app.command("sync")
def projects_sync(json_out: bool = typer.Option(False, "--json")):
    """Re-scan configured dirs and update PROJECTS.md. (Requires p-launch config.)"""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parents[3] / "p-launch"))
        from p_launch import read_project_dirs, collect_repos, sync_to_index
        dirs = read_project_dirs()
        repos = collect_repos(dirs)
        sync_to_index(repos, _md_path())
        if json_out:
            _out({"scanned": len(repos)}, json_out)
        else:
            typer.echo(f"✓ Scanned {len(repos)} repos")
    except ImportError:
        _err("p-launch not installed; cannot auto-scan", json_out)
```

- [ ] **Step 4: Run tests**

```bash
cd tools/hub && python -m pytest tests/test_cli.py -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add tools/hub/cli/projects.py tools/hub/tests/test_cli.py
git commit -m "feat(hub): cli projects commands (list/add/path/sync)"
```

---

## Task 7: CLI tasks commands

**Files:**
- Create: `tools/hub/cli/tasks.py`
- Modify: `tools/hub/tests/test_cli.py` (add tasks tests)

- [ ] **Step 1: Add tasks tests to test_cli.py**

Append to `tools/hub/tests/test_cli.py`:

```python
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
```

- [ ] **Step 2: Run to verify new tests fail**

```bash
cd tools/hub && python -m pytest tests/test_cli.py -v -k "tasks"
```
Expected: FAIL — `no such command 'tasks'`

- [ ] **Step 3: Write cli/tasks.py**

```python
# tools/hub/cli/tasks.py
import json
import sys
from typing import Optional

import typer

from hub.core.db import HubDB
from hub.core import tasks as task

app = typer.Typer(no_args_is_help=True)


def _out(data, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": True, "data": data}))


def _err(msg: str, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": False, "error": msg}))
    else:
        typer.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


@app.command("list")
def tasks_list(
    project:  Optional[str] = typer.Option(None, "--project",  "-p"),
    status:   Optional[str] = typer.Option(None, "--status",   "-s"),
    priority: Optional[str] = typer.Option(None, "--priority", "-P"),
    json_out: bool           = typer.Option(False, "--json"),
):
    """List tasks, optionally filtered."""
    db = HubDB()
    tasks = task.list_tasks(db, project=project, status=status, priority=priority)
    if json_out:
        _out(tasks, json_out)
    else:
        if not tasks:
            typer.echo("No tasks.")
            return
        for t in tasks:
            check = "✓" if t["status"] == "done" else "○"
            typer.echo(f"  [{t['id']:>4}] {check} [{t['priority']}] {t['title']}  ({t['project']})")


@app.command("add")
def tasks_add(
    title:    str           = typer.Argument(...),
    project:  str           = typer.Option(..., "--project", "-p"),
    priority: str           = typer.Option("P2", "--priority", "-P"),
    json_out: bool          = typer.Option(False, "--json"),
):
    """Add a new task."""
    db = HubDB()
    try:
        t = task.add_task(db, title=title, project=project, priority=priority)
    except ValueError as e:
        _err(str(e), json_out)
    if json_out:
        _out(t, json_out)
    else:
        typer.echo(f"✓ [{t['id']}] {t['title']}")


@app.command("done")
def tasks_done(
    task_id:  int  = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Mark a task as done."""
    db = HubDB()
    result = task.mark_done(db, task_id)
    if result is None:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ done: {result['title']}")


@app.command("update")
def tasks_update(
    task_id:  int            = typer.Argument(...),
    title:    Optional[str]  = typer.Option(None, "--title"),
    priority: Optional[str]  = typer.Option(None, "--priority"),
    status:   Optional[str]  = typer.Option(None, "--status"),
    json_out: bool           = typer.Option(False, "--json"),
):
    """Update task fields."""
    db = HubDB()
    result = task.update_task(db, task_id, title=title, priority=priority, status=status)
    if result is None:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ updated [{task_id}]")


@app.command("rm")
def tasks_rm(
    task_id:  int  = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Delete a task."""
    db = HubDB()
    deleted = task.delete_task(db, task_id)
    if not deleted:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out({"deleted": True}, json_out)
    else:
        typer.echo(f"✓ deleted [{task_id}]")
```

- [ ] **Step 4: Run all tests**

```bash
cd tools/hub && python -m pytest tests/ -v
```
Expected: all tests PASS (≥20 total)

- [ ] **Step 5: Smoke test the CLI manually**

```bash
hub projects add test-proj --path /tmp --desc "smoke test"
hub projects list
hub tasks add "check CLI works" --project test-proj --priority P1
hub tasks list --json
hub tasks done 1 --json
```
Expected: structured JSON output on `--json` commands, readable output without it.

- [ ] **Step 6: Commit**

```bash
git add tools/hub/cli/tasks.py tools/hub/tests/test_cli.py
git commit -m "feat(hub): cli tasks commands (list/add/done/update/rm)"
```

---

## Task 8: Migration script (first-launch auto-migrate)

**Files:**
- Create: `tools/hub/core/migrate.py`
- Modify: `tools/hub/__main__.py`

- [ ] **Step 1: Write core/migrate.py**

```python
# tools/hub/core/migrate.py
"""One-time migration: copy tasks from todo-tool's DB into hub's DB."""
import sqlite3
from pathlib import Path


_OLD_DB = Path.home() / ".local" / "share" / "todo" / "tasks.db"
_SENTINEL = Path.home() / ".hskill" / "hub" / ".migrated"


def needs_migration() -> bool:
    return _OLD_DB.exists() and not _SENTINEL.exists()


def run_migration(hub_db) -> int:
    """Copy projects + tasks from todo-tool DB. Returns number of tasks migrated."""
    if not _OLD_DB.exists():
        return 0
    old = sqlite3.connect(_OLD_DB)
    old.row_factory = sqlite3.Row
    migrated = 0
    try:
        from hub.core.projects import add_project
        from hub.core.tasks import add_task
        from pathlib import Path as _Path
        md = _Path.home() / ".hskill" / "public" / "PROJECTS.md"

        for row in old.execute("SELECT repo_name, local_path FROM projects").fetchall():
            try:
                add_project(hub_db, row["repo_name"], path=row["local_path"] or "", md_path=md)
            except Exception:
                pass  # already exists is fine

        for row in old.execute(
            "SELECT t.title, p.repo_name as project, t.priority, t.status "
            "FROM tasks t JOIN projects p ON p.id = t.project_id"
        ).fetchall():
            try:
                t = add_task(hub_db, title=row["title"], project=row["project"], priority=row["priority"])
                if row["status"] == "done":
                    from hub.core.tasks import mark_done
                    mark_done(hub_db, t["id"])
                migrated += 1
            except Exception:
                pass
    finally:
        old.close()

    _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    _SENTINEL.touch()
    return migrated
```

- [ ] **Step 2: Wire migration into __main__.py**

```python
# tools/hub/__main__.py
import sys


def main():
    from hub.core.db import HubDB
    from hub.core.migrate import needs_migration, run_migration

    db = HubDB()
    if needs_migration():
        n = run_migration(db)
        if n:
            import typer
            typer.echo(f"hub: migrated {n} tasks from todo-tool ✓")

    if len(sys.argv) == 1:
        print("hub TUI coming in Phase 2. Use 'hub --help' for CLI commands.")
        return
    from hub.cli import app
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run full test suite**

```bash
cd tools/hub && python -m pytest tests/ -v
```
Expected: all tests still PASS

- [ ] **Step 4: Commit**

```bash
git add tools/hub/core/migrate.py tools/hub/__main__.py
git commit -m "feat(hub): first-launch migration from todo-tool DB"
```

---

## Task 9: Register hub in skills-index.json

**Files:**
- Modify: `skills-index.json`

- [ ] **Step 1: Read current tools section**

```bash
grep -A5 '"p-launch"' skills-index.json
```

- [ ] **Step 2: Add hub entry**

In `skills-index.json`, add to the `tools` array (or equivalent structure used for p-launch):

```json
{
  "name": "hub",
  "path": "tools/hub",
  "bundle": "tools"
}
```

- [ ] **Step 3: Run existing hskill tests**

```bash
npm test
```
Expected: all tests pass including install test for hub

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "feat(hub): register in skills-index.json"
```

---

## Self-Review

**Spec coverage:**
- ✓ Data layer: `core/db.py` — SQLite at `~/.hskill/hub/tasks.db`
- ✓ Projects: `core/projects.py` + `cli/projects.py` — list/add/path/sync
- ✓ Tasks: `core/tasks.py` + `cli/tasks.py` — list/add/done/update/rm
- ✓ JSON output contract `{"ok": bool, "data": ...}` — in every CLI command
- ✓ PROJECTS.md sync with fcntl lock — `_write_md()` in projects.py
- ✓ Migration from todo-tool — `core/migrate.py`, runs on first launch
- ✓ `HUB_DB_PATH` env var for test isolation — in `db.py`
- ✓ `HUB_MD_PATH` env var for test isolation — in `cli/projects.py`
- ⏭ TUI — Phase 2 (separate plan)
- ⏭ p-launch retirement — Phase 3

**Placeholder scan:** No TBDs. All code blocks complete. ✓

**Type consistency:**
- `HubDB` constructed the same way in all tasks ✓
- `add_project(db, name, path, description, md_path)` signature consistent ✓
- `add_task(db, title, project, priority)` consistent ✓
- `_out / _err` helpers duplicated in `cli/projects.py` and `cli/tasks.py` — intentional (avoids shared state)

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Project, ProjectCreate, ProjectUpdate, Task, TaskCreate, TaskUpdate
from .parser import parse_todo_file

ALLOWED_TASK_UPDATE_COLUMNS = {"title", "priority", "status"}
ALLOWED_PROJECT_UPDATE_COLUMNS = {"repo_name", "local_path"}


def get_db_path() -> Path:
    if env_path := os.environ.get("TODO_DB_PATH"):
        return Path(env_path)
    config_path = Path.home() / ".local" / "share" / "todo" / "config.json"
    if config_path.exists():
        config = json.loads(config_path.read_text())
        if db_path := config.get("db_path"):
            return Path(db_path).expanduser()
    return Path.home() / ".local" / "share" / "todo" / "tasks.db"


class TodoDB:
    def __init__(self, db_path: Path = None):
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    repo_name  TEXT NOT NULL UNIQUE,
                    local_path TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL,
                    project_id INTEGER NOT NULL REFERENCES projects(id),
                    priority   TEXT DEFAULT 'P2',
                    status     TEXT DEFAULT 'todo',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON tasks(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status  ON tasks(status)")

    # ── Project CRUD ──────────────────────────────────────────────────────────

    def create_project(self, data: ProjectCreate) -> Project:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO projects (repo_name, local_path, created_at) VALUES (?, ?, ?)",
                (data.repo_name, data.local_path, now),
            )
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            assert row is not None
            return Project(**dict(row))

    def get_project(self, project_id: int) -> Optional[Project]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return Project(**dict(row)) if row else None

    def get_project_by_name(self, repo_name: str) -> Optional[Project]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM projects WHERE repo_name = ?", (repo_name,)
            ).fetchone()
            return Project(**dict(row)) if row else None

    def list_projects(self) -> list[Project]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY repo_name"
            ).fetchall()
            return [Project(**dict(r)) for r in rows]

    def update_project(self, project_id: int, data: ProjectUpdate) -> Optional[Project]:
        fields = {
            k: v
            for k, v in data.model_dump(exclude_none=True).items()
            if k in ALLOWED_PROJECT_UPDATE_COLUMNS
        }
        if not fields:
            return self.get_project(project_id)
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE projects SET {set_clause} WHERE id = ?",
                [*fields.values(), project_id],
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                "SELECT * FROM projects WHERE id = ?", (project_id,)
            ).fetchone()
            return Project(**dict(row)) if row else None

    def delete_project(self, project_id: int) -> bool:
        with self._conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
            ).fetchone()[0]
            if count > 0:
                raise ValueError(f"Project has {count} task(s); delete or reassign them first")
            cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cur.rowcount > 0

    # ── Task CRUD ─────────────────────────────────────────────────────────────

    _TASK_SELECT = """
        SELECT t.id, t.title, p.repo_name AS project, t.priority, t.status, t.created_at
        FROM tasks t JOIN projects p ON p.id = t.project_id
    """

    def create(self, data: TaskCreate) -> Task:
        project = self.get_project_by_name(data.project)
        if project is None:
            raise ValueError(
                f"Project '{data.project}' not found. Run: todo project add {data.project}"
            )
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, project_id, priority, status, created_at) "
                "VALUES (?, ?, ?, 'todo', ?)",
                (data.title, project.id, data.priority, now),
            )
            row = conn.execute(
                self._TASK_SELECT + " WHERE t.id = ?", (cur.lastrowid,)
            ).fetchone()
            assert row is not None
            return Task(**dict(row))

    def get(self, task_id: int) -> Optional[Task]:
        with self._conn() as conn:
            row = conn.execute(
                self._TASK_SELECT + " WHERE t.id = ?", (task_id,)
            ).fetchone()
            return Task(**dict(row)) if row else None

    def list_tasks(
        self,
        project: str = None,
        status: str = None,
        priority: str = None,
    ) -> list[Task]:
        query = self._TASK_SELECT + " WHERE 1=1"
        params: list = []
        if project:
            query += " AND p.repo_name = ?"
            params.append(project)
        if status:
            query += " AND t.status = ?"
            params.append(status)
        if priority:
            query += " AND t.priority = ?"
            params.append(priority)
        query += " ORDER BY t.created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Task(**dict(r)) for r in rows]

    def update(self, task_id: int, data: TaskUpdate) -> Optional[Task]:
        fields = {
            k: v
            for k, v in data.model_dump(exclude_none=True).items()
            if k in ALLOWED_TASK_UPDATE_COLUMNS
        }
        if not fields:
            return self.get(task_id)
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with self._conn() as conn:
            cur = conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                [*fields.values(), task_id],
            )
            if cur.rowcount == 0:
                return None
            row = conn.execute(
                self._TASK_SELECT + " WHERE t.id = ?", (task_id,)
            ).fetchone()
            return Task(**dict(row)) if row else None

    def delete(self, task_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def projects(self) -> list[Project]:
        return self.list_projects()

    def sync_from_file(self, path: Path, project_id: int) -> tuple[int, int]:
        tasks = parse_todo_file(path)
        lines = path.read_text(encoding="utf-8").splitlines()
        inserted = 0
        updated = 0

        # Process updates (tasks with existing IDs)
        for task in tasks:
            if task.id is not None:
                result = self.update(
                    task.id,
                    TaskUpdate(title=task.title, priority=task.priority, status=task.status),
                )
                if result:
                    updated += 1
                else:
                    print(
                        f"Warning: task ID {task.id} not found in DB — stale ID in TODO.md",
                        file=sys.stderr,
                    )

        # Batch-insert new tasks: write file first, then commit so a file-write failure rolls back
        new_tasks = [t for t in tasks if t.id is None]
        if new_tasks:
            now = datetime.now(timezone.utc).isoformat()
            conn = sqlite3.connect(self.db_path, isolation_level=None)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            try:
                conn.execute("BEGIN")
                for task in new_tasks:
                    cur = conn.execute(
                        "INSERT INTO tasks (title, project_id, priority, status, created_at) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (task.title, project_id, task.priority, task.status, now),
                    )
                    lines[task.metadata_line_num] += f" | **ID**: {cur.lastrowid}"
                    inserted += 1
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
            finally:
                conn.close()

        return inserted, updated

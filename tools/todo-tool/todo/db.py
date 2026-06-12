import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import Task, TaskCreate, TaskUpdate


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
        return conn

    def _init(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    title      TEXT NOT NULL,
                    project    TEXT NOT NULL,
                    priority   TEXT DEFAULT 'P2',
                    status     TEXT DEFAULT 'todo',
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON tasks(project)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")

    def create(self, data: TaskCreate) -> Task:
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO tasks (title, project, priority, status, created_at) "
                "VALUES (?, ?, ?, 'todo', ?)",
                (data.title, data.project, data.priority, now),
            )
            task_id = cur.lastrowid
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return Task(**dict(row)) if row else None

    def get(self, task_id: int) -> Optional[Task]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            return Task(**dict(row)) if row else None

    def list_tasks(
        self,
        project: str = None,
        status: str = None,
        priority: str = None,
    ) -> list[Task]:
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list = []
        if project:
            query += " AND project = ?"
            params.append(project)
        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)
        query += " ORDER BY created_at DESC"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [Task(**dict(r)) for r in rows]

    def update(self, task_id: int, data: TaskUpdate) -> Optional[Task]:
        fields = {k: v for k, v in data.model_dump(exclude_none=True).items()}
        if not fields:
            return self.get(task_id)
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        with self._conn() as conn:
            conn.execute(
                f"UPDATE tasks SET {set_clause} WHERE id = ?",
                [*fields.values(), task_id],
            )
        return self.get(task_id)

    def delete(self, task_id: int) -> bool:
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def projects(self) -> list[str]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT project FROM tasks ORDER BY project"
            ).fetchall()
            return [r[0] for r in rows]

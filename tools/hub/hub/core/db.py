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

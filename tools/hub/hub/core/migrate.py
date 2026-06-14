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
        from hub.core.tasks import add_task, mark_done
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
                    mark_done(hub_db, t["id"])
                migrated += 1
            except Exception:
                pass
    finally:
        old.close()

    _SENTINEL.parent.mkdir(parents=True, exist_ok=True)
    _SENTINEL.touch()
    return migrated

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
        elif result == "updated":
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
            "SELECT id, status, priority FROM tasks WHERE project_id = ? AND title = ?",
            (project_id, title),
        ).fetchone()
        if row:
            if row["status"] != status or row["priority"] != priority:
                conn.execute(
                    "UPDATE tasks SET status = ?, priority = ? WHERE id = ?",
                    (status, priority, row["id"]),
                )
                return "updated"
            return "unchanged"
        else:
            conn.execute(
                "INSERT INTO tasks (title, project_id, priority, status, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (title, project_id, priority, status, created_at),
            )
            return "imported"

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
        with db._conn() as conn:
            row = conn.execute(_TASK_SELECT + " WHERE t.id = ?", (task_id,)).fetchone()
        return dict(row) if row else None
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

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

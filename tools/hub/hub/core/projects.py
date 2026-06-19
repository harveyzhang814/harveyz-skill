import fcntl
import re
import subprocess
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


def _resolve_name(repo_path: Path) -> str:
    """Resolve project name from git remote origin URL, fall back to dir name."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            url = result.stdout.strip().rstrip("/")
            if url.endswith(".git"):
                url = url[:-4]
            return re.split(r"[/:]", url)[-1]
    except Exception:
        pass
    return repo_path.name


def remove_project(
    db,
    name: str,
    md_path: Path = _DEFAULT_MD,
    force: bool = False,
) -> dict:
    with db._conn() as conn:
        row = conn.execute("SELECT id FROM projects WHERE name = ?", (name,)).fetchone()
        if row is None:
            raise KeyError(f"Project '{name}' not found")
        project_id = row["id"]
        task_count = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
        ).fetchone()[0]
        if task_count and not force:
            raise ValueError(
                f"Project '{name}' has {task_count} task(s). Use --force to also delete them."
            )
        if task_count:
            conn.execute("DELETE FROM tasks WHERE project_id = ?", (project_id,))
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    _write_md(list_projects(db), md_path)
    return {"name": name, "tasks_deleted": task_count if force else 0}


def scan_projects(
    dirs: list[str],
    db,
    md_path: Path = _DEFAULT_MD,
) -> dict:
    """Scan directories (direct subdirectories (one level deep)) for git repos and register them as projects.

    Returns {"added": [...], "skipped": [...], "failed": [...]}.
    Existing projects (by name) are skipped without modification.
    """
    added: list[dict] = []
    skipped: list[str] = []
    failed: list[dict] = []
    existing = {p["name"] for p in list_projects(db)}

    for d in dirs:
        p = Path(d).expanduser()
        if not p.exists():
            failed.append({"path": str(d), "reason": "directory not found"})
            continue
        for git_dir in sorted(p.glob("*/.git")):
            repo_path = git_dir.parent
            name = _resolve_name(repo_path)
            if name in existing:
                skipped.append(name)
                continue
            try:
                add_project(db, name, path=str(repo_path), md_path=md_path)
                added.append({"name": name, "path": str(repo_path)})
                existing.add(name)
            except Exception as e:
                failed.append({"path": str(repo_path), "reason": str(e)})

    return {"added": added, "skipped": skipped, "failed": failed}

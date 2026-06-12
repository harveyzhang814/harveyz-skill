import os
import re
from pathlib import Path

_LINE_RE = re.compile(r'^\s*-\s+\*\*(.+?)\*\*\s+`(.+?)`\s*$')
_DESC_RE = re.compile(r'^  (.+)$')


def get_index_path() -> Path:
    if env := os.environ.get("TODO_INDEX_PATH"):
        return Path(env)
    return Path.home() / ".hskill" / "todo-tool" / "PROJECTS.md"


def load_projects() -> list[dict]:
    path = get_index_path()
    if not path.exists():
        return []
    projects = []
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lines):
        m = _LINE_RE.match(lines[i])
        if m:
            entry = {"name": m.group(1), "path": m.group(2), "description": ""}
            if i + 1 < len(lines):
                dm = _DESC_RE.match(lines[i + 1])
                if dm:
                    entry["description"] = dm.group(1)
                    i += 1
            projects.append(entry)
        i += 1
    return projects


def save_project(name: str, path: str, description: str = "") -> None:
    index_path = get_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    projects = load_projects()
    for p in projects:
        if p["name"] == name:
            p["path"] = path
            if description:
                p["description"] = description
            _write(projects, index_path)
            return
    projects.append({"name": name, "path": path, "description": description})
    _write(projects, index_path)


def set_project_path(name: str, new_path: str) -> bool:
    projects = load_projects()
    for p in projects:
        if p["name"] == name:
            p["path"] = new_path
            _write(projects, get_index_path())
            return True
    return False


def _write(projects: list[dict], path: Path) -> None:
    parts = ["# Project Index"]
    for p in projects:
        parts.append(f"\n- **{p['name']}** `{p['path']}`")
        if p.get("description"):
            parts.append(f"  {p['description']}")
    parts.append("")
    path.write_text("\n".join(parts), encoding="utf-8")

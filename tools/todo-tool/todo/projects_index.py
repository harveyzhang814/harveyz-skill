import fcntl
import os
import re
import shutil
import sys
from pathlib import Path

_LINE_RE = re.compile(r'^\s*-\s+\*\*(.+?)\*\*\s+`(.+?)`\s*$')
_DESC_RE = re.compile(r'^  (.+)$')

_OLD_INDEX = Path.home() / ".hskill" / "todo-tool" / "PROJECTS.md"
_PUBLIC_DIR = Path.home() / ".hskill" / "public"
_MIGRATED_FLAG = _PUBLIC_DIR / ".migrated"


def get_index_path() -> Path:
    if env := os.environ.get("TODO_INDEX_PATH"):
        return Path(env)
    return _PUBLIC_DIR / "PROJECTS.md"


def _parse(path: Path) -> list[dict]:
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


def _migrate_once(index_path: Path) -> None:
    """One-time merge of old index descriptions into new shared index."""
    if _MIGRATED_FLAG.exists():
        return
    if not _OLD_INDEX.exists():
        # Nothing to migrate; mark done so we don't check again.
        _mark_migrated()
        return

    old = {p["name"]: p for p in _parse(_OLD_INDEX)}
    if not old:
        _mark_migrated()
        return

    new = _parse(index_path)
    new_by_name = {p["name"]: p for p in new}

    # Back-fill descriptions that p-launch sync may have left empty.
    for name, op in old.items():
        if name in new_by_name:
            if not new_by_name[name]["description"] and op["description"]:
                new_by_name[name]["description"] = op["description"]
        else:
            new.append(op)

    _write_locked(new, index_path)
    _mark_migrated()


def _mark_migrated() -> None:
    try:
        _PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
        _MIGRATED_FLAG.touch()
    except OSError as e:
        print(f"warning: could not write migration flag: {e}", file=sys.stderr)


def load_projects() -> list[dict]:
    path = get_index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_once(path)
    return _parse(path)


def save_project(name: str, path: str, description: str = "") -> None:
    index_path = get_index_path()
    index_path.parent.mkdir(parents=True, exist_ok=True)
    _migrate_once(index_path)
    projects = _parse(index_path)
    for p in projects:
        if p["name"] == name:
            p["path"] = path
            if description:
                p["description"] = description
            _write_locked(projects, index_path)
            return
    projects.append({"name": name, "path": path, "description": description})
    _write_locked(projects, index_path)


def set_project_path(name: str, new_path: str) -> bool:
    index_path = get_index_path()
    _migrate_once(index_path)
    projects = _parse(index_path)
    for p in projects:
        if p["name"] == name:
            p["path"] = new_path
            _write_locked(projects, index_path)
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


def _write_locked(projects: list[dict], path: Path) -> None:
    lock = path.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            _write(projects, path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)

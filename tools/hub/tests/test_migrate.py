import sqlite3
import pytest
from pathlib import Path
from hub.core.db import HubDB
import hub.core.migrate as migrate_mod


def _make_old_db(path: Path) -> None:
    """Create a minimal todo-tool-style DB with one project and two tasks."""
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY, repo_name TEXT UNIQUE, local_path TEXT, created_at TEXT)"
    )
    conn.execute(
        "CREATE TABLE tasks (id INTEGER PRIMARY KEY, title TEXT, project_id INTEGER, priority TEXT, status TEXT, created_at TEXT)"
    )
    conn.execute("INSERT INTO projects VALUES (1, 'myrepo', '/code/myrepo', '2024-01-01')")
    conn.execute("INSERT INTO tasks VALUES (1, 'Write tests', 1, 'P1', 'done', '2024-01-01')")
    conn.execute("INSERT INTO tasks VALUES (2, 'Ship it',    1, 'P2', 'todo', '2024-01-01')")
    conn.commit()
    conn.close()


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    old_db = tmp_path / "old.db"
    sentinel = tmp_path / ".migrated"
    hub_db_path = tmp_path / "hub.db"
    monkeypatch.setenv("HUB_DB_PATH", str(hub_db_path))
    monkeypatch.setattr(migrate_mod, "_OLD_DB", old_db)
    monkeypatch.setattr(migrate_mod, "_SENTINEL", sentinel)
    return {"old_db": old_db, "sentinel": sentinel, "hub_db_path": hub_db_path, "tmp": tmp_path}


def test_needs_migration_no_old_db(isolated):
    assert migrate_mod.needs_migration() is False


def test_needs_migration_old_db_exists(isolated):
    isolated["old_db"].touch()
    assert migrate_mod.needs_migration() is True


def test_needs_migration_already_done(isolated):
    isolated["old_db"].touch()
    isolated["sentinel"].touch()
    assert migrate_mod.needs_migration() is False


def test_run_migration_copies_projects_and_tasks(isolated, tmp_path):
    _make_old_db(isolated["old_db"])
    md_path = tmp_path / "PROJECTS.md"

    db = HubDB(isolated["hub_db_path"])

    # monkeypatch the md path used inside run_migration
    import hub.core.migrate as m
    original_home = Path.home
    monkeypatch_path = tmp_path

    # patch Path.home inside migrate so PROJECTS.md goes to tmp
    import unittest.mock as mock
    with mock.patch("hub.core.migrate.Path") as MockPath:
        MockPath.home.return_value = tmp_path
        MockPath.side_effect = lambda *a: Path(*a)  # let Path(str) still work
        count = migrate_mod.run_migration(db)

    assert count == 2


def test_run_migration_writes_sentinel(isolated):
    _make_old_db(isolated["old_db"])
    db = HubDB(isolated["hub_db_path"])

    import unittest.mock as mock
    with mock.patch("hub.core.migrate.Path") as MockPath:
        MockPath.home.return_value = isolated["tmp"]
        MockPath.side_effect = lambda *a: Path(*a)
        migrate_mod.run_migration(db)

    assert isolated["sentinel"].exists()


def test_run_migration_returns_zero_if_no_old_db(isolated):
    db = HubDB(isolated["hub_db_path"])
    count = migrate_mod.run_migration(db)
    assert count == 0


def test_run_migration_idempotent_sentinel(isolated):
    """Running migration twice only touches sentinel once; second call is guarded by needs_migration."""
    _make_old_db(isolated["old_db"])
    db = HubDB(isolated["hub_db_path"])

    import unittest.mock as mock
    with mock.patch("hub.core.migrate.Path") as MockPath:
        MockPath.home.return_value = isolated["tmp"]
        MockPath.side_effect = lambda *a: Path(*a)
        migrate_mod.run_migration(db)

    # After first run, needs_migration() should return False
    assert migrate_mod.needs_migration() is False

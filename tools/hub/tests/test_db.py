import sqlite3
import pytest
from pathlib import Path
from hub.core.db import HubDB


@pytest.fixture
def db(tmp_path):
    return HubDB(db_path=tmp_path / "hub.db")


def test_db_creates_projects_table(db):
    with db._conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "projects" in tables


def test_db_creates_tasks_table(db):
    with db._conn() as conn:
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
    assert "tasks" in tables


def test_db_foreign_keys_enabled(db):
    with db._conn() as conn:
        result = conn.execute("PRAGMA foreign_keys").fetchone()
    assert result[0] == 1


def test_db_idempotent_init(db):
    db._init()  # calling _init twice must not raise

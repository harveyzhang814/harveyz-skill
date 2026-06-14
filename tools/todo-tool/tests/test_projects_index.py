import pytest
from pathlib import Path
from todo.projects_index import (
    load_projects, save_project, set_project_path, _write, get_index_path,
    _parse, _MIGRATED_FLAG, _OLD_INDEX, _PUBLIC_DIR,
)


@pytest.fixture(autouse=True)
def isolated_index(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "PROJECTS.md"))
    # Redirect migration paths into tmp_path so tests are hermetic.
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")


def test_load_empty():
    assert load_projects() == []


def test_save_and_load():
    save_project("myapp", "/home/user/myapp")
    projects = load_projects()
    assert len(projects) == 1
    assert projects[0]["name"] == "myapp"
    assert projects[0]["path"] == "/home/user/myapp"
    assert projects[0]["description"] == ""


def test_save_with_description():
    save_project("myapp", "/home/user/myapp", "A great app")
    projects = load_projects()
    assert projects[0]["description"] == "A great app"


def test_save_multiple():
    save_project("alpha", "/path/alpha")
    save_project("beta", "/path/beta", "Beta project")
    projects = load_projects()
    assert len(projects) == 2
    assert projects[0]["name"] == "alpha"
    assert projects[1]["name"] == "beta"
    assert projects[1]["description"] == "Beta project"


def test_save_updates_existing():
    save_project("myapp", "/old/path")
    save_project("myapp", "/new/path")
    projects = load_projects()
    assert len(projects) == 1
    assert projects[0]["path"] == "/new/path"


def test_save_updates_description():
    save_project("myapp", "/path", "old desc")
    save_project("myapp", "/path", "new desc")
    assert load_projects()[0]["description"] == "new desc"


def test_set_project_path():
    save_project("myapp", "/old/path")
    result = set_project_path("myapp", "/new/path")
    assert result is True
    assert load_projects()[0]["path"] == "/new/path"


def test_set_project_path_not_found():
    result = set_project_path("nope", "/x")
    assert result is False


def test_roundtrip_preserves_all_fields():
    save_project("proj-a", "/a", "desc a")
    save_project("proj-b", "/b")
    save_project("proj-c", "/c", "desc c")
    projects = load_projects()
    assert [(p["name"], p["path"], p["description"]) for p in projects] == [
        ("proj-a", "/a", "desc a"),
        ("proj-b", "/b", ""),
        ("proj-c", "/c", "desc c"),
    ]


# ── Migration tests ───────────────────────────────────────────────────────────

def _write_old(tmp_path, projects):
    old = tmp_path / "old_PROJECTS.md"
    _write(projects, old)
    return old


def test_migration_copies_old_when_new_absent(tmp_path, monkeypatch):
    """Old file exists, new file does not → copy old into new."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "public" / "PROJECTS.md"))

    _write([ {"name": "myapp", "path": "/p", "description": "my desc"} ],
           tmp_path / "old_PROJECTS.md")

    projects = load_projects()
    assert len(projects) == 1
    assert projects[0]["description"] == "my desc"
    assert (tmp_path / "public" / ".migrated").exists()


def test_migration_backfills_missing_descriptions(tmp_path, monkeypatch):
    """New file exists (p-launch created, no desc) + old file has desc → merge."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")
    new_path = tmp_path / "public" / "PROJECTS.md"
    monkeypatch.setenv("TODO_INDEX_PATH", str(new_path))

    # p-launch created the new file without description
    new_path.parent.mkdir(parents=True, exist_ok=True)
    _write([{"name": "myapp", "path": "/p", "description": ""}], new_path)
    # Old file has description
    _write([{"name": "myapp", "path": "/p", "description": "restored desc"}],
           tmp_path / "old_PROJECTS.md")

    projects = load_projects()
    assert projects[0]["description"] == "restored desc"


def test_migration_skips_if_flag_exists(tmp_path, monkeypatch):
    """Migration does not run again once .migrated flag is present."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    flag = tmp_path / "public" / ".migrated"
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", flag)
    new_path = tmp_path / "public" / "PROJECTS.md"
    monkeypatch.setenv("TODO_INDEX_PATH", str(new_path))

    flag.parent.mkdir(parents=True, exist_ok=True)
    flag.touch()
    # Old file has content that should NOT bleed into new file (flag prevents it)
    _write([{"name": "ghost", "path": "/g", "description": "ghost"}],
           tmp_path / "old_PROJECTS.md")

    assert load_projects() == []


def test_migration_no_old_file_marks_done(tmp_path, monkeypatch):
    """No old file → migration marks done immediately, load returns []."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "nonexistent.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "public" / "PROJECTS.md"))

    assert load_projects() == []
    assert (tmp_path / "public" / ".migrated").exists()


def test_migration_preserves_existing_description(tmp_path, monkeypatch):
    """New file already has a description → keep it, don't overwrite from old."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")
    new_path = tmp_path / "public" / "PROJECTS.md"
    monkeypatch.setenv("TODO_INDEX_PATH", str(new_path))

    new_path.parent.mkdir(parents=True, exist_ok=True)
    _write([{"name": "myapp", "path": "/p", "description": "new desc"}], new_path)
    _write([{"name": "myapp", "path": "/p", "description": "old desc"}],
           tmp_path / "old_PROJECTS.md")

    projects = load_projects()
    assert projects[0]["description"] == "new desc"


def test_migration_old_file_empty_marks_done(tmp_path, monkeypatch):
    """Old file exists but has no entries → still mark migrated, no crash."""
    monkeypatch.setattr("todo.projects_index._OLD_INDEX", tmp_path / "old_PROJECTS.md")
    monkeypatch.setattr("todo.projects_index._PUBLIC_DIR", tmp_path / "public")
    monkeypatch.setattr("todo.projects_index._MIGRATED_FLAG", tmp_path / "public" / ".migrated")
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "public" / "PROJECTS.md"))

    # Old file exists but contains no project entries (e.g. just a header).
    (tmp_path / "old_PROJECTS.md").write_text("# Project Index\n", encoding="utf-8")

    assert load_projects() == []
    assert (tmp_path / "public" / ".migrated").exists()

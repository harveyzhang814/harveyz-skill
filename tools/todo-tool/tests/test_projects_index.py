import pytest
from todo.projects_index import load_projects, save_project, set_project_path, _write, get_index_path


@pytest.fixture(autouse=True)
def isolated_index(tmp_path, monkeypatch):
    monkeypatch.setenv("TODO_INDEX_PATH", str(tmp_path / "PROJECTS.md"))


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

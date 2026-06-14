import pytest
from textual.app import App, ComposeResult
from textual.widgets import ListItem

from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task
from hub.tui.panels.projects import ProjectsPanel


def _make_app(db: HubDB) -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield ProjectsPanel(db)
    return _App()


async def test_projects_panel_empty(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        items = pilot.app.query_one(ProjectsPanel).query(ListItem)
        assert len(items) == 0


async def test_projects_panel_shows_projects(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "alpha", path="/tmp/alpha")
    add_project(db, "beta", path="/tmp/beta")
    async with _make_app(db).run_test() as pilot:
        items = pilot.app.query_one(ProjectsPanel).query(ListItem)
        assert len(items) == 2


async def test_projects_panel_posts_selected_message(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "myrepo", path="/tmp/myrepo")
    received: list[ProjectsPanel.ProjectSelected] = []

    class _App(App):
        def compose(self) -> ComposeResult:
            yield ProjectsPanel(db)
        def on_projects_panel_project_selected(self, msg: ProjectsPanel.ProjectSelected):
            received.append(msg)

    async with _App().run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        panel.query_one("ListView").focus()
        await pilot.press("down")
        await pilot.pause()

    assert any(m.name == "myrepo" for m in received)


async def test_projects_panel_shows_task_count(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="do something", project="proj")
    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        from textual.widgets import Label
        labels = panel.query(Label)
        text = " ".join(str(l.content) for l in labels)
        assert "proj" in text

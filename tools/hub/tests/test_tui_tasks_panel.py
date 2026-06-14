import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, ListItem

from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task, list_tasks
from hub.tui.panels.tasks import TasksPanel


def _make_app(db: HubDB) -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield TasksPanel(db)
    return _App()


async def test_tasks_panel_mounts(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        assert pilot.app.query_one(TasksPanel) is not None


async def test_tasks_panel_shows_tasks(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Task A", project="proj")
    add_task(db, title="Task B", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        items = panel.query(ListItem)
        assert len(items) == 2


async def test_tasks_panel_toggle_done(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Finish me", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.query_one("ListView").focus()
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()

    tasks = list_tasks(db, project="proj")
    assert tasks[0]["status"] == "done"


async def test_tasks_panel_new_task_input_appears(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.focus()
        await pilot.press("n")
        await pilot.pause()
        assert len(panel.query(Input)) == 1

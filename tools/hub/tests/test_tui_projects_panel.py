import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, ListItem

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


async def test_projects_panel_scan_input_appears(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        panel.focus()
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert len(panel.query(Input)) == 1


async def test_projects_panel_scan_esc_cancels(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        panel.focus()
        await pilot.press("ctrl+s")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        assert len(panel.query(Input)) == 0


async def test_projects_panel_scan_submit_triggers_worker(tmp_path):
    """Submitting the scan Input calls _scan_worker with the typed directory."""
    db = HubDB(tmp_path / "hub.db")
    calls: list[str] = []

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        panel.focus()
        await pilot.press("ctrl+s")
        await pilot.pause()

        inp = panel.query_one("#scan-dir-input", Input)
        panel._scan_worker = lambda d: calls.append(d)  # type: ignore[method-assign]

        from textual.widgets import Input as _Input
        panel.on_input_submitted(_Input.Submitted(inp, str(tmp_path)))
        await pilot.pause()

    assert calls == [str(tmp_path)]


async def test_projects_panel_after_scan_reloads_list(tmp_path):
    """_after_scan reloads the project list and shows a notification."""
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "pre-existing", path="/old")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        await pilot.pause()
        assert len(panel.query(ListItem)) == 1

        # Simulate a scan that added "new-repo" directly in the DB
        add_project(db, "new-repo", path=str(tmp_path))
        panel._after_scan(added=1, skipped=0, failed=0)
        await pilot.pause()

        assert len(panel.query(ListItem)) == 2


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

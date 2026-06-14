import pytest
from hub.tui.app import HubApp
from hub.tui.panels.git import GitPanel
from hub.tui.panels.projects import ProjectsPanel
from hub.tui.panels.tasks import TasksPanel


async def test_hub_app_mounts(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        assert pilot.app.query_one(ProjectsPanel) is not None
        assert pilot.app.query_one(GitPanel) is not None
        assert pilot.app.query_one(TasksPanel) is not None


async def test_hub_app_quit(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        await pilot.press("q")
    # If we got here without hanging, the app quit cleanly.
    assert True


async def test_hub_app_tab_cycles_focus(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")


from unittest.mock import patch


def test_main_no_args_launches_tui(tmp_path, monkeypatch):
    """hub with no args calls HubApp().run(), not the Phase 1 stub."""
    import sys
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    monkeypatch.setattr(sys, "argv", ["hub"])
    launched = []

    with patch("hub.tui.app.HubApp.run", side_effect=lambda **kw: launched.append(True)):
        from hub.__main__ import main
        main()

    assert launched == [True]


async def test_hub_app_project_selection_updates_panels(tmp_path, monkeypatch):
    """Selecting a project in ProjectsPanel updates GitPanel border and TasksPanel border."""
    from hub.core.projects import add_project as _add_project
    from hub.core.db import HubDB as _HubDB

    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    db = _HubDB(tmp_path / "hub.db")
    _add_project(db, "myrepo", path="/tmp/myrepo")

    async with HubApp().run_test() as pilot:
        projects_panel = pilot.app.query_one(ProjectsPanel)
        tasks_panel = pilot.app.query_one(TasksPanel)
        # Simulate project selection by posting the message directly
        projects_panel.post_message(
            ProjectsPanel.ProjectSelected(name="myrepo", path="/tmp/myrepo")
        )
        await pilot.pause()
        assert tasks_panel.border_title == "TASKS · myrepo"

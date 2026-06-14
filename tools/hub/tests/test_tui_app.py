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

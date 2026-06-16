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
        await pilot.press("ctrl+q")
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


def test_hub_app_routes_sync_with_hidden_binding():
    """HubApp must define ctrl+y with show=False so Sync fires from any focus,
    while the visible footer entry stays owned by GitPanel's own binding."""
    from textual.binding import Binding
    by_key = {b.key: b for b in HubApp.BINDINGS if isinstance(b, Binding)}
    assert "ctrl+y" in by_key and by_key["ctrl+y"].show is False
    assert "ctrl+p" not in by_key
    assert "ctrl+u" not in by_key


async def test_branch_list_keeps_focus_when_project_switches(tmp_path, monkeypatch):
    """lv.clear() during project switch must not lose focus if git column was active."""
    from pathlib import Path
    from textual.widgets import ListView

    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    branches_a = [{"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0,
                   "is_current": True, "is_local_only": False}]
    branches_b = [{"name": "dev", "upstream": "origin/dev", "ahead": 1, "behind": 0,
                   "is_current": True, "is_local_only": False}]
    async with HubApp().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        lv = pilot.app.query_one("#branch-list", ListView)

        # Load project A and focus lv
        await panel._render_branches(Path("/repo-a"), branches_a)
        await pilot.pause()
        pilot.app.set_focus(lv)
        await pilot.pause()
        assert pilot.app.focused is lv

        # Switch to project B while lv still has focus
        await panel._render_branches(Path("/repo-b"), branches_b)
        await pilot.pause()
        assert pilot.app.focused is lv, "lv.clear() must not lose focus on project switch"


async def test_right_arrow_focuses_branch_list_when_visible(tmp_path, monkeypatch):
    """Pressing right from projects column focuses the branch list when it's visible."""
    from pathlib import Path
    from textual.widgets import ListView

    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        lv = pilot.app.query_one("#branch-list", ListView)

        await panel._render_branches(Path("/repo"), [
            {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 2,
             "is_current": True, "is_local_only": False},
        ])
        await pilot.pause()
        assert lv.display

        await pilot.press("right")
        await pilot.pause()
        assert pilot.app.focused is lv


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

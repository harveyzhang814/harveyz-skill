import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import ListView, Static

from hub.tui.panels.git import GitPanel, BranchItem, SectionHeader


def _make_app() -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield GitPanel()
    return _App()


async def test_git_panel_mounts():
    async with _make_app().run_test() as pilot:
        assert pilot.app.query_one(GitPanel) is not None


async def test_git_panel_shows_placeholder_before_project():
    async with _make_app().run_test() as pilot:
        placeholder = pilot.app.query_one("#git-placeholder", Static)
        assert placeholder.display
        assert "Select a project" in str(placeholder.content)


async def test_git_panel_listview_hidden_before_project():
    async with _make_app().run_test() as pilot:
        lv = pilot.app.query_one("#branch-list", ListView)
        assert not lv.display


async def test_git_panel_refresh_nonexistent_path():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel.refresh_project(Path("/nonexistent/path/that/does/not/exist"))
        await pilot.pause()
        placeholder = pilot.app.query_one("#git-placeholder", Static)
        assert placeholder.display
        assert "No valid path" in str(placeholder.content)


async def test_branch_item_stores_data():
    b = {
        "name": "main", "upstream": "origin/main",
        "ahead": 0, "behind": 0,
        "is_current": True, "is_local_only": False,
    }
    item = BranchItem(b)
    assert item.branch_data == b


async def test_section_header_stores_title():
    h = SectionHeader("WITH REMOTE")
    assert h._title == "WITH REMOTE"


async def test_git_panel_render_branches_shows_listview():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        assert lv.display
        assert not pilot.app.query_one("#git-placeholder", Static).display


async def test_git_panel_render_branches_border_title():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        assert "harveyz-skill" in panel.border_title


async def test_git_panel_both_sections_present():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 2
        branch_items = list(lv.query(BranchItem))
        assert len(branch_items) == 2


async def test_git_panel_omits_local_section_when_empty():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 1


async def test_git_panel_omits_remote_section_when_empty():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 1

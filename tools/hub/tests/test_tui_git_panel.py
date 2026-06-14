import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import Static

from hub.tui.panels.git import GitPanel


def _make_app() -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield GitPanel()
    return _App()


async def test_git_panel_mounts():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        assert panel is not None


async def test_git_panel_shows_placeholder_before_project():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        content = panel.query_one("#git-content", Static)
        text = str(content.content)
        assert "Select a project" in text


async def test_git_panel_refresh_nonexistent_path():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel.refresh_project(Path("/nonexistent/path/that/does/not/exist"))
        await pilot.pause()
        content = str(panel.query_one("#git-content", Static).content)
        assert "No valid path" in content


async def test_git_panel_refresh_valid_path():
    """_render_git with a real git repo updates border_title and content."""
    from hub.tui.git import get_branches, get_recent_commits, get_working_tree

    # Use the harveyz-skill repo itself as a real git repo
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")

    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        # Call _render_git directly (the render step after the background worker)
        branches = get_branches(repo_path)
        current = next((b for b in branches if b["is_current"]), None)
        wt = get_working_tree(repo_path)
        commits = get_recent_commits(repo_path, n=5)
        panel._render_git(repo_path, current, wt, commits)
        await pilot.pause()
        border = panel.border_title
        assert "harveyz-skill" in border

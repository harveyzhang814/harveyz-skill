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

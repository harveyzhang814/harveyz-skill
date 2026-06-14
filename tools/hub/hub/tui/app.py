from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer

from hub.core.db import HubDB
from hub.tui.git import launch_project
from hub.tui.panels.git import GitPanel
from hub.tui.panels.projects import ProjectsPanel
from hub.tui.panels.tasks import TasksPanel


class HubApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    Footer {
        height: 1;
    }
    """

    BINDINGS = [
        Binding("tab", "cycle_focus", "Switch col", show=True),
        Binding("f", "fetch", "Fetch", show=True),
        Binding("enter", "open_project", "Open", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.db = HubDB()

    def compose(self) -> ComposeResult:
        with Container(id="main"):
            yield ProjectsPanel(self.db, id="col-projects")
            yield GitPanel(id="col-git")
            yield TasksPanel(self.db, id="col-tasks")
        yield Footer()

    def on_projects_panel_project_selected(
        self, message: ProjectsPanel.ProjectSelected
    ) -> None:
        path = Path(message.path) if message.path else None
        self.query_one(GitPanel).refresh_project(path)
        self.query_one(TasksPanel).refresh_project(message.name)

    def action_cycle_focus(self) -> None:
        panels = [
            self.query_one("#col-projects"),
            self.query_one("#col-git"),
            self.query_one("#col-tasks"),
        ]
        for i, p in enumerate(panels):
            if p.has_focus_within or p == self.focused:
                panels[(i + 1) % len(panels)].focus()
                return
        panels[0].focus()

    def action_fetch(self) -> None:
        self.query_one(GitPanel).action_fetch()

    def action_open_project(self) -> None:
        panel = self.query_one(ProjectsPanel)
        if not panel.selected_path:
            return
        cursor_ok, ghostty_ok, err = launch_project(Path(panel.selected_path))
        parts = [
            "Cursor ✓" if cursor_ok else "Cursor ⚠",
            "Ghostty ✓" if ghostty_ok else f"Ghostty ⚠ {err}",
        ]
        self.notify(", ".join(parts))

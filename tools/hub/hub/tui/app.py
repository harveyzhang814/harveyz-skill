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
        Binding("tab", "cycle_focus", "Tab col", show=False),
        Binding("left", "prev_col", "← Col", show=True),
        Binding("right", "next_col", "→ Col", show=True),
        Binding("ctrl+f", "fetch", "Fetch", show=True),
        Binding("enter", "open_project", "Open", show=True),
        Binding("ctrl+q", "quit", "Quit", show=True),
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

    def _shift_focus(self, delta: int) -> None:
        panels = [
            self.query_one("#col-projects"),
            self.query_one("#col-git"),
            self.query_one("#col-tasks"),
        ]
        targets = [
            self.query_one("#projects-list"),
            self.query_one("#col-git"),
            self.query_one("#tasks-list"),
        ]
        for i, p in enumerate(panels):
            if p.has_focus_within or p == self.focused:
                self.set_focus(targets[(i + delta) % len(targets)])
                return
        self.set_focus(targets[0])

    def action_cycle_focus(self) -> None:
        self._shift_focus(1)

    def action_next_col(self) -> None:
        self._shift_focus(1)

    def action_prev_col(self) -> None:
        self._shift_focus(-1)

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

from pathlib import Path

from collections import defaultdict
from itertools import groupby

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Footer
from textual.widgets._footer import FooterKey, FooterLabel, KeyGroup

from hub.core.db import HubDB
from hub.tui.git import launch_project
from hub.tui.panels.git import GitPanel
from hub.tui.panels.projects import ProjectsPanel
from hub.tui.panels.tasks import TasksPanel


_ACTION_CATEGORY = {
    "prev_col": "nav",
    "next_col": "nav",
    "cycle_focus": "nav",
    "open_project": "project",
    "fetch": "git",
    "sync": "git",
    "quit": "system",
}


class StyledFooter(Footer):
    """Footer that tags each FooterKey with a category class at construction."""

    def compose(self) -> ComposeResult:
        if not self._bindings_ready:
            return
        active_bindings = self.screen.active_bindings
        bindings = [
            (binding, enabled, tooltip)
            for (_, binding, enabled, tooltip) in active_bindings.values()
            if binding.show
        ]
        action_to_bindings: defaultdict[str, list] = defaultdict(list)
        for binding, enabled, tooltip in bindings:
            action_to_bindings[binding.action].append((binding, enabled, tooltip))

        self.styles.grid_size_columns = len(action_to_bindings)

        def _cat_class(action: str) -> str:
            cat = _ACTION_CATEGORY.get(action)
            return f"-cat-{cat}" if cat else ""

        for group, multi_iter in groupby(
            action_to_bindings.values(),
            lambda mb: mb[0][0].group,
        ):
            multi_list = list(multi_iter)
            if group is not None and len(multi_list) > 1:
                with KeyGroup(classes="-compact" if group.compact else ""):
                    for mb in multi_list:
                        binding, enabled, tooltip = mb[0]
                        yield FooterKey(
                            binding.key,
                            self.app.get_key_display(binding),
                            "",
                            binding.action,
                            disabled=not enabled,
                            tooltip=tooltip or binding.description,
                            classes=f"-grouped {_cat_class(binding.action)}".strip(),
                        ).data_bind(compact=Footer.compact)
                yield FooterLabel(group.description)
            else:
                for mb in multi_list:
                    binding, enabled, tooltip = mb[0]
                    yield FooterKey(
                        binding.key,
                        self.app.get_key_display(binding),
                        binding.description,
                        binding.action,
                        disabled=not enabled,
                        tooltip=tooltip,
                        classes=_cat_class(binding.action),
                    ).data_bind(compact=Footer.compact)
        if self.show_command_palette and self.app.ENABLE_COMMAND_PALETTE:
            try:
                _node, binding, enabled, tooltip = active_bindings[
                    self.app.COMMAND_PALETTE_BINDING
                ]
            except KeyError:
                pass
            else:
                yield FooterKey(
                    binding.key,
                    self.app.get_key_display(binding),
                    binding.description,
                    binding.action,
                    classes="-command-palette",
                    disabled=not enabled,
                    tooltip=binding.tooltip or binding.description,
                )


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
    FooterKey.-cat-nav .footer-key--key {
        background: $primary 30%;
        color: $primary-lighten-2;
    }
    FooterKey.-cat-nav .footer-key--description {
        color: $primary-lighten-2;
    }
    FooterKey.-cat-project .footer-key--key {
        background: $success 30%;
        color: $success-lighten-2;
    }
    FooterKey.-cat-project .footer-key--description {
        color: $success-lighten-2;
    }
    FooterKey.-cat-git .footer-key--key {
        background: $warning 30%;
        color: $warning-lighten-2;
    }
    FooterKey.-cat-git .footer-key--description {
        color: $warning-lighten-2;
    }
    FooterKey.-cat-system {
        dock: right;
    }
    FooterKey.-cat-system .footer-key--key {
        background: $error 30%;
        color: $error-lighten-2;
    }
    FooterKey.-cat-system .footer-key--description {
        color: $error-lighten-2;
    }
    """

    BINDINGS = [
        Binding("tab", "cycle_focus", "Tab col", show=False),
        Binding("left", "prev_col", "← Col", show=True),
        Binding("right", "next_col", "→ Col", show=True),
        Binding("enter", "open_project", "Open", show=True),
        Binding("ctrl+f", "fetch", "Fetch", show=True),
        Binding("ctrl+y", "sync", "Sync", show=False),
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
        yield StyledFooter()

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
        lv = self.query_one("#branch-list")
        targets = [
            self.query_one("#projects-list"),
            lv if lv.display else self.query_one("#col-git"),
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

    def action_sync(self) -> None:
        self.query_one(GitPanel).action_sync()

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

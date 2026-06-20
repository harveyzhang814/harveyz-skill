import os
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from hub.core.db import HubDB
from hub.core.projects import list_projects, remove_project, scan_projects
from hub.core.tasks import list_tasks

_DEFAULT_MD = Path.home() / ".hskill" / "public" / "PROJECTS.md"


class ProjectsPanel(Widget):
    BINDINGS = [
        Binding("ctrl+s", "scan_action", "Scan", show=True),
        Binding("ctrl+d", "remove_action", "Remove", show=True),
        Binding("enter", "open_selected", show=False, priority=True),
    ]

    DEFAULT_CSS = """
    ProjectsPanel {
        width: 30;
        height: 100%;
        border: solid $surface-lighten-2;
    }
    ProjectsPanel:focus-within {
        border: solid $accent;
    }
    ProjectsPanel Input {
        dock: bottom;
    }
    """

    class ProjectSelected(Message):
        def __init__(self, name: str, path: str) -> None:
            super().__init__()
            self.name = name
            self.path = path

    def __init__(self, db: HubDB, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self.selected_name: str | None = None
        self.selected_path: str | None = None
        self._projects: list[dict] = []

    def compose(self) -> ComposeResult:
        yield ListView(id="projects-list")

    def on_mount(self) -> None:
        self.border_title = "PROJECTS"
        self._reload()

    def _reload(self) -> None:
        self._projects = list_projects(self.db)
        lst = self.query_one(ListView)
        lst.clear()
        for p in self._projects:
            todo_count = len(list_tasks(self.db, project=p["name"], status="todo"))
            badge = f"  [dim]{todo_count}[/]" if todo_count else ""
            lst.append(ListItem(Label(f"{p['name']}{badge}", markup=True)))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = event.control.index
        if idx is not None and idx < len(self._projects):
            p = self._projects[idx]
            self.selected_name = p["name"]
            self.selected_path = p.get("path", "")
            self.post_message(self.ProjectSelected(p["name"], p.get("path", "")))

    def action_open_selected(self) -> None:
        if self.query("#scan-dir-input"):
            return
        self.app.action_open_project()

    def action_scan_action(self) -> None:
        if self.query("#scan-dir-input"):
            return
        inp = Input(
            placeholder="Directory to scan… (Enter to scan, Esc to cancel)",
            id="scan-dir-input",
        )
        self.mount(inp)
        inp.focus()

    def action_remove_action(self) -> None:
        if self.query("#scan-dir-input"):
            return
        if not self.selected_name:
            return
        name = self.selected_name
        task_count = len(list_tasks(self.db, project=name))
        if task_count:
            self.app.notify(
                f"'{name}' has {task_count} task(s) — remove them first",
                severity="error",
            )
            return
        self._remove_worker(name)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "scan-dir-input":
            return
        directory = event.value.strip()
        event.input.remove()
        if directory:
            self._scan_worker(directory)

    def on_key(self, event) -> None:
        if self.query("#scan-dir-input") and event.key == "escape":
            self.query_one("#scan-dir-input").remove()
            event.prevent_default()

    @work(thread=True)
    def _scan_worker(self, directory: str) -> None:
        md = Path(os.environ["HUB_MD_PATH"]) if "HUB_MD_PATH" in os.environ else _DEFAULT_MD
        result = scan_projects([directory], self.db, md_path=md)
        a = len(result["added"])
        s = len(result["skipped"])
        f = len(result["failed"])
        self.app.call_from_thread(self._after_scan, a, s, f)

    def _after_scan(self, added: int, skipped: int, failed: int) -> None:
        self._reload()
        self.app.notify(f"Scanned: {added} added, {skipped} skipped, {failed} failed")

    @work(thread=True)
    def _remove_worker(self, name: str) -> None:
        md = Path(os.environ["HUB_MD_PATH"]) if "HUB_MD_PATH" in os.environ else _DEFAULT_MD
        try:
            result = remove_project(self.db, name, md_path=md, force=False)
            self.app.call_from_thread(self._after_remove, name, None)
        except Exception as e:
            self.app.call_from_thread(self._after_remove, name, str(e))

    def _after_remove(self, name: str, error: str | None) -> None:
        if error:
            self.app.notify(f"Failed to remove '{name}': {error}", severity="error")
            return
        self._reload()
        self.app.notify(f"Removed '{name}'")

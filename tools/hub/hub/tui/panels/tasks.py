from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from hub.core.db import HubDB
from hub.core.projects import get_project_path
from hub.core.tasks import add_task, delete_task, list_tasks, mark_done, update_task
from hub.core.todo_sync import sync_project


class TasksPanel(Widget):
    BINDINGS = [
        Binding("ctrl+n", "new_task", "New", show=True),
        Binding("ctrl+r", "sync_from_file", "Sync", show=True),
        Binding("space", "toggle_done", "Done", show=True),
        Binding("ctrl+d", "delete_task_action", "Delete", show=True),
    ]

    DEFAULT_CSS = """
    TasksPanel {
        width: 1fr;
        height: 100%;
        border: solid $surface-lighten-2;
    }
    TasksPanel:focus-within {
        border: solid $accent;
    }
    TasksPanel Input {
        dock: bottom;
    }
    """

    def __init__(self, db: HubDB, **kwargs) -> None:
        super().__init__(**kwargs)
        self.db = db
        self._project: str | None = None
        self._tasks: list[dict] = []
        self._confirm_delete: int | None = None

    def compose(self) -> ComposeResult:
        yield ListView(id="tasks-list")

    def on_mount(self) -> None:
        self.border_title = "TASKS"

    def refresh_project(self, project_name: str) -> None:
        self._project = project_name
        self._confirm_delete = None
        self._reload()

    def _reload(self) -> None:
        if not self._project:
            return
        self._tasks = list_tasks(self.db, project=self._project)
        lst = self.query_one(ListView)
        lst.clear()

        todo = [t for t in self._tasks if t["status"] == "todo"]
        done = [t for t in self._tasks if t["status"] == "done"]

        for t in todo:
            pri = f"[dim]{t['priority']}[/]"
            date = f"[dim]{t['created_at'][:10]}[/]"
            item = ListItem(
                Label(f"☐ {t['title']}  {pri}  {date}", markup=True),
            )
            item.task_id = t["id"]
            lst.append(item)
        if done:
            sep = ListItem(Label("[dim]── DONE ──[/]", markup=True))
            sep.task_id = None
            lst.append(sep)
            for t in done:
                date = f"{t['created_at'][:10]}"
                item = ListItem(
                    Label(f"[dim]☑ {t['title']}  {date}[/]", markup=True),
                )
                item.task_id = t["id"]
                lst.append(item)

        self.border_title = f"TASKS · {self._project}"

    def _selected_task(self) -> dict | None:
        lst = self.query_one(ListView)
        item = lst.highlighted_child
        if item is None:
            return None
        task_id = getattr(item, "task_id", None)
        if task_id is None:
            return None
        return next((t for t in self._tasks if t["id"] == task_id), None)

    def action_toggle_done(self) -> None:
        task = self._selected_task()
        if not task:
            return
        if task["status"] == "todo":
            mark_done(self.db, task["id"])
        else:
            update_task(self.db, task["id"], status="todo")
        self._reload()

    def action_delete_task_action(self) -> None:
        task = self._selected_task()
        if not task:
            return
        if self._confirm_delete == task["id"]:
            delete_task(self.db, task["id"])
            self._confirm_delete = None
            self._reload()
        else:
            self._confirm_delete = task["id"]
            self.app.notify(
                f"Press D again to delete '{task['title']}'",
                severity="warning",
            )

    def action_sync_from_file(self) -> None:
        if not self._project:
            return
        path = get_project_path(self.db, self._project)
        if not path:
            self.app.notify("No local path configured for this project", severity="warning")
            return
        try:
            result = sync_project(self.db, self._project, path)
        except Exception as exc:
            self.app.notify(f"Sync failed: {exc}", severity="error")
            return
        self._reload()
        self.app.notify(
            f"Synced: {result['imported']} imported, {result['updated']} updated"
        )

    def action_new_task(self) -> None:
        if not self._project or self.query("#new-task-input"):
            return
        inp = Input(
            placeholder="New task title… (Enter to save, Esc to cancel)",
            id="new-task-input",
        )
        self.mount(inp)
        inp.focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "new-task-input":
            return
        title = event.value.strip()
        if title and self._project:
            try:
                add_task(self.db, title=title, project=self._project)
            except ValueError as e:
                self.app.notify(str(e), severity="error")
        event.input.remove()
        self._reload()

    def on_key(self, event) -> None:
        if event.key == "escape" and self.query("#new-task-input"):
            self.query("#new-task-input").first().remove()
            event.prevent_default()

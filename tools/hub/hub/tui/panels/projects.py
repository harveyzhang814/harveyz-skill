from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView

from hub.core.db import HubDB
from hub.core.projects import list_projects
from hub.core.tasks import list_tasks


class ProjectsPanel(Widget):
    DEFAULT_CSS = """
    ProjectsPanel {
        width: 30;
        height: 100%;
        border: solid $surface-lighten-2;
    }
    ProjectsPanel:focus-within {
        border: solid $accent;
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

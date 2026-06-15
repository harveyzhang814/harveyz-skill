from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label, Static

from hub.tui.git import fetch_repo, get_branches, is_git_with_remote, pull_branch, push_branch


class SectionHeader(ListItem):
    """Non-interactive section divider row."""

    DEFAULT_CSS = """
    SectionHeader {
        padding: 0 1;
    }
    """

    def __init__(self, title: str) -> None:
        super().__init__()
        self._title = title
        self.disabled = True

    def compose(self) -> ComposeResult:
        yield Label(f"[dim]▸ {self._title}[/]", markup=True)


class BranchItem(ListItem):
    """One branch row in the branch list."""

    def __init__(self, branch: dict) -> None:
        super().__init__()
        self.branch_data = branch

    def compose(self) -> ComposeResult:
        b = self.branch_data
        cur = "[cyan]▶[/] " if b["is_current"] else "  "
        if b["is_local_only"]:
            sym_plain = "local  "
            sym_m = f"[dim]{sym_plain}[/]"
        elif b["ahead"] and b["behind"]:
            sym_plain = f"↑{b['ahead']}↓{b['behind']}".ljust(7)
            sym_m = f"[yellow]{sym_plain}[/]"
        elif b["ahead"]:
            sym_plain = f"↑{b['ahead']}".ljust(7)
            sym_m = f"[yellow]{sym_plain}[/]"
        elif b["behind"]:
            sym_plain = f"↓{b['behind']}".ljust(7)
            sym_m = f"[red]{sym_plain}[/]"
        else:
            sym_plain = "✓      "
            sym_m = f"[green]{sym_plain}[/]"
        name = b["name"]
        remote = f"  [dim]{b['upstream']}[/]" if b.get("upstream") else ""
        yield Label(f"{cur}{sym_m}{name}{remote}", markup=True)


class GitPanel(Widget):
    can_focus = True

    BINDINGS = [
        Binding("ctrl+p", "pull", "Pull", show=True),
        Binding("ctrl+u", "push", "Push", show=True),
    ]

    DEFAULT_CSS = """
    GitPanel {
        width: 44;
        height: 100%;
        border: solid $surface-lighten-2;
        padding: 1 2;
    }
    GitPanel:focus-within {
        border: solid $accent;
    }
    #branch-list {
        height: 1fr;
        border: none;
        padding: 0;
        margin: 0 -2;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._path: Path | None = None
        self._selected_branch: dict | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select a project to see git status.", id="git-placeholder", markup=True)
        lv = ListView(id="branch-list")
        lv.display = False
        yield lv

    def on_mount(self) -> None:
        self.border_title = "GIT"

    def on_focus(self) -> None:
        lv = self.query_one("#branch-list", ListView)
        if lv.display:
            lv.focus()

    def _selected_branch_data(self) -> dict | None:
        return self._selected_branch

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, BranchItem):
            self._selected_branch = event.item.branch_data
        else:
            self._selected_branch = None

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if action not in ("pull", "push"):
            return None
        b = self._selected_branch_data()
        if b is None:
            return False
        if action == "pull":
            return not b["is_local_only"] and b["behind"] > 0 and b["ahead"] == 0
        if action == "push":
            return not b["is_local_only"] and b["ahead"] > 0 and b["behind"] == 0
        return None

    def refresh_project(self, path: Path | None) -> None:
        self._path = path
        if path is None or not path.exists():
            ph = self.query_one("#git-placeholder", Static)
            ph.update("No valid path.")
            ph.display = True
            self.query_one("#branch-list", ListView).display = False
            self.border_title = "GIT"
            return
        self._load_git_info(path)

    @work(thread=True)
    def _load_git_info(self, path: Path) -> None:
        branches = get_branches(path)
        self.app.call_from_thread(self._render_branches, path, branches)

    def _render_branches(self, path: Path, branches: list[dict]) -> None:
        placeholder = self.query_one("#git-placeholder", Static)
        lv = self.query_one("#branch-list", ListView)
        placeholder.display = False
        lv.display = True
        lv.clear()

        if not branches:
            placeholder.update("Not a git repository.")
            placeholder.display = True
            lv.display = False
            self.border_title = "GIT"
            return

        with_remote = [b for b in branches if not b["is_local_only"]]
        local_only = [b for b in branches if b["is_local_only"]]

        current_lv_idx = 0
        idx = 0

        if with_remote:
            lv.append(SectionHeader("WITH REMOTE"))
            idx += 1
            for b in with_remote:
                lv.append(BranchItem(b))
                if b["is_current"]:
                    current_lv_idx = idx
                idx += 1

        if local_only:
            lv.append(SectionHeader("LOCAL ONLY"))
            idx += 1
            for b in local_only:
                lv.append(BranchItem(b))
                if b["is_current"]:
                    current_lv_idx = idx
                idx += 1

        if branches:
            lv.index = current_lv_idx

        self.border_title = f"GIT — {path.name}"

    def action_fetch(self) -> None:
        if self._path and is_git_with_remote(self._path):
            self._fetch_worker(self._path)

    @work(thread=True)
    def _fetch_worker(self, path: Path) -> None:
        fetch_repo(path)
        self.app.call_from_thread(self.refresh_project, path)
        self.app.call_from_thread(self.app.notify, f"Fetched {path.name}")

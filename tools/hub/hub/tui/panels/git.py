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
        Binding("ctrl+y", "sync", "Sync", show=True),
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
            # lv.focus() inside on_focus is a no-op in Textual 8.x; defer to next tick.
            self.call_later(self.app.set_focus, lv)

    def _selected_branch_data(self) -> dict | None:
        return self._selected_branch

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if isinstance(event.item, BranchItem):
            self._selected_branch = event.item.branch_data
        else:
            self._selected_branch = None
        self.refresh_bindings()

    def _sync_direction(self, b: dict | None) -> str | None:
        """Return 'pull' / 'push' / None depending on branch state."""
        if b is None or b["is_local_only"]:
            return None
        if b["behind"] > 0 and b["ahead"] == 0:
            return "pull"
        if b["ahead"] > 0 and b["behind"] == 0:
            return "push"
        return None

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        if action == "sync":
            return True
        if action in ("pull", "push"):
            direction = self._sync_direction(self._selected_branch_data())
            return direction == action
        return None

    def action_sync(self) -> None:
        if not self._path:
            self.app.notify("No project selected", severity="warning")
            return
        b = self._selected_branch_data()
        if not b:
            self.app.notify("No branch selected", severity="warning")
            return
        if b["is_local_only"]:
            self.app.notify(
                f"{b['name']} is local-only — nothing to sync", severity="warning"
            )
            return
        if b["ahead"] > 0 and b["behind"] > 0:
            self.app.notify(
                f"{b['name']} is diverged — pull/rebase, then push manually",
                severity="warning",
            )
            return
        if b["ahead"] == 0 and b["behind"] == 0:
            self.app.notify(f"{b['name']} is already up to date")
            return
        if b["behind"] > 0:
            self.app.notify(f"Pulling {b['name']}…")
            self._pull_worker(self._path, b["name"])
        else:
            self.app.notify(f"Pushing {b['name']}…")
            self._push_worker(self._path, b["name"])

    def action_pull(self) -> None:
        b = self._selected_branch_data()
        if not b or not self._path:
            return
        self._pull_worker(self._path, b["name"])

    def action_push(self) -> None:
        b = self._selected_branch_data()
        if not b or not self._path:
            return
        self._push_worker(self._path, b["name"])

    @work(thread=True)
    def _pull_worker(self, path: Path, branch: str) -> None:
        msg = pull_branch(path, branch)
        self.app.call_from_thread(self.app.notify, msg)
        self.app.call_from_thread(self.refresh_project, path)

    @work(thread=True)
    def _push_worker(self, path: Path, branch: str) -> None:
        msg = push_branch(path, branch)
        self.app.call_from_thread(self.app.notify, msg)
        self.app.call_from_thread(self.refresh_project, path)

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

    @work(thread=True, group="git-load", exclusive=True)
    def _load_git_info(self, path: Path) -> None:
        branches = get_branches(path)
        self.app.call_from_thread(self._launch_render, path, branches)

    def _launch_render(self, path: Path, branches: list[dict]) -> None:
        self.run_worker(
            self._render_branches(path, branches),
            group="git-render",
            exclusive=True,
        )

    async def _render_branches(self, path: Path, branches: list[dict]) -> None:
        placeholder = self.query_one("#git-placeholder", Static)
        lv = self.query_one("#branch-list", ListView)
        had_focus = lv.has_focus or self.has_focus

        if not branches:
            await lv.clear()
            placeholder.update("Not a git repository.")
            placeholder.display = True
            lv.display = False
            self.border_title = "GIT"
            return

        placeholder.display = False
        lv.display = True
        await lv.clear()

        with_remote = [b for b in branches if not b["is_local_only"]]
        local_only = [b for b in branches if b["is_local_only"]]

        items: list[ListItem] = []
        current_lv_idx = 0
        idx = 0

        if with_remote:
            items.append(SectionHeader("WITH REMOTE"))
            idx += 1
            for b in with_remote:
                items.append(BranchItem(b))
                if b["is_current"]:
                    current_lv_idx = idx
                idx += 1

        if local_only:
            items.append(SectionHeader("LOCAL ONLY"))
            idx += 1
            for b in local_only:
                items.append(BranchItem(b))
                if b["is_current"]:
                    current_lv_idx = idx
                idx += 1

        await lv.extend(items)
        lv.index = current_lv_idx
        self.border_title = f"GIT — {path.name}"

        if had_focus:
            lv.focus()

    def action_fetch(self) -> None:
        if self._path and is_git_with_remote(self._path):
            self._fetch_worker(self._path)

    @work(thread=True)
    def _fetch_worker(self, path: Path) -> None:
        fetch_repo(path)
        self.app.call_from_thread(self.refresh_project, path)
        self.app.call_from_thread(self.app.notify, f"Fetched {path.name}")

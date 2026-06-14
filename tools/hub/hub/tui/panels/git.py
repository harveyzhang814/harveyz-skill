from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from hub.tui.git import (
    fetch_repo,
    get_branches,
    get_recent_commits,
    get_working_tree,
    is_git_with_remote,
)


class GitPanel(Widget):
    DEFAULT_CSS = """
    GitPanel {
        width: 44;
        height: 100%;
        border: solid $surface-lighten-2;
        padding: 1 2;
        overflow-y: auto;
    }
    GitPanel:focus-within {
        border: solid $accent;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Static("Select a project to see git status.", id="git-content", markup=True)

    def on_mount(self) -> None:
        self.border_title = "GIT"

    def refresh_project(self, path: Path | None) -> None:
        self._path = path
        if path is None or not path.exists():
            self.query_one("#git-content", Static).update("No valid path.")
            self.border_title = "GIT"
            return
        self._load_git_info(path)

    @work(thread=True)
    def _load_git_info(self, path: Path) -> None:
        branches = get_branches(path)
        current = next((b for b in branches if b["is_current"]), None)
        wt = get_working_tree(path)
        commits = get_recent_commits(path, n=5)
        self.app.call_from_thread(self._render_git, path, current, wt, commits)

    def _render_git(
        self,
        path: Path,
        current: dict | None,
        wt: dict,
        commits: list[dict],
    ) -> None:
        lines: list[str] = [f"[bold]{path.name}[/]\n"]

        lines.append("[dim]BRANCH[/]")
        if current:
            lines.append(f"  local    [cyan]{current['name']}[/]")
            if current["upstream"]:
                lines.append(f"  tracking [dim]{current['upstream']}[/]")
                if current["ahead"] or current["behind"]:
                    parts = []
                    if current["ahead"]:
                        parts.append(f"[yellow]↑{current['ahead']}[/]")
                    if current["behind"]:
                        parts.append(f"[red]↓{current['behind']}[/]")
                    lines.append(f"  sync     {' '.join(parts)}")
                else:
                    lines.append("  sync     [green]up to date[/]")
            else:
                lines.append("  tracking [dim]none (local only)[/]")
        else:
            lines.append("  [dim]not a git repository[/]")

        lines.append("")
        lines.append("[dim]WORKING TREE[/]")
        total = wt["modified"] + wt["new"] + wt["deleted"]
        if total == 0:
            lines.append("  [green]clean[/]")
        else:
            parts = []
            if wt["modified"]:
                parts.append(f"{wt['modified']} mod")
            if wt["new"]:
                parts.append(f"{wt['new']} new")
            if wt["deleted"]:
                parts.append(f"{wt['deleted']} del")
            lines.append(f"  [yellow]{', '.join(parts)}[/]")

        if commits:
            lines.append("")
            lines.append("[dim]RECENT COMMITS[/]")
            for c in commits:
                msg = c["msg"][:30] + "…" if len(c["msg"]) > 30 else c["msg"]
                lines.append(f"  [dim]{c['sha']}[/] {msg}  [dim]{c['date']}[/]")

        self.query_one("#git-content", Static).update("\n".join(lines))
        self.border_title = f"GIT — {path.name}"

    def action_fetch(self) -> None:
        if self._path and is_git_with_remote(self._path):
            self._fetch_worker(self._path)

    @work(thread=True)
    def _fetch_worker(self, path: Path) -> None:
        fetch_repo(path)
        self.app.call_from_thread(self.refresh_project, path)
        self.app.call_from_thread(self.app.notify, f"Fetched {path.name}")

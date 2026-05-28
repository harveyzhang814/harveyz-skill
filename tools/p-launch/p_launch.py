#!/usr/bin/env python3
"""p-launch v3 — local repository manager (Python + Textual)"""
import re
import subprocess
import shutil
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "p-launch" / "config.zsh"


def read_project_dirs() -> list[Path]:
    """Parse PROJECT_DIRS array from ~/.config/p-launch/config.zsh."""
    if not CONFIG_FILE.exists():
        return [Path.home() / "Projects"]
    content = CONFIG_FILE.read_text()
    match = re.search(r'PROJECT_DIRS\s*=\s*\(([^)]+)\)', content, re.DOTALL)
    if not match:
        return [Path.home() / "Projects"]
    dirs = []
    for token in re.findall(r'\S+', match.group(1)):
        p = Path(token).expanduser()
        if p.exists():
            dirs.append(p)
    return dirs or [Path.home() / "Projects"]


def collect_repos(dirs: list[Path]) -> list[Path]:
    """Find all git repos (direct children with .git) under the given dirs."""
    repos: list[Path] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for child in sorted(d.iterdir()):
            if child.is_dir() and (child / ".git").exists():
                repos.append(child)
    return repos


def is_git_with_remote(path: Path) -> bool:
    r = subprocess.run(
        ["git", "-C", str(path), "remote"],
        capture_output=True, text=True
    )
    return r.returncode == 0 and bool(r.stdout.strip())


def fetch_repo(path: Path) -> None:
    try:
        subprocess.run(
            ["git", "-C", str(path), "fetch", "--all", "-q"],
            capture_output=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        pass


def get_repo_status(path: Path) -> dict:
    """Returns {'symbol': str, 'ahead': int, 'behind': int}."""
    if not is_git_with_remote(path):
        return {"symbol": "·", "ahead": 0, "behind": 0}

    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True
    )
    total_ahead = total_behind = 0
    has_tracking = False
    for line in r.stdout.strip().splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        upstream, track = parts[1], parts[2]
        if not upstream or "gone" in track:
            continue
        has_tracking = True
        if m := re.search(r"ahead (\d+)", track):
            total_ahead += int(m.group(1))
        if m := re.search(r"behind (\d+)", track):
            total_behind += int(m.group(1))

    if not has_tracking:
        return {"symbol": "·", "ahead": 0, "behind": 0}

    symbol = ""
    if total_ahead:
        symbol += f"↑{total_ahead}"
    if total_behind:
        symbol += f"↓{total_behind}"
    if not symbol:
        symbol = "✓"
    return {"symbol": symbol, "ahead": total_ahead, "behind": total_behind}


def get_branches(path: Path) -> list[dict]:
    """List all branches. Each dict has: name, upstream, ahead, behind, is_current, is_local_only."""
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True
    )
    current = cur_r.stdout.strip()

    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True
    )
    branches: list[dict] = []
    for line in r.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|")
        name = parts[0]
        upstream = parts[1] if len(parts) > 1 else ""
        track = parts[2] if len(parts) > 2 else ""
        if upstream and "gone" in track:
            continue
        ahead = behind = 0
        if upstream:
            if m := re.search(r"ahead (\d+)", track):
                ahead = int(m.group(1))
            if m := re.search(r"behind (\d+)", track):
                behind = int(m.group(1))
        branches.append({
            "name": name, "upstream": upstream,
            "ahead": ahead, "behind": behind,
            "is_current": name == current,
            "is_local_only": not bool(upstream),
        })
    return branches


def get_branch_detail(path: Path, branch: str) -> dict:
    """Detailed info for a single branch."""
    def git(*args) -> str:
        r = subprocess.run(["git", "-C", str(path)] + list(args),
                           capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""

    upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    local_sha = git("rev-parse", "--short", branch) or "—"
    remote_sha = git("rev-parse", "--short", upstream) if upstream else "—"
    log = git("log", "-1", "--format=%s|%an|%cr", branch)
    parts = log.split("|", 2) if log else ["", "", ""]
    commit_msg = parts[0] if len(parts) > 0 else ""
    author = parts[1] if len(parts) > 1 else ""
    date = parts[2] if len(parts) > 2 else ""

    ahead = behind = 0
    if upstream:
        track = git("for-each-ref", "--format=%(upstream:track)", f"refs/heads/{branch}")
        if m := re.search(r"ahead (\d+)", track):
            ahead = int(m.group(1))
        if m := re.search(r"behind (\d+)", track):
            behind = int(m.group(1))

    return {
        "name": branch, "upstream": upstream,
        "local_sha": local_sha, "remote_sha": remote_sha,
        "commit_msg": commit_msg, "author": author, "date": date,
        "ahead": ahead, "behind": behind,
        "is_local_only": not bool(upstream),
    }


def pull_branch(path: Path, branch: str) -> str:
    """Pull a single branch. Returns human-readable result."""
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True
    )
    current = cur_r.stdout.strip()

    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True
    )
    if up_r.returncode != 0:
        return "no upstream — nothing to pull"

    if branch == current:
        r = subprocess.run(
            ["git", "-C", str(path), "pull", "--ff-only", "origin", branch],
            capture_output=True, text=True
        )
    else:
        r = subprocess.run(
            ["git", "-C", str(path), "fetch", "origin", f"{branch}:{branch}"],
            capture_output=True, text=True
        )
    return f"✓ pulled {branch}" if r.returncode == 0 else f"⚠ failed to pull {branch}"


def push_branch(path: Path, branch: str) -> str:
    """Push a single branch. Returns human-readable result."""
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True
    )
    if up_r.returncode != 0:
        return "no upstream — branch is local only"

    r = subprocess.run(
        ["git", "-C", str(path), "push", "origin", branch],
        capture_output=True, text=True
    )
    return f"✓ pushed {branch}" if r.returncode == 0 else f"⚠ failed to push {branch}"


def launch_project(path: Path) -> tuple[bool, bool, str]:
    """Open project in Cursor + Ghostty. Returns (cursor_ok, ghostty_ok, ghostty_err)."""
    cursor_ok = False
    ghostty_ok = False
    ghostty_err = "not installed"

    if shutil.which("cursor"):
        subprocess.Popen(["cursor", str(path)])
        cursor_ok = True
    elif Path("/Applications/Cursor.app").exists():
        r = subprocess.run(["/usr/bin/open", "-na", "Cursor", "--args", str(path)])
        cursor_ok = r.returncode == 0

    mdfind = subprocess.run(
        ["mdfind", "kMDItemCFBundleIdentifier == 'com.mitchellh.ghostty'"],
        capture_output=True, text=True
    )
    ghostty_app = (mdfind.stdout.strip().splitlines() or [""])[0]
    if not ghostty_app:
        for p in ["/Applications/Ghostty.app",
                  str(Path.home() / "Applications/Ghostty.app")]:
            if Path(p).exists():
                ghostty_app = p
                break

    if ghostty_app:
        ghostty_err = "failed to open"
        children = sorted(path.iterdir()) if path.exists() else []
        service_path = str(children[0]) if children else str(path)
        safe_path = service_path.replace("\\", "\\\\").replace('"', '\\"')
        script = f'''use framework "AppKit"
use scripting additions
set thePboard to current application's NSPasteboard's generalPasteboard()
thePboard's clearContents()
thePboard's setPropertyList:{{"{safe_path}"}} forType:"NSFilenamesPboardType"
return current application's NSPerformService("New Ghostty Window Here", thePboard)'''
        r = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)
        if r.returncode == 0:
            ghostty_ok = True

    return cursor_ok, ghostty_ok, ghostty_err


# ── Textual UI ────────────────────────────────────────────────────────────────
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Label, Static
from textual.binding import Binding
from textual import work
from concurrent.futures import ThreadPoolExecutor, as_completed


class RepoItem(ListItem):
    def __init__(self, path: Path, status: dict) -> None:
        super().__init__()
        self.repo_path = path
        self.repo_status = status
        self._label: Label | None = None

    def compose(self) -> ComposeResult:
        self._label = Label(self._render_text(), markup=True)
        yield self._label

    def _render_text(self) -> str:
        sym = self.repo_status["symbol"]
        name = self.repo_path.name
        parent = str(self.repo_path.parent).replace(str(Path.home()), "~")
        if "↑" in sym and "↓" in sym:
            sym_m = f"[yellow]{sym}[/]"
        elif "↑" in sym:
            sym_m = f"[yellow]{sym}[/]"
        elif "↓" in sym:
            sym_m = f"[red]{sym}[/]"
        elif sym == "✓":
            sym_m = f"[green]{sym}[/]"
        else:
            sym_m = f"[dim]{sym}[/]"
        return f"{sym_m:<12}{name}  [dim]{parent}[/]"

    def update_status(self, status: dict) -> None:
        self.repo_status = status
        if self._label is not None:
            self._label.update(self._render_text())


class BranchItem(ListItem):
    def __init__(self, branch: dict) -> None:
        super().__init__()
        self.branch_data = branch

    def compose(self) -> ComposeResult:
        b = self.branch_data
        cur = "[cyan]▶[/] " if b["is_current"] else "  "
        if b["is_local_only"]:
            sym_m = "[dim]local[/]"
        elif b["ahead"] and b["behind"]:
            sym_m = f"[yellow]↑{b['ahead']}↓{b['behind']}[/]"
        elif b["ahead"]:
            sym_m = f"[yellow]↑{b['ahead']}[/]"
        elif b["behind"]:
            sym_m = f"[red]↓{b['behind']}[/]"
        else:
            sym_m = "[green]✓[/]"
        remote = f"[dim]{b['upstream'] or '—'}[/]"
        yield Label(f"{cur}{sym_m:<14}{b['name']}  {remote}", markup=True)


class PLaunchApp(App):
    CSS = """
    Screen {
        layout: horizontal;
    }

    #repo-list {
        width: 28%;
        height: 100%;
        border: solid $surface-lighten-2;
    }

    #right-panel {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    #branch-list {
        height: 55%;
        border: solid $surface-lighten-2;
    }

    #branch-detail {
        height: 1fr;
        border: solid $surface-lighten-2;
        padding: 1 2;
        overflow-y: auto;
    }

    ListView:focus {
        border: solid $accent;
    }

    ListItem > Label {
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+p", "pull", "Pull", show=True),
        Binding("ctrl+u", "push_action", "Push", show=True),
        Binding("ctrl+r", "refresh", "Refresh", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "quit", "Quit", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.repos: list[Path] = []
        self.selected_repo: Path | None = None
        self.selected_branch: str | None = None

    def compose(self) -> ComposeResult:
        yield ListView(id="repo-list")
        with Container(id="right-panel"):
            yield ListView(id="branch-list")
            yield Static("", id="branch-detail", markup=True)

    def on_mount(self) -> None:
        self.query_one("#repo-list", ListView).border_title = "repositories"
        self.query_one("#branch-list", ListView).border_title = "branches"
        self.query_one("#branch-detail", Static).border_title = "branch detail"
        self.load_repos()

    # ── Workers ───────────────────────────────────────────────────────────────

    @work(thread=True, exclusive=True)
    def load_repos(self) -> None:
        dirs = read_project_dirs()
        repos = collect_repos(dirs)
        self.call_from_thread(self._populate_repo_list, repos)
        with ThreadPoolExecutor(max_workers=8) as ex:
            futs = {ex.submit(self._fetch_and_refresh, r): r
                    for r in repos if is_git_with_remote(r)}
            for fut in as_completed(futs):
                pass

    def _fetch_and_refresh(self, path: Path) -> None:
        fetch_repo(path)
        status = get_repo_status(path)
        self.call_from_thread(self._update_repo_item_status, path, status)

    # ── UI update helpers ─────────────────────────────────────────────────────

    def _populate_repo_list(self, repos: list[Path]) -> None:
        self.repos = repos
        lst = self.query_one("#repo-list", ListView)
        lst.clear()
        for repo in repos:
            lst.append(RepoItem(repo, {"symbol": "…", "ahead": 0, "behind": 0}))
        if repos:
            self.selected_repo = repos[0]
            self._refresh_branches(repos[0])

    def _update_repo_item_status(self, path: Path, status: dict) -> None:
        for item in self.query_one("#repo-list", ListView).query(RepoItem):
            if item.repo_path == path:
                item.update_status(status)
                break

    def _refresh_branches(self, path: Path) -> None:
        branches = get_branches(path)
        lst = self.query_one("#branch-list", ListView)
        lst.clear()
        for b in branches:
            lst.append(BranchItem(b))
        lst.border_title = f"branches — {path.name}"
        if branches:
            self.selected_branch = branches[0]["name"]
            self._refresh_detail(path, branches[0]["name"])

    def _refresh_detail(self, path: Path, branch: str) -> None:
        d = get_branch_detail(path, branch)
        if d["is_local_only"]:
            status_line = "[dim]local only — no upstream[/]"
        elif d["ahead"] and d["behind"]:
            status_line = (f"[yellow]↑{d['ahead']}[/] [red]↓{d['behind']}[/]"
                           f"  diverged from {d['upstream']}")
        elif d["ahead"]:
            status_line = f"[yellow]↑{d['ahead']}[/]  ahead of {d['upstream']}"
        elif d["behind"]:
            status_line = f"[red]↓{d['behind']}[/]  behind {d['upstream']}"
        else:
            status_line = f"[green]✓[/]  synced with {d['upstream']}"

        content = (
            f"[bold cyan]{d['name']}[/]\n\n"
            f"{status_line}\n\n"
            f"[dim]local [/] {d['local_sha']}\n"
            f"[dim]remote[/] {d['remote_sha']}\n\n"
            f"[dim]commit[/] {d['commit_msg']}\n"
            f"[dim]author[/] {d['author']} · {d['date']}\n"
        )
        w = self.query_one("#branch-detail", Static)
        w.update(content)
        w.border_title = f"detail — {d['name']}"

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.control.id == "branch-list":
            item = event.item
            if isinstance(item, BranchItem) and self.selected_repo:
                self.selected_branch = item.branch_data["name"]
                self._refresh_detail(self.selected_repo, item.branch_data["name"])

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.control.id == "repo-list":
            item = event.item
            if isinstance(item, RepoItem):
                self.selected_repo = item.repo_path
                self._refresh_branches(item.repo_path)
                self.action_launch()

    def on_key(self, event) -> None:
        if event.key == "right":
            self.query_one("#branch-list", ListView).focus()
            event.prevent_default()
        elif event.key == "left":
            self.query_one("#repo-list", ListView).focus()
            event.prevent_default()

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_pull(self) -> None:
        if not self.selected_repo:
            return
        branch_list = self.query_one("#branch-list", ListView)
        if self.focused is branch_list and self.selected_branch:
            msg = pull_branch(self.selected_repo, self.selected_branch)
            self.notify(msg)
        else:
            for b in get_branches(self.selected_repo):
                if not b["is_local_only"] and b["behind"] > 0:
                    pull_branch(self.selected_repo, b["name"])
            self.notify(f"pulled all behind branches of {self.selected_repo.name}")
        self._refresh_branches(self.selected_repo)

    def action_push_action(self) -> None:
        if not self.selected_repo:
            return
        branch_list = self.query_one("#branch-list", ListView)
        if self.focused is branch_list and self.selected_branch:
            msg = push_branch(self.selected_repo, self.selected_branch)
            self.notify(msg)
        else:
            for b in get_branches(self.selected_repo):
                if not b["is_local_only"] and b["ahead"] > 0:
                    push_branch(self.selected_repo, b["name"])
            self.notify(f"pushed all ahead branches of {self.selected_repo.name}")
        self._refresh_branches(self.selected_repo)

    def action_refresh(self) -> None:
        self.notify("Refreshing git status…")
        self.load_repos()

    def action_launch(self) -> None:
        if not self.selected_repo:
            return
        cursor_ok, ghostty_ok, ghostty_err = launch_project(self.selected_repo)
        parts = ["Cursor ✓" if cursor_ok else "Cursor ⚠",
                 "Ghostty ✓" if ghostty_ok else f"Ghostty ⚠ {ghostty_err}"]
        self.notify(f"{self.selected_repo.name}: {', '.join(parts)}")


if __name__ == "__main__":
    PLaunchApp().run()

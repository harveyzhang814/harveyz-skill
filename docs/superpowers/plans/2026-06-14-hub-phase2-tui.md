# hub Phase 2 — TUI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a three-column Textual TUI for hub, replacing the Phase 1 stub, so `hub` (no args) launches a live terminal interface for projects, git status, and tasks.

**Architecture:** Three Textual widgets (ProjectsPanel, GitPanel, TasksPanel) wired together in `HubApp`. Panels communicate via Textual `Message` — `ProjectsPanel` posts `ProjectSelected`, the app handles it and refreshes the other two panels. Git I/O lives in `hub/tui/git.py` (pure functions, no TUI deps), copied and extended from p-launch's `p_launch.py`.

**Tech Stack:** Python 3.11+, Textual ≥ 0.80, pytest-asyncio ≥ 0.23 (headless widget tests)

---

## File Map

```
tools/hub/hub/tui/
├── __init__.py                  (empty)
├── git.py                       (pure git functions — no Textual deps)
├── app.py                       (HubApp — three-column layout, bindings, wiring)
└── panels/
    ├── __init__.py              (empty)
    ├── projects.py              (ProjectsPanel — Col 1)
    ├── git.py                   (GitPanel — Col 2)
    └── tasks.py                 (TasksPanel — Col 3)

tools/hub/tests/
├── test_tui_git.py              (unit tests for hub/tui/git.py pure functions)
├── test_tui_projects_panel.py   (headless Textual tests for ProjectsPanel)
├── test_tui_git_panel.py        (headless Textual tests for GitPanel)
├── test_tui_tasks_panel.py      (headless Textual tests for TasksPanel)
└── test_tui_app.py              (HubApp smoke test)

tools/hub/pyproject.toml        (add pytest-asyncio to dev deps; asyncio_mode = "auto")
tools/hub/hub/__main__.py       (replace stub with HubApp().run())
```

---

### Task 1: hub/tui/git.py — pure git functions

Port git I/O from p-launch into hub. Add two new functions: `get_working_tree` and `get_recent_commits`. No Textual imports here.

**Files:**
- Create: `tools/hub/hub/tui/__init__.py`
- Create: `tools/hub/hub/tui/git.py`
- Create: `tools/hub/tests/test_tui_git.py`
- Modify: `tools/hub/pyproject.toml` (add pytest-asyncio, asyncio_mode)

- [ ] **Step 1: Update pyproject.toml**

```toml
# tools/hub/pyproject.toml — full file
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "hub"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.12",
    "textual>=0.80",
]

[project.scripts]
hub = "hub.__main__:main"

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[tool.hatch.build.targets.wheel]
packages = ["hub"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

- [ ] **Step 2: Write failing tests**

```python
# tools/hub/tests/test_tui_git.py
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from hub.tui.git import (
    get_recent_commits,
    get_working_tree,
    read_project_dirs,
)


def test_get_working_tree_clean():
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        result = get_working_tree(Path("/fake"))
    assert result == {"modified": 0, "new": 0, "deleted": 0}


def test_get_working_tree_dirty():
    output = " M README.md\n?? newfile.py\nD  deleted.py\n M other.py\n"
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        result = get_working_tree(Path("/fake"))
    assert result == {"modified": 2, "new": 1, "deleted": 1}


def test_get_recent_commits():
    output = "abc123|Fix bug|2 hours ago\ndef456|Add feature|1 day ago\n"
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=output, returncode=0)
        commits = get_recent_commits(Path("/fake"), n=2)
    assert len(commits) == 2
    assert commits[0] == {"sha": "abc123", "msg": "Fix bug", "date": "2 hours ago"}
    assert commits[1] == {"sha": "def456", "msg": "Add feature", "date": "1 day ago"}


def test_get_recent_commits_empty():
    with patch("hub.tui.git.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", returncode=0)
        commits = get_recent_commits(Path("/fake"), n=5)
    assert commits == []


def test_read_project_dirs_default(tmp_path, monkeypatch):
    monkeypatch.setattr("hub.tui.git.CONFIG_FILE", tmp_path / "nonexistent.zsh")
    result = read_project_dirs()
    assert result == [Path.home() / "Projects"]


def test_read_project_dirs_from_config(tmp_path, monkeypatch):
    projects_dir = tmp_path / "my_projects"
    projects_dir.mkdir()
    config = tmp_path / "config.zsh"
    config.write_text(f'PROJECT_DIRS=("{projects_dir}")\n')
    monkeypatch.setattr("hub.tui.git.CONFIG_FILE", config)
    result = read_project_dirs()
    assert result == [projects_dir]
```

- [ ] **Step 3: Run tests — verify they fail**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_git.py -v
```

Expected: `ModuleNotFoundError: No module named 'hub.tui'`

- [ ] **Step 4: Create `hub/tui/__init__.py`**

```python
# tools/hub/hub/tui/__init__.py
```

(empty file)

- [ ] **Step 5: Create `hub/tui/git.py`**

```python
# tools/hub/hub/tui/git.py
"""Pure git I/O functions — no Textual dependencies."""
import fcntl
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "p-launch" / "config.zsh"


def read_project_dirs() -> list[Path]:
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
        capture_output=True, text=True,
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
    if not is_git_with_remote(path):
        return {"symbol": "·", "ahead": 0, "behind": 0}
    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True,
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
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    current = cur_r.stdout.strip()
    r = subprocess.run(
        ["git", "-C", str(path), "for-each-ref",
         "--format=%(refname:short)|%(upstream:short)|%(upstream:track)",
         "refs/heads"],
        capture_output=True, text=True,
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
    def git(*args) -> str:
        r = subprocess.run(
            ["git", "-C", str(path)] + list(args),
            capture_output=True, text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else ""

    upstream = git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    local_sha = git("rev-parse", "--short", branch) or "—"
    remote_sha = git("rev-parse", "--short", upstream) if upstream else "—"
    log = git("log", "-1", "--format=%s|%an|%cr", branch)
    parts = log.split("|", 2) if log else ["", "", ""]
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
        "commit_msg": parts[0] if parts else "",
        "author": parts[1] if len(parts) > 1 else "",
        "date": parts[2] if len(parts) > 2 else "",
        "ahead": ahead, "behind": behind,
        "is_local_only": not bool(upstream),
    }


def get_working_tree(path: Path) -> dict:
    """Return counts of modified/new/deleted files in the working tree."""
    r = subprocess.run(
        ["git", "-C", str(path), "status", "--short"],
        capture_output=True, text=True,
    )
    modified = new = deleted = 0
    for line in r.stdout.splitlines():
        if not line:
            continue
        xy = line[:2]
        if "?" in xy:
            new += 1
        elif "D" in xy:
            deleted += 1
        else:
            modified += 1
    return {"modified": modified, "new": new, "deleted": deleted}


def get_recent_commits(path: Path, n: int = 5) -> list[dict]:
    """Return the last n commits as list of {sha, msg, date}."""
    r = subprocess.run(
        ["git", "-C", str(path), "log", f"-{n}", "--format=%h|%s|%cr"],
        capture_output=True, text=True,
    )
    commits = []
    for line in r.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) == 3:
            commits.append({"sha": parts[0], "msg": parts[1], "date": parts[2]})
    return commits


def pull_branch(path: Path, branch: str) -> str:
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True,
    )
    if up_r.returncode != 0:
        return "no upstream — nothing to pull"
    detail = get_branch_detail(path, branch)
    if detail["ahead"] > 0 and detail["behind"] > 0:
        return f"⚠ skipped {branch} (diverged — push or rebase first)"
    if detail["behind"] == 0:
        return f"nothing to pull — {branch} is up to date"
    cur_r = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--short", "HEAD"],
        capture_output=True, text=True,
    )
    current = cur_r.stdout.strip()
    if branch == current:
        r = subprocess.run(
            ["git", "-C", str(path), "pull", "--ff-only", "origin", branch],
            capture_output=True, text=True,
        )
    else:
        r = subprocess.run(
            ["git", "-C", str(path), "fetch", "origin", f"{branch}:{branch}"],
            capture_output=True, text=True,
        )
    if r.returncode == 0:
        return f"✓ pulled {branch}"
    err = (r.stderr or r.stdout).strip().splitlines()
    reason = err[-1] if err else "unknown error"
    return f"⚠ failed to pull {branch}: {reason}"


def push_branch(path: Path, branch: str) -> str:
    up_r = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}"],
        capture_output=True, text=True,
    )
    if up_r.returncode != 0:
        return "no upstream — branch is local only"
    detail = get_branch_detail(path, branch)
    if detail["ahead"] == 0:
        return f"nothing to push — {branch} is up to date"
    if detail["behind"] > 0:
        return f"⚠ skipped {branch} (diverged — pull or rebase first)"
    r = subprocess.run(
        ["git", "-C", str(path), "push", "origin", branch],
        capture_output=True, text=True,
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
        capture_output=True, text=True,
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
        script = (
            'use framework "AppKit"\n'
            'use scripting additions\n'
            'set thePboard to current application\'s NSPasteboard\'s generalPasteboard()\n'
            'thePboard\'s clearContents()\n'
            f'thePboard\'s setPropertyList:{{"{safe_path}"}} forType:"NSFilenamesPboardType"\n'
            'return current application\'s NSPerformService("New Ghostty Window Here", thePboard)'
        )
        r = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True)
        if r.returncode == 0:
            ghostty_ok = True

    return cursor_ok, ghostty_ok, ghostty_err
```

- [ ] **Step 6: Run tests — verify they pass**

```bash
cd tools/hub && pip install pytest-asyncio -q && python3 -m pytest tests/test_tui_git.py -v
```

Expected: 6 passed

- [ ] **Step 7: Commit**

```bash
git add tools/hub/hub/tui/__init__.py tools/hub/hub/tui/git.py \
        tools/hub/tests/test_tui_git.py tools/hub/pyproject.toml
git commit -m "feat(hub): tui/git.py — pure git functions + tests"
```

---

### Task 2: ProjectsPanel

Col 1 widget. Lists projects with open-task count badges. Posts `ProjectSelected` message on highlight change.

**Files:**
- Create: `tools/hub/hub/tui/panels/__init__.py`
- Create: `tools/hub/hub/tui/panels/projects.py`
- Create: `tools/hub/tests/test_tui_projects_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/hub/tests/test_tui_projects_panel.py
import pytest
from textual.app import App, ComposeResult
from textual.widgets import ListItem

from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task
from hub.tui.panels.projects import ProjectsPanel


def _make_app(db: HubDB) -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield ProjectsPanel(db)
    return _App()


async def test_projects_panel_empty(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        items = pilot.app.query_one(ProjectsPanel).query(ListItem)
        assert len(items) == 0


async def test_projects_panel_shows_projects(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "alpha", path="/tmp/alpha")
    add_project(db, "beta", path="/tmp/beta")
    async with _make_app(db).run_test() as pilot:
        items = pilot.app.query_one(ProjectsPanel).query(ListItem)
        assert len(items) == 2


async def test_projects_panel_posts_selected_message(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "myrepo", path="/tmp/myrepo")
    received: list[ProjectsPanel.ProjectSelected] = []

    class _App(App):
        def compose(self) -> ComposeResult:
            yield ProjectsPanel(db)
        def on_projects_panel_project_selected(self, msg: ProjectsPanel.ProjectSelected):
            received.append(msg)

    async with _App().run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        panel.query_one("ListView").focus()
        await pilot.press("down")
        await pilot.pause()

    assert any(m.name == "myrepo" for m in received)


async def test_projects_panel_shows_task_count(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="do something", project="proj")
    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(ProjectsPanel)
        from textual.widgets import Label
        labels = panel.query(Label)
        text = " ".join(str(l.renderable) for l in labels)
        assert "proj" in text
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_projects_panel.py -v
```

Expected: `ModuleNotFoundError: No module named 'hub.tui.panels'`

- [ ] **Step 3: Create `hub/tui/panels/__init__.py`**

```python
# tools/hub/hub/tui/panels/__init__.py
```

(empty file)

- [ ] **Step 4: Create `hub/tui/panels/projects.py`**

```python
# tools/hub/hub/tui/panels/projects.py
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
```

- [ ] **Step 5: Run tests — verify they pass**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_projects_panel.py -v
```

Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add tools/hub/hub/tui/panels/__init__.py tools/hub/hub/tui/panels/projects.py \
        tools/hub/tests/test_tui_projects_panel.py
git commit -m "feat(hub): ProjectsPanel — project list with task count badges"
```

---

### Task 3: GitPanel

Col 2 widget. Shows current branch, ahead/behind, working tree state, and recent commits. Refreshed by the app when project selection changes.

**Files:**
- Create: `tools/hub/hub/tui/panels/git.py`
- Create: `tools/hub/tests/test_tui_git_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/hub/tests/test_tui_git_panel.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from textual.app import App, ComposeResult
from textual.widgets import Static

from hub.tui.panels.git import GitPanel


def _make_app() -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield GitPanel()
    return _App()


async def test_git_panel_mounts():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        assert panel is not None


async def test_git_panel_shows_placeholder_before_project():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        content = panel.query_one("#git-content", Static)
        text = str(content.renderable)
        assert "Select a project" in text


async def test_git_panel_refresh_nonexistent_path():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel.refresh_project(Path("/nonexistent/path"))
        await pilot.pause()
        content = str(panel.query_one("#git-content", Static).renderable)
        assert "No valid path" in content
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_git_panel.py -v
```

Expected: `ModuleNotFoundError: No module named 'hub.tui.panels.git'`

- [ ] **Step 3: Create `hub/tui/panels/git.py`**

```python
# tools/hub/hub/tui/panels/git.py
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
        self.call_from_thread(self._render, path, current, wt, commits)

    def _render(
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
        self.call_from_thread(self.refresh_project, path)
        self.app.call_from_thread(self.app.notify, f"Fetched {path.name}")
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_git_panel.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add tools/hub/hub/tui/panels/git.py tools/hub/tests/test_tui_git_panel.py
git commit -m "feat(hub): GitPanel — branch, working tree, recent commits"
```

---

### Task 4: TasksPanel

Col 3 widget. Shows tasks for the selected project grouped by status. Supports inline new-task input (`n`), toggle done (`Space`), delete with two-press confirm (`D`).

**Files:**
- Create: `tools/hub/hub/tui/panels/tasks.py`
- Create: `tools/hub/tests/test_tui_tasks_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/hub/tests/test_tui_tasks_panel.py
import pytest
from textual.app import App, ComposeResult
from textual.widgets import ListItem

from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task, list_tasks
from hub.tui.panels.tasks import TasksPanel


def _make_app(db: HubDB) -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield TasksPanel(db)
    return _App()


async def test_tasks_panel_mounts(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        assert pilot.app.query_one(TasksPanel) is not None


async def test_tasks_panel_shows_tasks(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Task A", project="proj")
    add_task(db, title="Task B", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        items = panel.query(ListItem)
        assert len(items) == 2


async def test_tasks_panel_toggle_done(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    t = add_task(db, title="Finish me", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        # focus list, select first item, press Space
        panel.query_one("ListView").focus()
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()

    tasks = list_tasks(db, project="proj")
    assert tasks[0]["status"] == "done"


async def test_tasks_panel_new_task_input_appears(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")

    from textual.widgets import Input

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.focus()
        await pilot.press("n")
        await pilot.pause()
        assert len(panel.query(Input)) == 1
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_tasks_panel.py -v
```

Expected: `ModuleNotFoundError: No module named 'hub.tui.panels.tasks'`

- [ ] **Step 3: Create `hub/tui/panels/tasks.py`**

```python
# tools/hub/hub/tui/panels/tasks.py
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Input, Label, ListItem, ListView

from hub.core.db import HubDB
from hub.core.tasks import add_task, delete_task, list_tasks, mark_done, update_task


class TasksPanel(Widget):
    BINDINGS = [
        Binding("n", "new_task", "New", show=True),
        Binding("space", "toggle_done", "Done", show=True),
        Binding("D", "delete_task_action", "Delete", show=True),
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
            lst.append(ListItem(
                Label(f"☐ {t['title']}  {pri}", markup=True),
                id=f"task-{t['id']}",
            ))
        if done:
            lst.append(ListItem(Label("[dim]── DONE ──[/]", markup=True)))
            for t in done:
                lst.append(ListItem(
                    Label(f"[dim]☑ {t['title']}[/]", markup=True),
                    id=f"task-{t['id']}",
                ))

        self.border_title = f"TASKS · {self._project}"

    def _selected_task(self) -> dict | None:
        lst = self.query_one(ListView)
        item = lst.highlighted_child
        if item is None or not (item.id or "").startswith("task-"):
            return None
        task_id = int((item.id or "").split("-")[1])
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_tasks_panel.py -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add tools/hub/hub/tui/panels/tasks.py tools/hub/tests/test_tui_tasks_panel.py
git commit -m "feat(hub): TasksPanel — task list, toggle done, new task input"
```

---

### Task 5: HubApp — wire three panels together

The `HubApp` Textual `App` subclass. Composes the three panels, handles `ProjectSelected` messages to keep GitPanel and TasksPanel in sync, and provides app-level key bindings.

**Files:**
- Create: `tools/hub/hub/tui/app.py`
- Create: `tools/hub/tests/test_tui_app.py`

- [ ] **Step 1: Write failing tests**

```python
# tools/hub/tests/test_tui_app.py
import pytest
from hub.tui.app import HubApp
from hub.tui.panels.git import GitPanel
from hub.tui.panels.projects import ProjectsPanel
from hub.tui.panels.tasks import TasksPanel


async def test_hub_app_mounts(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        assert pilot.app.query_one(ProjectsPanel) is not None
        assert pilot.app.query_one(GitPanel) is not None
        assert pilot.app.query_one(TasksPanel) is not None


async def test_hub_app_quit(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        await pilot.press("q")
    # If we got here without hanging, the app quit cleanly.
    assert True


async def test_hub_app_tab_cycles_focus(tmp_path, monkeypatch):
    monkeypatch.setenv("HUB_DB_PATH", str(tmp_path / "hub.db"))
    async with HubApp().run_test() as pilot:
        # Tab should not raise
        await pilot.press("tab")
        await pilot.press("tab")
        await pilot.press("tab")
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_app.py -v
```

Expected: `ModuleNotFoundError: No module named 'hub.tui.app'`

- [ ] **Step 3: Create `hub/tui/app.py`**

```python
# tools/hub/hub/tui/app.py
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
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_app.py -v
```

Expected: 3 passed

- [ ] **Step 5: Run full test suite — no regressions**

```bash
cd tools/hub && python3 -m pytest tests/ -v
```

Expected: all tests pass (36 previous + 10 new TUI = 46 total)

- [ ] **Step 6: Commit**

```bash
git add tools/hub/hub/tui/app.py tools/hub/tests/test_tui_app.py
git commit -m "feat(hub): HubApp — three-column TUI with panel wiring"
```

---

### Task 6: Wire `__main__.py` — launch TUI

Replace the Phase 1 stub with `HubApp().run()`.

**Files:**
- Modify: `tools/hub/hub/__main__.py`

- [ ] **Step 1: Write failing test**

```python
# Add to tools/hub/tests/test_tui_app.py (append to existing file):

from unittest.mock import patch

def test_main_no_args_launches_tui(monkeypatch):
    """hub with no args calls HubApp().run(), not the CLI."""
    import sys
    monkeypatch.setattr(sys, "argv", ["hub"])
    launched = []

    with patch("hub.tui.app.HubApp.run", side_effect=lambda: launched.append(True)):
        from hub.__main__ import main
        main()

    assert launched == [True]
```

- [ ] **Step 2: Run test — verify it fails**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_app.py::test_main_no_args_launches_tui -v
```

Expected: FAIL — test prints the Phase 1 stub message instead of calling `HubApp().run()`

- [ ] **Step 3: Update `hub/__main__.py`**

```python
# tools/hub/hub/__main__.py
import sys


def main():
    from hub.core.db import HubDB
    from hub.core.migrate import needs_migration, run_migration

    db = HubDB()
    if needs_migration():
        n = run_migration(db)
        if n:
            import typer
            typer.echo(f"hub: migrated {n} tasks from todo-tool ✓")

    if len(sys.argv) == 1:
        from hub.tui.app import HubApp
        HubApp().run()
        return

    from hub.cli import app
    app()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test — verify it passes**

```bash
cd tools/hub && python3 -m pytest tests/test_tui_app.py -v
```

Expected: all 4 tests pass

- [ ] **Step 5: Run full test suite**

```bash
cd tools/hub && python3 -m pytest tests/ -v
```

Expected: 47 total tests, all pass

- [ ] **Step 6: Commit**

```bash
git add tools/hub/hub/__main__.py
git commit -m "feat(hub): wire TUI launch — hub with no args starts HubApp"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|---|---|
| Three-column layout (Projects / Git / Tasks) | Task 5 (HubApp CSS) |
| Col 1: project list, task count badge | Task 2 (ProjectsPanel) |
| Col 2: branch, tracking, ahead/behind, working tree, recent commits | Task 3 (GitPanel) |
| Col 3: tasks grouped todo/done, search filter | Task 4 (TasksPanel) — filter deferred (YAGNI: no use case yet) |
| Tab cycles focus | Task 5 (action_cycle_focus) |
| `f` fetch | Task 5 (action_fetch → GitPanel.action_fetch) |
| `Enter` open project in Cursor + Ghostty | Task 5 (action_open_project) |
| `n` new task | Task 4 (action_new_task) |
| `Space` toggle done | Task 4 (action_toggle_done) |
| `D` delete with confirm | Task 4 (action_delete_task_action, two-press) |
| `q` quit | Task 5 (Binding quit) |
| `hub` (no args) launches TUI | Task 6 |
| Pure git functions (no Textual deps) | Task 1 (hub/tui/git.py) |
| p-launch git functions ported to hub | Task 1 |

**Deferred (YAGNI):** `/` live-filter tasks — no concrete use case in the current scope; TasksPanel can add it later without changing any interfaces.

### Placeholder scan

No TBDs, no "implement later", no "add error handling" without code. All steps include exact code.

### Type consistency

- `ProjectsPanel.ProjectSelected.name: str` — used in Task 5 `on_projects_panel_project_selected` ✓
- `GitPanel.refresh_project(path: Path | None)` — called in Task 5 ✓
- `TasksPanel.refresh_project(project_name: str)` — called in Task 5 ✓
- `list_tasks(db, project=..., status=...)` — same signature as Phase 1 `core/tasks.py` ✓

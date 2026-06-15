# Hub Git Panel — Branch List Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the hub TUI's static git info panel with an interactive `ListView` that shows all branches grouped into "WITH REMOTE" and "LOCAL ONLY" sections.

**Architecture:** `GitPanel` (`hub/tui/panels/git.py`) drops its `Static` widget and composes a `ListView` instead. Two new `ListItem` subclasses — `SectionHeader` (non-interactive divider) and `BranchItem` (one branch row) — handle rendering. The data layer (`hub/tui/git.py`) is unchanged.

**Tech Stack:** Python 3.11+, Textual 0.80+ (tested on 8.2.7), pytest-asyncio

---

## File Map

| File | Change |
|---|---|
| `hub/tui/panels/git.py` | Full rewrite: add `SectionHeader`, `BranchItem`; refactor `GitPanel` |
| `tests/test_tui_git_panel.py` | Full rewrite: update all tests to match new widget structure |

`hub/tui/git.py` and `hub/tui/app.py` are **not touched**.

---

### Task 1: Write failing tests for `BranchItem` and `SectionHeader`

**Files:**
- Modify: `tests/test_tui_git_panel.py`

- [ ] **Step 1: Replace the entire test file with new failing tests**

```python
import pytest
from pathlib import Path
from textual.app import App, ComposeResult
from textual.widgets import ListView, Static, Label

from hub.tui.panels.git import GitPanel, BranchItem, SectionHeader


def _make_app() -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield GitPanel()
    return _App()


async def test_git_panel_mounts():
    async with _make_app().run_test() as pilot:
        assert pilot.app.query_one(GitPanel) is not None


async def test_git_panel_shows_placeholder_before_project():
    async with _make_app().run_test() as pilot:
        placeholder = pilot.app.query_one("#git-placeholder", Static)
        assert placeholder.display
        assert "Select a project" in str(placeholder.content)


async def test_git_panel_listview_hidden_before_project():
    async with _make_app().run_test() as pilot:
        lv = pilot.app.query_one("#branch-list", ListView)
        assert not lv.display


async def test_git_panel_refresh_nonexistent_path():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel.refresh_project(Path("/nonexistent/path/that/does/not/exist"))
        await pilot.pause()
        placeholder = pilot.app.query_one("#git-placeholder", Static)
        assert placeholder.display
        assert "No valid path" in str(placeholder.content)


async def test_branch_item_stores_data():
    b = {
        "name": "main", "upstream": "origin/main",
        "ahead": 0, "behind": 0,
        "is_current": True, "is_local_only": False,
    }
    item = BranchItem(b)
    assert item.branch_data == b


async def test_section_header_stores_title():
    h = SectionHeader("WITH REMOTE")
    assert h._title == "WITH REMOTE"


async def test_git_panel_render_branches_shows_listview():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        assert lv.display
        assert not pilot.app.query_one("#git-placeholder", Static).display


async def test_git_panel_render_branches_border_title():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        assert "harveyz-skill" in panel.border_title


async def test_git_panel_both_sections_present():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 2
        branch_items = list(lv.query(BranchItem))
        assert len(branch_items) == 2


async def test_git_panel_omits_local_section_when_empty():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "main", "upstream": "origin/main", "ahead": 0, "behind": 0, "is_current": True, "is_local_only": False},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 1


async def test_git_panel_omits_remote_section_when_empty():
    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    branches = [
        {"name": "wip", "upstream": "", "ahead": 0, "behind": 0, "is_current": False, "is_local_only": True},
    ]
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._render_branches(repo_path, branches)
        await pilot.pause()
        lv = pilot.app.query_one("#branch-list", ListView)
        headers = list(lv.query(SectionHeader))
        assert len(headers) == 1
```

- [ ] **Step 2: Run tests — expect ImportError on `BranchItem`, `SectionHeader`**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/hub
.venv/bin/python -m pytest tests/test_tui_git_panel.py -v 2>&1 | head -40
```

Expected: `ImportError: cannot import name 'BranchItem' from 'hub.tui.panels.git'`

- [ ] **Step 3: Commit the failing tests**

```bash
git add tests/test_tui_git_panel.py
git commit -m "test(git-panel): failing tests for branch list redesign"
```

---

### Task 2: Implement `SectionHeader` and `BranchItem`

**Files:**
- Modify: `hub/tui/panels/git.py`

- [ ] **Step 1: Replace the entire file content**

```python
from pathlib import Path

from textual import work
from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import ListView, ListItem, Label, Static

from hub.tui.git import fetch_repo, get_branches, is_git_with_remote


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
            sym_m = "[dim]local[/]  "
        elif b["ahead"] and b["behind"]:
            sym_m = f"[yellow]↑{b['ahead']}↓{b['behind']}[/]"
        elif b["ahead"]:
            sym_m = f"[yellow]↑{b['ahead']}[/]   "
        elif b["behind"]:
            sym_m = f"[red]↓{b['behind']}[/]   "
        else:
            sym_m = "[green]✓[/]     "
        name = b["name"]
        remote = f"  [dim]{b['upstream']}[/]" if b.get("upstream") else ""
        yield Label(f"{cur}{sym_m} {name}{remote}", markup=True)


class GitPanel(Widget):
    can_focus = True

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

    def compose(self) -> ComposeResult:
        yield Static("Select a project to see git status.", id="git-placeholder", markup=True)
        lv = ListView(id="branch-list")
        lv.display = False
        yield lv

    def on_mount(self) -> None:
        self.border_title = "GIT"

    def refresh_project(self, path: Path | None) -> None:
        self._path = path
        if path is None or not path.exists():
            self.query_one("#git-placeholder", Static).update("No valid path.")
            self.query_one("#git-placeholder", Static).display = True
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
```

- [ ] **Step 2: Run tests — expect most to pass**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/hub
.venv/bin/python -m pytest tests/test_tui_git_panel.py -v
```

Expected: all tests pass. If `SectionHeader.disabled` causes issues in Textual 8.x, skip it (the header will be visually navigable but won't respond to selection — acceptable).

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
.venv/bin/python -m pytest -v
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add hub/tui/panels/git.py
git commit -m "feat(git-panel): replace static with branch ListView, section headers"
```

---

### Task 3: Verify in the running TUI

**Files:** none (smoke test only)

- [ ] **Step 1: Run the hub TUI**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/hub
.venv/bin/hub tui
```

- [ ] **Step 2: Verify the following**

Select a project in the left panel:
- GIT column shows a `ListView` with branches
- Branches with remotes appear under `▸ WITH REMOTE`
- Local-only branches appear under `▸ LOCAL ONLY`
- Current branch shows `▶` cyan marker
- Sync symbols: `✓` green / `↑N` yellow / `↓N` red / `local` dim
- Section headers are visually distinct (dim text)
- Column is scrollable when many branches exist
- Switching projects updates the list

- [ ] **Step 3: If anything looks wrong, fix and re-run tests before committing**

---

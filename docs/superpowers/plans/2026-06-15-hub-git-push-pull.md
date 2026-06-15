# Hub Git Push/Pull Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add state-aware push/pull to the hub TUI git panel (Ctrl+P / Ctrl+U, Footer-visible only when applicable) and to the CLI (`hub git pull` / `hub git push`).

**Architecture:** `GitPanel` gains `BINDINGS`, `_selected_branch` tracking, `check_action`, and worker methods. No changes to `hub/tui/git.py` (data layer) or `hub/tui/app.py`. CLI gains two new commands in `hub/cli/git.py` with full pre-validation before calling existing `pull_branch`/`push_branch` functions.

**Tech Stack:** Python 3.11+, Textual 8.2.7, Typer, pytest-asyncio

---

## File Map

| File | Change |
|---|---|
| `hub/tui/panels/git.py` | Add `BINDINGS`, `_selected_branch`, `on_list_view_highlighted`, `_selected_branch_data`, `check_action`, `action_pull`, `action_push`, `_pull_worker`, `_push_worker`; add imports `pull_branch`, `push_branch` |
| `hub/cli/git.py` | Add `pull_branch`/`push_branch` to imports; add `git_pull` and `git_push` commands |
| `tests/test_tui_git_panel.py` | Add `check_action` tests |
| `tests/test_cli.py` | Add CLI pull/push tests |

`hub/tui/git.py` and `hub/tui/app.py` are **not touched**.

---

### Task 1: TUI — Branch selection tracking + check_action

**Files:**
- Modify: `hub/tui/panels/git.py`
- Test: `tests/test_tui_git_panel.py`

- [ ] **Step 1: Add failing tests for check_action to test_tui_git_panel.py**

Append these tests to the existing file:

```python
# --- check_action and branch selection ---

def _branch(name="main", upstream="origin/main", ahead=0, behind=0,
            is_current=True, is_local_only=False):
    return {"name": name, "upstream": upstream, "ahead": ahead, "behind": behind,
            "is_current": is_current, "is_local_only": is_local_only}


async def test_selected_branch_initially_none():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        assert panel._selected_branch_data() is None


async def test_check_action_pull_available_when_behind_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(behind=2, ahead=0)
        assert panel.check_action("pull", ()) is True


async def test_check_action_pull_not_available_when_ahead_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=1, behind=0)
        assert panel.check_action("pull", ()) is False


async def test_check_action_pull_not_available_when_diverged():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=1, behind=1)
        assert panel.check_action("pull", ()) is False


async def test_check_action_pull_not_available_when_local_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(upstream="", is_local_only=True)
        assert panel.check_action("pull", ()) is False


async def test_check_action_pull_not_available_when_synced():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=0, behind=0)
        assert panel.check_action("pull", ()) is False


async def test_check_action_push_available_when_ahead_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=1, behind=0)
        assert panel.check_action("push", ()) is True


async def test_check_action_push_not_available_when_behind_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=0, behind=1)
        assert panel.check_action("push", ()) is False


async def test_check_action_push_not_available_when_diverged():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=1, behind=1)
        assert panel.check_action("push", ()) is False


async def test_check_action_push_not_available_when_local_only():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(upstream="", is_local_only=True)
        assert panel.check_action("push", ()) is False


async def test_check_action_push_not_available_when_synced():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._selected_branch = _branch(ahead=0, behind=0)
        assert panel.check_action("push", ()) is False


async def test_check_action_false_when_no_branch_selected():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        assert panel.check_action("pull", ()) is False
        assert panel.check_action("push", ()) is False


async def test_check_action_none_for_unrelated_action():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        assert panel.check_action("fetch", ()) is None
```

- [ ] **Step 2: Run failing tests**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill/tools/hub
.venv/bin/python -m pytest tests/test_tui_git_panel.py -k "check_action or selected_branch" -v 2>&1 | tail -20
```

Expected: `AttributeError: 'GitPanel' object has no attribute '_selected_branch'`

- [ ] **Step 3: Add tracking + check_action to GitPanel**

In `hub/tui/panels/git.py`, make the following changes:

**3a. Add import at top of file** (add to existing import from hub.tui.git):

```python
from hub.tui.git import fetch_repo, get_branches, is_git_with_remote, pull_branch, push_branch
```

**3b. Add `BINDINGS` class attribute** (add after `can_focus = True`):

```python
from textual.binding import Binding

BINDINGS = [
    Binding("ctrl+p", "pull", "Pull", show=True),
    Binding("ctrl+u", "push", "Push", show=True),
]
```

**3c. Add `_selected_branch` to `__init__`** (add after `self._path`):

```python
self._selected_branch: dict | None = None
```

**3d. Add these methods** (add after `on_focus`):

```python
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
.venv/bin/python -m pytest tests/test_tui_git_panel.py -v
```

Expected: all pass (79 + 13 new = 92 total).

- [ ] **Step 5: Commit**

```bash
git -C /Users/harveyzhang96/Projects/harveyz-skill add \
  tools/hub/hub/tui/panels/git.py \
  tools/hub/tests/test_tui_git_panel.py
git -C /Users/harveyzhang96/Projects/harveyz-skill commit -m "feat(git-panel): branch selection tracking and check_action for pull/push"
```

---

### Task 2: TUI — Pull/Push actions + workers

**Files:**
- Modify: `hub/tui/panels/git.py`
- Test: `tests/test_tui_git_panel.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_tui_git_panel.py`:

```python
# --- action_pull / action_push ---

async def test_action_pull_does_nothing_when_no_branch():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        # no selected branch and no path → should not raise
        panel.action_pull()
        await pilot.pause()


async def test_action_push_does_nothing_when_no_branch():
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel.action_push()
        await pilot.pause()


async def test_action_pull_calls_pull_branch(monkeypatch):
    calls = []

    def fake_pull(path, branch):
        calls.append((path, branch))
        return "✓ pulled main"

    monkeypatch.setattr("hub.tui.panels.git.pull_branch", fake_pull)

    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._path = repo_path
        panel._selected_branch = _branch(name="main", behind=1, ahead=0)
        panel.action_pull()
        await pilot.pause(delay=0.5)
        assert len(calls) == 1
        assert calls[0] == (repo_path, "main")


async def test_action_push_calls_push_branch(monkeypatch):
    calls = []

    def fake_push(path, branch):
        calls.append((path, branch))
        return "✓ pushed main"

    monkeypatch.setattr("hub.tui.panels.git.push_branch", fake_push)

    repo_path = Path("/Users/harveyzhang96/Projects/harveyz-skill")
    async with _make_app().run_test() as pilot:
        panel = pilot.app.query_one(GitPanel)
        panel._path = repo_path
        panel._selected_branch = _branch(name="main", ahead=1, behind=0)
        panel.action_push()
        await pilot.pause(delay=0.5)
        assert len(calls) == 1
        assert calls[0] == (repo_path, "main")
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_tui_git_panel.py -k "action_pull or action_push" -v 2>&1 | tail -20
```

Expected: `AttributeError: 'GitPanel' object has no attribute 'action_pull'`

- [ ] **Step 3: Add action methods and workers to GitPanel**

Add these methods to `GitPanel` in `hub/tui/panels/git.py` (after `check_action`):

```python
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
.venv/bin/python -m pytest tests/test_tui_git_panel.py -v
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/harveyzhang96/Projects/harveyz-skill add \
  tools/hub/hub/tui/panels/git.py \
  tools/hub/tests/test_tui_git_panel.py
git -C /Users/harveyzhang96/Projects/harveyz-skill commit -m "feat(git-panel): pull/push actions with background workers and refresh"
```

---

### Task 3: CLI — git pull and git push

**Files:**
- Modify: `hub/cli/git.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add failing CLI tests**

Append to `tests/test_cli.py`. First add `from pathlib import Path` to the existing imports at the top of the file (after `import pytest`), then add:

```python
# --- git pull / git push ---

def _br(name="main", upstream="origin/main", ahead=0, behind=0,
        is_current=True, is_local_only=False):
    return {"name": name, "upstream": upstream, "ahead": ahead, "behind": behind,
            "is_current": is_current, "is_local_only": is_local_only}


def test_git_pull_not_a_git_repo(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "not a git repository" in result.output


def test_git_pull_branch_not_found(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br()])
    result = runner.invoke(app, ["git", "pull", "--branch", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_git_pull_local_only(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(upstream="", is_local_only=True)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "no upstream" in result.output


def test_git_pull_diverged(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=1)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code != 0
    assert "diverged" in result.output


def test_git_pull_already_up_to_date(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(behind=0, ahead=0)])
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_git_pull_success(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(behind=1, ahead=0)])
    monkeypatch.setattr("hub.cli.git.pull_branch", lambda p, b: f"✓ pulled {b}")
    result = runner.invoke(app, ["git", "pull"])
    assert result.exit_code == 0
    assert "✓ pulled main" in result.output


def test_git_push_not_a_git_repo(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "not a git repository" in result.output


def test_git_push_branch_not_found(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br()])
    result = runner.invoke(app, ["git", "push", "--branch", "nonexistent"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_git_push_local_only(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(upstream="", is_local_only=True)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "no upstream" in result.output


def test_git_push_diverged(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=1)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code != 0
    assert "diverged" in result.output


def test_git_push_already_up_to_date(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=0, behind=0)])
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code == 0
    assert "already up to date" in result.output


def test_git_push_success(monkeypatch):
    monkeypatch.setattr("hub.cli.git._resolve_path", lambda p: Path("/tmp/fake"))
    monkeypatch.setattr("hub.cli.git.get_branches", lambda p: [_br(ahead=1, behind=0)])
    monkeypatch.setattr("hub.cli.git.push_branch", lambda p, b: f"✓ pushed {b}")
    result = runner.invoke(app, ["git", "push"])
    assert result.exit_code == 0
    assert "✓ pushed main" in result.output
```

- [ ] **Step 2: Run failing tests**

```bash
.venv/bin/python -m pytest tests/test_cli.py -k "git_pull or git_push" -v 2>&1 | tail -20
```

Expected: `Error: No such command 'pull'` (CLI command not yet registered).

- [ ] **Step 3: Add pull and push commands to hub/cli/git.py**

**3a. Update the import block** (replace the existing `from hub.tui.git import ...` block):

```python
from hub.tui.git import (
    fetch_repo,
    get_branches,
    get_recent_commits,
    get_working_tree,
    is_git_with_remote,
    pull_branch,
    push_branch,
)
```

**3b. Add these two commands** at the end of `hub/cli/git.py`:

```python
@app.command("pull")
def git_pull(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to pull (default: current branch)"),
):
    """Pull a branch from its remote upstream."""
    path = _resolve_path(project)
    branches = get_branches(path)
    if not branches:
        typer.echo("Error: not a git repository", err=True)
        raise SystemExit(1)

    if branch is None:
        b = next((x for x in branches if x["is_current"]), None)
        if b is None:
            typer.echo("Error: no current branch found", err=True)
            raise SystemExit(1)
    else:
        b = next((x for x in branches if x["name"] == branch), None)
        if b is None:
            typer.echo(f"Error: branch '{branch}' not found", err=True)
            raise SystemExit(1)

    if b["is_local_only"]:
        typer.echo(f"Error: branch '{b['name']}' has no upstream", err=True)
        raise SystemExit(1)
    if b["ahead"] > 0 and b["behind"] > 0:
        typer.echo(f"Error: branch '{b['name']}' is diverged — rebase or merge first", err=True)
        raise SystemExit(1)
    if b["behind"] == 0:
        typer.echo(f"branch '{b['name']}' is already up to date")
        return

    msg = pull_branch(path, b["name"])
    if msg.startswith("⚠") or "failed" in msg:
        typer.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    typer.echo(msg)


@app.command("push")
def git_push(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to push (default: current branch)"),
):
    """Push a branch to its remote upstream."""
    path = _resolve_path(project)
    branches = get_branches(path)
    if not branches:
        typer.echo("Error: not a git repository", err=True)
        raise SystemExit(1)

    if branch is None:
        b = next((x for x in branches if x["is_current"]), None)
        if b is None:
            typer.echo("Error: no current branch found", err=True)
            raise SystemExit(1)
    else:
        b = next((x for x in branches if x["name"] == branch), None)
        if b is None:
            typer.echo(f"Error: branch '{branch}' not found", err=True)
            raise SystemExit(1)

    if b["is_local_only"]:
        typer.echo(f"Error: branch '{b['name']}' has no upstream", err=True)
        raise SystemExit(1)
    if b["ahead"] > 0 and b["behind"] > 0:
        typer.echo(f"Error: branch '{b['name']}' is diverged — rebase or merge first", err=True)
        raise SystemExit(1)
    if b["ahead"] == 0:
        typer.echo(f"branch '{b['name']}' is already up to date")
        return

    msg = push_branch(path, b["name"])
    if msg.startswith("⚠") or "failed" in msg:
        typer.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    typer.echo(msg)
```

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/harveyzhang96/Projects/harveyz-skill add \
  tools/hub/hub/cli/git.py \
  tools/hub/tests/test_cli.py
git -C /Users/harveyzhang96/Projects/harveyz-skill commit -m "feat(cli): hub git pull and hub git push commands"
```

---

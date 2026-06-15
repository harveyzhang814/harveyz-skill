# Hub Git Panel — Push/Pull Feature Design

**Date:** 2026-06-15  
**Scope:** `hub/tui/panels/git.py`, `hub/tui/app.py`, `hub/cli/git.py`

## Problem

The hub TUI's git panel and CLI have no way to push or pull branches. Users must leave the TUI to run git commands manually.

## Goal

Add state-aware push and pull to the TUI git panel and the CLI. Actions are only available when they will succeed — the UI reflects this in real time, and the CLI exits clearly on any error condition.

## Design

### 1. State Availability Logic

Based on the selected branch's `branch_data`:

| Branch state | Pull | Push |
|---|---|---|
| `is_local_only` (no upstream) | ✗ | ✗ |
| `ahead > 0`, `behind == 0` | ✗ | ✓ |
| `behind > 0`, `ahead == 0` | ✓ | ✗ |
| `ahead > 0` and `behind > 0` (diverged) | ✗ | ✗ |
| `ahead == 0` and `behind == 0` (synced) | ✗ | ✗ |

### 2. TUI

#### Bindings

`Ctrl+P` (pull) and `Ctrl+U` (push) are defined as `BINDINGS` on `GitPanel`. They appear in the Footer only when available for the currently highlighted branch, using Textual's `check_action()` mechanism:

```python
def check_action(self, action: str, parameters: tuple) -> bool | None:
    b = self._selected_branch_data()
    if b is None:
        return False
    if action == "pull":
        return not b["is_local_only"] and b["behind"] > 0 and b["ahead"] == 0
    if action == "push":
        return not b["is_local_only"] and b["ahead"] > 0 and b["behind"] == 0
    return None
```

Footer updates automatically when the highlighted branch changes.

#### Selected Branch Tracking

`GitPanel` stores `_selected_branch: dict | None` and updates it via `on_list_view_highlighted`:

```python
def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
    if isinstance(event.item, BranchItem):
        self._selected_branch = event.item.branch_data
    else:
        self._selected_branch = None
```

Helper: `_selected_branch_data() -> dict | None` returns `self._selected_branch`.

#### Execution

`action_pull` and `action_push` run in background workers using the existing `pull_branch()` / `push_branch()` functions from `hub/tui/git.py`. On completion:
1. Show result via `self.app.notify(msg)`
2. Call `self.refresh_project(self._path)` to reload branch list

#### App-Level Routing

`app.py` delegates `action_pull` and `action_push` to `GitPanel`:

```python
def action_pull(self) -> None:
    self.query_one(GitPanel).action_pull()

def action_push(self) -> None:
    self.query_one(GitPanel).action_push()
```

And registers the bindings with `show=False` so the Footer shows only the `GitPanel`-level ones:

```python
Binding("ctrl+p", "pull", "Pull", show=False),
Binding("ctrl+u", "push", "Push", show=False),
```

### 3. CLI

New commands added to `hub/cli/git.py`:

```
hub git pull [--branch/-b BRANCH] [--project/-p PROJECT]
hub git push [--branch/-b BRANCH] [--project/-p PROJECT]
```

If `--branch` is omitted, the current branch is used (via `get_branches()` looking for `is_current`).

#### Error Handling

| Condition | Output | Exit |
|---|---|---|
| Project not found | `Error: project 'x' not found` | 1 |
| Path not a git repo / no branches | `Error: not a git repository` | 1 |
| Branch not found | `Error: branch 'x' not found` | 1 |
| No upstream (`is_local_only`) | `Error: branch 'x' has no upstream` | 1 |
| Diverged (`ahead > 0 and behind > 0`) | `Error: branch 'x' is diverged — rebase or merge first` | 1 |
| Already up to date (synced) | `branch 'x' is already up to date` | 0 |
| Git command failure | `Error: <git error message>` | 1 |
| Success | `✓ pulled main` / `✓ pushed main` | 0 |

All validation runs before calling `pull_branch()` / `push_branch()` to produce specific error messages rather than relying on those functions' return strings.

### 4. Data Layer

No changes to `hub/tui/git.py`. The existing `pull_branch(path, branch)` and `push_branch(path, branch)` functions are used as-is.

### 5. Implementation Scope

**Modified:**
- `hub/tui/panels/git.py` — add `_selected_branch`, `on_list_view_highlighted`, `check_action`, `action_pull`, `action_push`, worker methods
- `hub/tui/app.py` — add `Ctrl+P` / `Ctrl+U` bindings (show=False) + delegate actions to `GitPanel`
- `hub/cli/git.py` — add `pull` and `push` commands

**Unchanged:**
- `hub/tui/git.py` (data functions)
- `hub/tui/panels/projects.py`, `hub/tui/panels/tasks.py`

**Tests:**
- `tests/test_tui_git_panel.py` — add tests for `check_action`, `_selected_branch_data`, worker behavior
- `tests/test_cli.py` — add tests for `hub git pull` and `hub git push` error/success paths

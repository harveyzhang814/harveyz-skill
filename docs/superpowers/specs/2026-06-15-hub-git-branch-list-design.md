# Hub TUI Git Panel — Branch List Redesign

**Date:** 2026-06-15  
**Scope:** `tools/hub/hub/tui/panels/git.py` + `tests/test_tui_git_panel.py`

## Problem

The current `GitPanel` shows only the currently checked-out branch via a static text widget. All other branches are invisible. Users have no way to see the full branch state of a project at a glance.

## Goal

Replace the static git info panel with an interactive `ListView` that shows all branches, grouped into two sections: branches with remote tracking and local-only branches — matching the branch display pattern already used in p-launch.

## Design

### Layout

`GitPanel` becomes a `Widget` containing a single `ListView`. The `Static` content widget is removed entirely. Working tree (modified/new/deleted) and recent commits are also removed — the panel focuses exclusively on branch state.

### Sections

Two non-selectable section header rows divide the list:

```
▸ WITH REMOTE
  ▶ ↑2    staging         origin/staging
    ✓     main            origin/main
    ↓1    feature/x       origin/feature/x

▸ LOCAL ONLY
    local  chore/cleanup
    local  wip/experiment
```

Section headers are rendered as non-focusable `ListItem` rows with dimmed styling. If a section is empty it is omitted entirely.

### Row Format

Each branch row (within 44-char column width):

| Field | Content |
|---|---|
| current marker | `▶ ` if current branch, `  ` otherwise |
| status symbol | `✓` / `↑N` / `↓N` / `↑N↓N` / `local` |
| branch name | truncated to fit |
| upstream ref | dimmed, truncated — omitted for local-only |

Color coding:
- `✓` → green
- `↑` only → yellow  
- `↓` only → red  
- `↑↓` (diverged) → yellow  
- `local` → dim  
- current branch marker `▶` → cyan

### Behavior

- On project selection: load branches, render list, auto-scroll to current branch.
- Navigation: up/down keys move through branch items (section headers are skipped).
- On project change: list clears and reloads.
- No project selected: show placeholder text (same as current: "Select a project to see git status.").
- Fetch (Ctrl+F): existing app-level binding, triggers refresh after completion.

### Data Layer

No changes to `hub/tui/git.py`. The existing `get_branches(path)` function returns all required data:
- `name`, `upstream`, `ahead`, `behind`, `is_current`, `is_local_only`

### Implementation Scope

**Changed:**
- `hub/tui/panels/git.py` — full rewrite of `GitPanel`: replace `Static` with `ListView`, add `BranchItem` and `SectionHeader` widget classes, update `_load_git_info` / render flow.

**Updated:**
- `tests/test_tui_git_panel.py` — update tests to query `ListView` instead of `#git-content Static`; add tests for section headers and branch rows.

**Unchanged:**
- `hub/tui/git.py` (data functions)
- `hub/tui/app.py` (app bindings, layout)
- `hub/tui/panels/projects.py`, `hub/tui/panels/tasks.py`

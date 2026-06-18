# Design: TODO.md → SQLite Sync

**Date:** 2026-06-18
**Status:** Approved

## Overview

Add one-way sync from each project's `TODO.md` file into the hub SQLite database, so the TUI tasks panel reflects the latest state of the markdown file.

## Decisions

| Question | Decision |
|---|---|
| Sync direction | One-way: TODO.md → SQLite |
| Source of truth | TODO.md wins on conflict (overwrites SQLite) |
| Trigger: bulk | On hub startup — sync all registered projects |
| Trigger: single | `ctrl+r` in TasksPanel — sync current project only |
| Conflict key | `(project_id, title)` exact match |
| Deleted tasks | SQLite-only tasks are never removed (may be TUI-created) |

## TODO.md Format Support

Two formats coexist and must both be parsed.

**Format 1** — capture-todo output (section-based status):
```markdown
## 🚧 待开发
### Task title
**优先级**: P2 | **日期**: 2026-06-14
Description
---
## ✅ 已完成
### Done task title
```

**Format 2** — older format (checkbox-based status):
```markdown
### [ ] Task title
**优先级**: P3 | **日期**: 2026-06-14
---
### [x] Completed task
```

Parser rules:
- `## ` heading → sets current section state (`待开发` = todo, `已完成` = done)
- `### ` heading → starts new task; extract checkbox if present (`[ ]` / `[x]`)
- Checkbox in title overrides section state
- `**优先级**: Px` regex → priority; default P2 if absent
- `**日期**: YYYY-MM-DD` regex → created_at; default to sync time if absent
- `---` → ends current task entry
- Description lines are parsed but not stored (no `description` column in current schema)

## Upsert Logic

For each task parsed from TODO.md:
1. Lookup by `(project_id, title)` in SQLite
2. **Found** → `UPDATE status, priority` (TODO.md overwrites)
3. **Not found** → `INSERT` with parsed priority, status, created_at

Tasks in SQLite not present in TODO.md are left untouched.

## New Files

### `hub/core/todo_sync.py`

```
parse_todo_md(path: Path) -> list[dict]
    Parses a TODO.md file, returns list of:
    {title, status, priority, created_at}

sync_project(db, name: str, path: str) -> dict
    Reads {path}/TODO.md, upserts tasks for project `name`.
    Returns {imported: int, updated: int, skipped: int}
    Silently returns {skipped: 0} if TODO.md does not exist.

sync_all_projects(db) -> dict
    Iterates all projects with a non-empty path, calls sync_project.
    Logs warning on per-project failure, never raises.
    Returns aggregate {imported, updated, skipped}.
```

## Modified Files

### `hub/__main__.py`

Before launching the TUI, call:
```python
sync_all_projects(db)
```

Wrapped in try/except — failure must never block startup.

### `hub/tui/panels/tasks.py`

Add binding:
```python
Binding("ctrl+r", "sync_from_file", "Sync", show=True)
```

`action_sync_from_file`:
1. Look up current project's path from DB
2. If no path → `notify("No local path for this project", severity="warning")`
3. Call `sync_project(db, self._project, path)`
4. Call `_reload()`
5. `notify(f"Synced: {result['imported']} imported, {result['updated']} updated")`

## Non-Goals

- Bidirectional sync (writing TUI changes back to TODO.md)
- File watching / auto-sync on file change
- Storing task descriptions in SQLite
- Sync on project selection in TUI

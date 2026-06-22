---
migrated: 2026-06-21
docs:
  - explanation/hub-architecture.md  # 整体架构、数据层设计、p-launch 演进路径
  - reference/hub-reference.md       # CLI 接口（projects/tasks 命令已在此文件）
---

# hub — Design Spec

**Date:** 2026-06-14  
**Status:** Approved  

---

## Product Vision

hub is a personal developer OS — a single terminal interface that unifies project management, git status, and task tracking. It replaces p-launch and todo-tool as two separate tools with one cohesive product.

Two usage paths:
- **Human → TUI**: Textual-based three-column terminal interface
- **Agent → CLI**: `hub <command> --json` for structured, scriptable access

---

## Architecture

### Approach: Shared Python library + dual entry points

```
hub (TUI, no args)          hub <cmd> --json (CLI)
        ↘                       ↙
         core/  (pure Python, no UI deps)
     projects · tasks · db
              ↓
           SQLite
```

`core/` has no dependency on Textual or Typer. TUI and CLI import from it independently.

### Package structure

```
tools/hub/
├── core/
│   ├── projects.py     # project registry: scan, add, list, path lookup
│   ├── tasks.py        # task CRUD
│   └── db.py           # SQLite connection, schema, migrations
├── cli/
│   ├── __init__.py     # Typer app, global --json flag
│   ├── projects.py
│   └── tasks.py
├── tui/
│   ├── app.py          # Textual App entry point
│   └── panels/         # ProjectsPanel, GitPanel, TasksPanel
├── __main__.py         # no args → TUI; args → CLI
└── pyproject.toml
```

Tech stack: **Python 3 + Textual** (inherited from p-launch).

---

## Data Layer

### Storage layout

```
~/.hskill/
├── public/
│   └── PROJECTS.md     # human-readable project registry (agent: Read directly)
└── hub/
    └── tasks.db        # SQLite task store (agent: use CLI --json)
```

**Design principle:** structured queries use SQLite; the project list stays as a readable file so agents can access it without the CLI installed.

### Schema

```sql
projects (id, name, path, description, github_url, last_opened_at)
tasks    (id, title, project_id, priority, status, created_at)
```

`PROJECTS.md` is written on every project add/sync. It is never the write target — SQLite is the source of truth; `PROJECTS.md` is a derived export.

### Migration from existing tools

- `PROJECTS.md` path unchanged — hub inherits it directly
- `~/.local/share/todo/tasks.db` → `~/.hskill/hub/tasks.db` via one-time migration script run on first launch

---

## CLI Interface

Entry point: `hub`

```bash
# Projects
hub projects list [--json]
hub projects add <name> --path <path> [--desc <desc>]
hub projects sync                        # re-scan configured dirs, update PROJECTS.md
hub projects path <name>                 # print path (for shell/agent cd)

# Tasks
hub tasks list [--project <name>] [--status todo|done|blocked] [--priority P1|P2|P3] [--json]
hub tasks add <title> --project <name> [--priority P1|P2|P3]
hub tasks done <id>
hub tasks update <id> [--status <s>] [--priority <p>] [--title <t>]
hub tasks rm <id>
```

### JSON output contract

Every command with `--json` returns:

```json
{ "ok": true,  "data": [...] }
{ "ok": false, "error": "project 'foo' not found" }
```

Exit code `0` on success, non-zero on error. Agents can gate on exit code without parsing body.

### Agent access patterns

| Goal | Method |
|------|--------|
| List projects | `Read ~/.hskill/public/PROJECTS.md` (no CLI needed) |
| Get project path | `hub projects path <name> --json` |
| List open tasks | `hub tasks list --project <name> --status todo --json` |
| Create task | `hub tasks add "title" --project <name>` |
| Mark done | `hub tasks done <id>` |

---

## TUI Layout

Three-column layout, Textual framework:

```
┌─ hub ──────────────────────────────────────────────────────────────────┐
│ Col 1 (172px)  │ Col 2 (258px)          │ Col 3 (flex)                │
│ ─────────────  │ ──────────────────────  │ ──────────────────────────  │
│ PROJECTS    4  │ video-learner      GIT  │ Tasks · video-learner       │
│ ▸ video-learn 3│                         │                             │
│ ◦ harveyz-sk 2│ BRANCH                  │ TODO — 3                    │
│ ◦ blog       1│ local    main           │ ☐ Fix transcript sync   P1  │
│ ◦ raycast-ext │ tracking origin/main    │ ☐ Update ffmpeg deps    P1  │
│               │ sync     ↑ 2 ahead      │ ☐ Add dark mode toggle  P2  │
│               │                         │                             │
│ ● 4 synced    │ WORKING TREE            │ DONE — 2                    │
│               │ working  3 mod, 1 new   │ ☑ Write integration tests  │
│               │                         │ ☑ Update README             │
│               │ RECENT COMMITS          │                             │
│               │ cb01258 fix: sync… 1h   │                             │
│               │ 4a41385 feat: add… 3h   │                             │
│               │                         │                             │
│               │ fetched 2 min ago [f]   │                             │
├───────────────┴─────────────────────────┴─────────────────────────────┤
│ j/k navigate  tab switch col  enter open  f fetch  n new  space done  │
└────────────────────────────────────────────────────────────────────────┘
```

### Keyboard bindings

| Key | Action |
|-----|--------|
| `j` / `k` | Navigate within focused column |
| `Tab` | Cycle focus: Projects → Git → Tasks |
| `Enter` | Open project in terminal (from Projects or Git col) / toggle task (from Tasks col) |
| `f` | Fetch remote for active project |
| `n` | New task (bound to active project) |
| `Space` | Toggle task done/todo |
| `D` | Delete focused task (with confirm) |
| `/` | Live-filter tasks |
| `q` | Quit |

### Column responsibilities

- **Col 1 (Projects):** Project list, task count badge, sync status
- **Col 2 (Git):** Branch, tracking, ahead/behind, working tree dirty state, recent commits, last fetch time. This is p-launch's core functionality.
- **Col 3 (Tasks):** Tasks for active project, grouped todo/done, search filter, new task input

Future panels (behind `[` `]` tab switch in Col 3): Notes, etc.

---

## Migration Path

### Phase 1 — hub skeleton
- Create `tools/hub/` with `core/`, `cli/`, `tui/`
- Migrate p-launch project scan + index logic → `core/projects.py`
- Migrate todo-tool task logic → `core/tasks.py` + `core/db.py`
- CLI entry point working: `hub projects list`, `hub tasks list --json`

### Phase 2 — TUI
- Build Textual app with three-column layout
- Port p-launch's `PLaunchApp` as base for Git panel
- Wire Tasks panel to `core/tasks.py`
- `hub` (no args) launches TUI

### Phase 3 — Retire old tools
- p-launch and todo-tool marked deprecated in `hskill`
- First launch of hub runs data migration automatically
- Old commands continue working until next major version

### tool.json

```json
{
  "name": "hub",
  "version": "1.0.0",
  "description": "personal developer OS — projects, git status, tasks",
  "extraPaths": ["core", "cli", "tui", "pyproject.toml"],
  "uninstallPaths": ["~/.hskill/tools/hub/venv"],
  "configPaths": ["~/.hskill/hub"]
}
```

---

## Out of Scope (deferred)

- Notes / context panel (no concrete use case yet)
- Remote sync / multi-machine
- Time tracking
- OV-3: server.py hot-path sync in todo-tool
- OV-5: venv upgrade on tool update

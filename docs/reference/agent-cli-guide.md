# hskill Agent CLI Guide

Reference for AI agents and CI scripts calling `hskill` non-interactively.

---

## Quick rules

| Rule | Detail |
|------|--------|
| Always pass `--json` | Machine-readable output; errors route to stderr as JSON |
| Never omit `--skill`/`--tool`/`--bundle` | No-flag mode launches an interactive fzf picker and blocks forever in non-TTY |
| Always pass `--target` | Avoids a fzf target-selector that also blocks in non-TTY |
| `--skill` and `--tool` are mutually exclusive | Use `--bundle` if a bundle contains both |
| Set `NO_COLOR=1` if you parse stderr | Strips ANSI codes from status messages |
| stdout = data, stderr = logs | Only parse stdout; stderr is human-readable progress (or JSON errors in `--json` mode) |

---

## Self-discovery

Before hard-coding flags, fetch the live schema:

```bash
hskill --help --json
```

Returns a single JSON object:

```json
{
  "name": "hskill",
  "version": "0.6.2",
  "description": "...",
  "agent_notes": "Interactive mode requires TTY. Use --json for machine-readable output...",
  "commands": [
    {
      "name": "install",
      "note": "--skill and --tool are mutually exclusive; use --bundle to install both",
      "flags": [
        { "name": "--skill",  "arg": "<name>",   "description": "..." },
        { "name": "--target", "arg": "<target>",  "enum": ["claude","cursor","codex","openclaw","hermes","all"] },
        { "name": "--scope",  "arg": "<scope>",   "enum": ["user","project"], "default": "user" },
        ...
      ]
    },
    ...
  ]
}
```

---

## Read-only queries

These commands never prompt and always exit 0 (unless the tool itself is broken).

### `status --json`

```bash
hskill status --json
```

```json
{
  "skills": [
    { "name": "skill-analyzer", "version": "1.0.0", "user": "none", "project": "none" }
  ],
  "tools": [
    { "name": "p-launch", "version": "1.2.0", "status": "up-to-date" }
  ]
}
```

`user` / `project` values: `"none"` | `"up-to-date"` | `"update"`

### `outdated --json`

```bash
hskill outdated --json
```

Same shape as `status --json` but only includes entries with `"update"` status. Returns `{ "skills": [], "tools": [] }` when everything is current.

### `list --json`

```bash
hskill list --json
```

```json
{
  "bundles": {
    "analysis": {
      "description": "分析工具（skill-analyzer）",
      "skills": ["analysis/skill-analyzer"]
    }
  },
  "tools": ["p-launch"]
}
```

### `info <name> --json`

```bash
hskill info skill-analyzer --json
```

```json
{
  "name": "skill-analyzer",
  "type": "skill",
  "version": "1.0.0",
  "user": {
    "claude":   { "version": "1.0.0", "status": "up-to-date" },
    "cursor":   { "version": "—",     "status": "none" },
    "codex":    { "version": "—",     "status": "none" },
    "openclaw": { "version": "—",     "status": "none" },
    "hermes":   { "version": "—",     "status": "none" }
  },
  "project": { ... }
}
```

For tools, `type` is `"tool"` and `installed` has a single `bin` key instead of per-target scopes.

---

## Install

### Minimal invocation

```bash
hskill install --skill skill-analyzer --target claude --scope user --json
```

### Output shape

A single JSON object is written to stdout only on success. Nothing is written to stdout on failure (error goes to stderr).

```json
{
  "skills": {
    "claude": {
      "installed": ["skill-analyzer"],
      "skipped":   [],
      "failed":    []
    }
  }
}
```

When installing tools, the top-level key is `tools` instead of `skills`:

```json
{
  "tools": {
    "installed": ["p-launch"],
    "skipped":   [],
    "failed":    []
  }
}
```

### `skipped` entries

```json
{ "name": "skill-analyzer", "reason": "up-to-date", "version": "1.0.0" }
{ "name": "skill-analyzer", "reason": "outdated",   "installed": "0.9.0", "available": "1.0.0" }
```

`"up-to-date"` — installed version matches available; no action needed.  
`"outdated"` — newer version exists but `--force` was not passed (non-TTY never prompts).

### `failed` entries

```json
{ "name": "skill-analyzer", "reason": "source_not_found" }
{ "name": "skill-analyzer", "reason": "error", "detail": "EACCES: permission denied" }
```

### Force-overwrite

```bash
hskill install --skill skill-analyzer --target claude --scope user --force --json
```

### Install multiple skills

```bash
hskill install --skill skill-analyzer,diataxis-docs --target claude --scope user --json
```

### Install a bundle

```bash
hskill install --bundle analysis --target claude --scope user --json
```

---

## Error handling

In `--json` mode all errors go to stderr as a JSON object and exit code is 1:

```json
{ "error": true, "message": "Unknown skill: \"typo-skill\"" }
```

stdout is empty on error — safe to parse stdout unconditionally.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (unknown skill/tool, mutual exclusion violation, unexpected exception) |

---

## Non-TTY behavior reference

| Situation | Behavior |
|-----------|----------|
| No `--skill`/`--tool`/`--bundle` flag | Exits 1 with error; never launches fzf |
| Skill already installed, same version | Skipped with `reason: "up-to-date"`; no prompt |
| Skill already installed, older version | Skipped with `reason: "outdated"`; use `--force` to update |
| Tool already installed, no `--force` | Skipped with `reason: "already_exists"`; no prompt |
| Skill/tool has `vars.json` | Default values applied automatically; no prompt |
| Tool has `zshrc.snippet` | Patch skipped with a stderr note; apply manually |

---

## Recommended agent workflow

```
1. hskill status --json          → check what's already installed
2. hskill outdated --json        → check for updates
3. hskill install --skill <s>    → install / update as needed
4. parse stdout JSON             → confirm installed/skipped/failed
5. check exit code               → 0 = ok, 1 = error (read stderr JSON)
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal Claude Code skills repository for Harvey. Skills are self-contained directories installed to `~/.claude/skills/` to extend Claude Code's capabilities.

## Installation

```bash
# Install all skills
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/

# Install git branch-protection hooks (optional, for this repo)
bash scripts/git/install-git-hooks.sh
```

The git hooks block direct commits to `main` and `staging` — use feature/fix/chore/doc branches merged via staging.

## Skill Structure

Skills live under `skills/`. Two patterns exist:

**Flat skill** (`skills/harvey-plain/`):
```
harvey-plain/
├── SKILL.md        # Skill definition — sole entry point
└── references/     # (optional) reference docs
```

**Skill group** (`skills/superpowers/`): subdirectory containing multiple related skills, each with their own `SKILL.md`.

The `skill-analyzer` skill uses an extended layout with a `research/` directory holding iteration records and analysis — it tracks its own development history.

## SKILL.md Format

Standard frontmatter (required for Claude Code to register the skill):

```yaml
---
name: skill-name
description: "What this skill does. Trigger phrases..."
user_invocable: true|false
version: "x.x.x"
---
```

The `skill-analyzer` skill omits this frontmatter (uses a custom header instead) — this is intentional but non-standard.

## Naming Convention

- Flat skills: `harvey-` prefix (e.g., `harvey-plain`)
- Skill groups: group name as directory, skills inside use plain `{name}` (e.g., `brainstorming` inside `superpowers-fork/`)

## Shared Output Conventions

Skills that produce org-mode output follow these rules:

**Org-mode syntax:**
- Bold: `*text*` (single asterisk — never `**text**`)
- Headings start at `*`, no skipped levels

**Denote file naming:** `{YYYYMMDDTHHMMSS}--{title}__{type}.org`  
**Output directory:** `~/Documents/notes/`  
**Timestamp command:** `date +%Y%m%dT%H%M%S`

**ASCII art** — allowed: `+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "`  
Forbidden: Unicode box-drawing characters (e.g., `┌ │ └`)

## Plugin Manifest

`.claude-plugin/plugin.json` declares the plugin metadata for Claude Code's skill discovery. The `"skills": "./skills"` field points to the skills directory.

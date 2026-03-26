# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Overview

This is a personal Claude Code skills repository for Harvey. Each skill is a self-contained directory that can be installed to `~/.claude/skills/` to extend Claude Code's capabilities.

## Repository Structure

```
my-skill-repository/
├── .claude-plugin/
│   └── plugin.json       # Claude Code plugin manifest
├── skills/               # All skills live here
│   └── harvey-*/         # Each skill is a prefixed directory
│       ├── SKILL.md      # Skill definition
│       ├── references/   # (optional) Reference docs
│       ├── assets/       # (optional) Templates, scripts
│       └── scripts/      # (optional) Helper scripts
├── scripts/              # (optional) Shared scripts across skills
├── README.md
└── .gitignore
```

## Skill Format

Each `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name
description: "What this skill does. Use when user says..."
user_invocable: true|false
version: "x.x.x"
---
```

## Installation

Copy skills to Claude Code's skills directory:

```bash
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

## Skill Naming Convention

Prefix: `harvey-` (e.g., `harvey-plain`, `harvey-paper`)

## Shared Conventions

**Org-mode output:**
- Bold: `*text*` (single asterisk)
- Filenames: `{timestamp}--{title}__{type}.org`
- Output directory: `~/Documents/notes/`
- Timestamps: `date +%Y%m%dT%H%M%S`

**ASCII Art:**
- Allowed: `+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "`
- Forbidden: Unicode box-drawing characters

## Development Guidelines

- Skills are atomic — each skill directory is self-contained
- Version numbers are manually maintained in SKILL.md frontmatter
- External dependencies are declared in SKILL.md or a `references/deps.md`

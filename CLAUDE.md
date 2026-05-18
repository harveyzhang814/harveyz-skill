# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Personal Claude Code skills repository for Harvey. Skills are self-contained directories installed to `~/.claude/skills/` to extend Claude Code's capabilities.

## Installation

```bash
# Recommended: global install
npm install -g harveyz-skill
hskill                          # interactive install

# Or manual install
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/

# Install git branch-protection hooks (optional, for this repo)
bash scripts/git/install-git-hooks.sh
```

The git hooks block direct commits to `main` and `staging` — use feature/fix/chore/doc branches merged via staging.

## Skill Structure

Skills live under `skills/`. Two patterns:

- **Flat skill** (`skills/harvey-plain/`): single `SKILL.md` + optional `references/`
- **Skill group** (`skills/superpowers/`): subdirectory with multiple skills, each with their own `SKILL.md`

## SKILL.md Format

```yaml
---
name: skill-name
description: "What this skill does. Trigger phrases..."
user_invocable: true|false
version: "x.x.x"
---
```

## Naming Convention

- Flat skills: `harvey-` prefix (e.g., `harvey-plain`)
- Skill groups: group name as directory, skills inside use plain `{name}`

## Shared Output Conventions

Skills that produce org-mode output:

**Org-mode syntax:** Bold: `*text*` (single asterisk). Headings start at `*`, no skipped levels.

**Denote file naming:** `{YYYYMMDDTHHMMSS}--{title}__{type}.org` → `~/Documents/notes/`

**ASCII art** — allowed: `+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "` — no Unicode box-drawing characters.

## Publishing a New Skill

1. Create `skills/<category>/<skill-name>/SKILL.md`
2. Add to `skills-index.json` under `skills[]` with `path` and `bundle`; add to `bundleMeta` if bundle is new

`skills-index.json` is the single source of truth. Skills absent from it are excluded from npm.

## 测试

```bash
npm test
```

`tests/agent-cli.bats` — CLI 输出格式；`tests/install.bats` — flag 安装，断言文件系统；`tests/interactive.bats` — fzf 交互循环。

写新测试前读 [docs/reference/testing-guide.md](docs/reference/testing-guide.md)。

## Git 工作流

分支命名规范与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。

**分支使用规范：** 一个功能或迭代使用一个分支，积累所有相关改动，只在用户明确说"合并"或"完成"时才 merge 到 staging。不要为每次 commit 单独创建新分支。

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the **source maintenance repository** for Harvey's Claude Code skills. Skills are authored and maintained here under `skills/`, then published/installed to `~/.claude/skills/`.

**Important:** This repo is the authoritative source for all skills. When looking up, reading, or editing any skill's content, always work within the `skills/` directory here — never in the installed copy at `~/.claude/skills/` or any Claude user-level directory. `~/.claude/skills/` is the deployment target; its contents may lag behind this repo.

Skills are self-contained directories installed to `~/.claude/skills/` to extend Claude Code's capabilities.

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

Skills that produce Markdown reports (e.g. `learn-skill`) save `.md` files with YAML frontmatter to a user-configured `skillDir`. These are not subject to the org-mode or Denote naming conventions above.

## Publishing a New Skill

1. Create `skills/<category>/<skill-name>/SKILL.md`
2. Add to `skills-index.json` under `skills[]` with `path` and `bundle`; add to `bundleMeta` if bundle is new

`skills-index.json` is the single source of truth. Skills absent from it are excluded from npm.

## 测试

```bash
npm test
```

hskill CLI 行为（安装、交互、JSON 输出）+ 所有 skill 的 SKILL.md 格式校验。

写新测试前读 [docs/reference/testing-guide.md](docs/reference/testing-guide.md)。

## Git 工作流

分支命名规范与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。

**分支使用规范：** 一个功能或迭代使用一个分支，积累所有相关改动，只在用户明确说"合并"或"完成"时才 merge 到 staging。不要为每次 commit 单独创建新分支。

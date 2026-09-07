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

**合并方式：** 本仓库没有合并脚本，手动 `git checkout staging && git merge --no-ff <分支>` 即可（`.githooks/commit-msg` 不要求 `Merge-Via` 标记）。别照搬别的仓库的 `scripts/merge-to-staging.sh`，这里没有那个文件。

**worktree 路径习惯：** `.claude/worktrees/<slug>`，slug 是分支名去掉 `feature/`、`doc/` 等前缀（例如 `feature/handoff-node-relation` → `.claude/worktrees/handoff-node-relation`）。仓库里另有历史遗留的 `.worktrees/`，新建一律用前者。

## 跨 session 交接（handoff）

用 `/handoff` skill 交接任务时（约定详见 `.hskill/handoff/config.md`）。一条分支不能被两个 worktree 同时 checkout，这是唯一的硬约束，下面的规则都是从它推出来的：

**一次交接自始至终只用一个工作区，由交出方建、交出方留、交出方收。** 三方（交出方 author、接手方、验收方）轮流进同一个 worktree，谁都不另建。这不是省事，是唯一能闭环的形态：worktree 由交出方建，它就一直知道在哪；验收时直接回去读那份被接手方改过的文档，不必扫描、不必猜。若改成接手方自建，验收方回的是自己建的那个，看不到接手方的改动，交接链当场断掉。

1. 交出方在 worktree 里跑 `/handoff` author 写交接文档（落 `docs/commute/`），连同相关产物一起 commit 到那条分支（feature/doc 分支上随便提交，hook 只拦 staging/main）。**提交完成之后不要 `git worktree remove`**——这个工作区是接手方的落脚点，也是你验收时要回来的地方，它要一直活到验收通过、合并完成。
2. **交接时不合并到 staging。** 分支停在未合并状态等接手方接着做，最后一次性合并。
3. **交接文档 frontmatter 的 `branch` 与 `worktree` 成对，都由交出方填。** 分支名是权威载体，worktree 路径是那条分支当下的落脚点，必须写出来、不能让接手方去猜（本仓库两种路径习惯并存，见上）。路径万一失效，用 `git worktree list` 查这条分支现在挂在哪。
4. 接手方**不建 worktree、不建分支**，直接 `cd` 进文档里那个路径，核对当前分支与 `branch` 一致后开工，并补上 `git config core.hooksPath .githooks && git config merge.ff false`。那条分支已经被这个工作区 checkout，`git worktree add` 会直接失败——这是提示，不是障碍。
5. **验收也在这个工作区里跑，不在主工作树、不在 staging/main 上跑。** 主工作树停在 `staging`，那里根本没有接手方的改动；在那里跑出来的绿是别的代码的绿，比不跑更有害，因为它看起来像验过了。验收方 `cd` 回去，**先在那里重读一遍交接文档**——接手方的自测记录与 `status` 只存在于那一份里，你手上那份是 author 时的旧版。
6. **只有交出方能合并。** 接手方与验收方都不合。验收通过后由交出方 `git merge --no-ff` 进 staging，合完再 `git worktree remove` 收掉工作区。
7. **同一时刻只有一方在这个工作区里动手。** 交出方写完停手、接手方做完停手、再轮到验收方。两个 session 同时在一个工作区里跑 git 会互踩暂存区。

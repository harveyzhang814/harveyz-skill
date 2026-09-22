# Repository Agent Guide

## Overview

This is the source-maintenance repository for Harvey's agent skills. Skills are authored and maintained under `skills/`, then installed or published for one or more agent hosts.

`skills/` is the authoritative source. Read and edit skill content here, never in an installed copy or a host-level skill directory: installed copies are deployment targets and may lag behind the repository.

## Deploying skills

Always deploy a skill from the integrated `staging` branch, not from the current working tree. The current tree can be on an unfinished feature or documentation branch, so copying directly from it can silently install an older version.

```bash
git archive staging skills/coding/<skill> | tar -x -C <temporary-directory>
rsync -a --exclude '.DS_Store' <temporary-directory>/skills/coding/<skill>/ <target-skill-root>/<skill>/
```

`<target-skill-root>` is determined by the selected installation target. Do not assume a particular host's configuration directory. After deployment, check the installed `SKILL.md` version against the intended release.

## Skill structure and publishing

Skills live under `skills/<category>/<skill-name>/`. Each skill directory contains `SKILL.md` and may contain `references/`, scripts, assets, or tests.

`SKILL.md` starts with YAML frontmatter such as:

```yaml
---
name: skill-name
description: "What this skill does. Trigger phrases..."
user_invocable: true
version: "x.y.z"
---
```

When publishing a skill:

1. Create or update `skills/<category>/<skill-name>/SKILL.md`.
2. Register it in `skills-index.json` with its `path` and `bundle`.
3. Add `bundleMeta` when introducing a bundle.
4. Update the skill's `contentHash` and `contentVersion` when skill content changes.

`skills-index.json` is the packaging source of truth; unindexed skills are excluded from the npm package.

## Output conventions

For org-mode output, use single asterisks for bold text and start headings with `*` without skipping levels. Denote filenames use `{YYYYMMDDTHHMMSS}--{title}__{type}.org` and are written to `~/Documents/notes/`. ASCII diagrams may use only ASCII characters.

Markdown reports may use YAML frontmatter and a user-configured `skillDir`; they do not follow the org-mode or Denote rules.

## Testing

Run:

```bash
npm test
```

This verifies hskill CLI behavior and validates all `SKILL.md` files. Before adding tests, read [docs/reference/testing-guide.md](docs/reference/testing-guide.md).

## Git and worktree workflow

Read [docs/reference/git-workflow.md](docs/reference/git-workflow.md) for the complete branch and merge workflow.

- Use one `feature/`, `fix/`, `chore/`, `doc/`, or `release/` branch per related unit of work.
- Create a branch and worktree from an explicit `staging` baseline. Do not let the current checkout choose the base implicitly.
- Configure each worktree with `core.hooksPath=.githooks` and `merge.ff=false`.
- Before merging, confirm the current branch with `git rev-parse --abbrev-ref HEAD`.
- Merge to `staging` with `git merge --no-ff <branch>` only when the user explicitly asks to merge or finish. Do not directly commit to `main` or `staging`.

For example:

```bash
git worktree add <worktree-path> -b <type>/<slug> staging
git -C <worktree-path> config core.hooksPath .githooks
git -C <worktree-path> config merge.ff false
```

An agent host may provide its own way to bind subsequent operations to a worktree. Use it when available. Otherwise, every Git command must be scoped with `git -C <worktree-path>`, and file reads and writes must use absolute paths. A bare `cd` does not carry across independent command invocations.

`.claude/worktrees/` is an existing repository path convention, including historical directories; it is not a required host API or a universal worktree location.

## Cross-session handoff

`handoff` is a general-purpose skill, not a Claude-specific feature. In hosts that support skill invocation, invoke `handoff`; otherwise execute the workflow defined by the skill. Read `.hskill/handoff/config.md` for this repository's output location, Git workflow, verification commands, and authority references.

Keep the skill's four phases: `author`, `verify`, `self-test`, and `accept`. Slash-command syntax, if a host offers it, is only one invocation interface and is not part of the process requirement.

For a handoff involving a separate branch and worktree:

1. The author creates the branch and worktree, records their absolute path and branch in the handoff document, and keeps that worktree available.
2. The recipient verifies the handoff and works in that same worktree; they do not create a replacement worktree or branch and do not remove it.
3. The author returns to that same worktree to accept the result. Acceptance runs there, not in the main checkout or an integration branch.
4. Only the author merges the accepted branch and removes the handoff worktree afterward.

Only one party may operate in a shared handoff worktree at a time. If the host cannot enter a worktree directly, use the explicit-path fallback described above.

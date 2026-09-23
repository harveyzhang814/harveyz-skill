# Handoff Codex Host Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make handoff host-neutral at its core while preserving Claude behavior and proving the full workflow on Codex.

**Architecture:** Retain the existing workflow and add a small host-adapter section plus optional workspace metadata. The validator infers legacy behavior so current Claude handoffs remain valid, while Codex receives explicit invocation and workspace instructions.

**Tech Stack:** Markdown skills, Bash validator, Bats tests, Claude Code CLI, Codex CLI.

**Spec:** `docs/superpowers/specs/2026-09-22-handoff-codex-host-adapter-design.md`

## Global Constraints

- Edit the authoritative source under `skills/coding/handoff/`, never an installed copy.
- Preserve all four phases and single-writer worktree ownership.
- Do not merge to `staging` unless the user explicitly asks.
- Update `skills-index.json` content metadata after skill content changes.

## Review Focus

- Legacy documents with no `workspace_mode` must validate exactly as before.
- Shared worktrees with only half of the branch/path pair must fail structurally.
- Detached or disposable host-managed worktrees must not be presented as durable fresh-session handoff workspaces.
- Generated receiver instructions must select the correct host invocation syntax.
- Acceptance must run in the recorded workspace, not the main checkout.

---

### Task 1: Extend validator behavior

**Files:**
- Modify: `skills/coding/handoff/tests/validate-handoff.bats`
- Modify: `skills/coding/handoff/scripts/validate-handoff.sh`

**Interfaces:**
- Consumes: existing YAML frontmatter parser and error/warning collectors.
- Produces: backward-compatible validation for `workspace_mode` and `commit`.

- [ ] Add Bats cases for valid/invalid modes, shared-worktree pairing, base-commit resolution, and detached-worktree rejection.
- [ ] Run the focused suite and confirm the new cases fail for the missing behavior.
- [ ] Implement mode inference and validation.
- [ ] Run the focused suite and confirm all old and new cases pass.

### Task 2: Adapt skill and project configuration

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`
- Modify: `skills/coding/handoff/assets/handoff-template.md`
- Modify: `skills/coding/handoff/references/config-schema.md`
- Modify: `.hskill/handoff/config.md`
- Modify: `skills-index.json`

**Interfaces:**
- Consumes: host identity and recorded workspace metadata.
- Produces: host-specific invocation/entry instructions with unchanged workflow semantics.

- [ ] Replace universal slash-command wording with a host invocation table.
- [ ] Add Codex workspace guidance while retaining Claude native tool guidance.
- [ ] Document optional workspace metadata and legacy inference in the template/schema.
- [ ] Make repository config host-conditional and make `AGENTS.md` primary authority.
- [ ] Bump the skill minor version and recompute the package content hash.

### Task 3: Behavioral verification

**Files:**
- Create only temporary external test repositories and captured logs; do not add generated artifacts to this repository.

**Interfaces:**
- Consumes: the baseline and modified skill packages.
- Produces: observable Claude regression and Codex end-to-end evidence.

- [ ] Run the same Claude scenario against baseline and modified skills; compare phase/workspace/status invariants.
- [ ] Run Codex author in a fresh test repository.
- [ ] Run a separate Codex receiver through verify, implementation, self-test, and `待验收`.
- [ ] Run a separate Codex acceptor, rerun the anchor, and verify `已验收`.
- [ ] Run focused validation plus full `npm test`, inspect the final diff, and report any limitations.

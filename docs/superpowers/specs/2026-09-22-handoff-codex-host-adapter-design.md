# Handoff Codex Host Adapter Design

## Overview

Make the cross-session `handoff` skill executable on Codex without changing the four-phase contract or Claude Code's established behavior.

## Compatibility contract

- Preserve `author -> verify -> self-test -> accept`, single-writer worktree ownership, the handoff document as the truth source, and independent acceptance.
- Keep Claude Code's `EnterWorktree(path: ...)` and `ExitWorktree(action: "keep")` instructions available and behaviorally unchanged.
- Describe invocation by host: Claude Code uses `/handoff <phase>`, Codex uses `$handoff <phase>`, and hosts without skill syntax execute the named phase directly.
- For a fresh Codex session, use a durable author-created shared worktree and named branch. Do not treat Codex App Handoff or a disposable managed worktree as equivalent to a fresh-session handoff.
- Codex enters an existing handoff workspace by launching with that directory as the workspace or by scoping every operation to the recorded absolute path. It must not create a replacement worktree.

## Document schema

Add optional frontmatter fields without invalidating existing documents:

- `workspace_mode: same-workspace | shared-worktree`
- `base_commit: <40-hex commit>` as an optional branch-point anchor

If `workspace_mode` is absent, infer the legacy behavior: `shared-worktree` when `branch` or `worktree` is present, otherwise `same-workspace`.

Validation rules:

- `same-workspace` does not require branch/worktree.
- `shared-worktree` requires both a named branch and an absolute worktree root.
- A supplied base commit must resolve in the repository.
- A detached or disposable host-managed worktree is not a valid fresh-session handoff workspace; promote the work to a named branch in a durable shared worktree first.
- Existing legacy documents retain their current validation outcome.

## Repository configuration

Keep project workflow facts in `.hskill/handoff/config.md`, but express entry/exit as host branches instead of treating Claude tools as universal. `AGENTS.md` is the primary repository authority; `CLAUDE.md` remains a Claude-specific supplemental authority.

## Testing strategy

1. Add validator tests first and observe them fail.
2. Run the focused Bats suite and full `npm test` after implementation.
3. Run a real Claude Code regression scenario before and after the change, comparing phase decisions and artifacts rather than transcript wording.
4. Run a real Codex multi-session scenario through author, verify, implementation, self-test, and independent accept in the same shared worktree.

## Acceptance criteria

- All pre-existing handoff validator tests remain green.
- New workspace-mode and commit-anchor tests pass.
- Claude Code still uses its native worktree entry/keep behavior and reaches the same phase outcomes.
- Codex creates or consumes the handoff document, uses the author's workspace, records self-test evidence before `待验收`, and independently marks the result `已验收` only after rerunning the anchor.

# High-priority cross-platform skill remediation design

## Overview

Remove the high-priority Claude-only assumptions found in seven published skills while preserving their shared workflow semantics. The source of truth remains `skills/`; all edits are made on `fix/cross-platform-high-priority`, created from `staging` at `3f330cb`.

## Goals

- A published shared `SKILL.md` must not require a Claude installation path, native Claude tool name, or `/loop` command to perform its core workflow.
- Claude-specific invocation may remain available as an explicit adapter or example, never as the only path.
- Each changed published skill receives a patch version and an accurate `skills-index.json` content-version record.
- The Codex `clip-url` adapter must be backed by a no-write in-host delegation smoke test, with a sequential fallback when delegation is unavailable.

## Non-goals

- Do not rewrite every historical Claude reference in the repository or unindexed archived skills.
- Do not force every host to have an identical interactive UI, scheduler, or subagent API.
- Do not change the documented user approval boundaries for filesystem writes, external configuration, branch creation, or browser profiles.

## Design

### Shared portability rule

Executable assets are addressed relative to the directory containing the loaded `SKILL.md`, called `SKILL_DIR`. A host may provide that directory directly; otherwise the agent discovers the installed skill directory or asks the user. Shared instructions must not synthesize a `~/.claude/skills/` path from a skill name.

Host-native facilities are specified as capabilities: ask the user, search, request structured text, download a binary file, schedule/repeat work, or delegate a stage. A host adapter may name the local facility. If a capability is absent, the shared workflow declares a safe fallback rather than pretending that a different host API exists.

### Per-skill changes

| Skill | Change |
|---|---|
| `capture-vocab` | Replace all hard-coded script paths in the entrypoint and write-operation reference with `SKILL_DIR/scripts/vocab.py`. |
| `init-project` | Select an active hskill target instead of reading only Claude status or installing only to Claude. Rename the generated instruction skeleton to `AGENTS.md` and use platform-neutral contents. |
| `contribute-skill` | Treat the source skill directory as a verified explicit path. Store its local cache under `~/.hskill/contribute-skill/`; preserve the exact source path for bidirectional sync. |
| `forge-doc` | Resolve scripts, assets, and previews through `SKILL_DIR`. Replace `AskUserQuestion` with the host question capability plus ordinary conversation fallback. |
| `fetch-paper` | Replace named `WebSearch`/`WebFetch` requirements and the temporary-path promise with capability language. Download candidates to a temporary file using the host downloader or a shell fallback, then validate MIME or `%PDF-`. |
| `init-goal` | Make the generated result a host-neutral sustained-work prompt. Keep `/loop` only in a Claude adapter/example; other hosts use their native task mechanism or a manual continuation fallback. |
| `clip-url` Codex patch | Remove the unverified stop-and-ask gate. Record the supported Codex delegation mechanism only after a no-write smoke test; otherwise specify sequential execution of the three stages. |

### Packaging

Increment each changed skill's patch version. Update the matching `skills-index.json` entry's `contentHash` and `contentVersion`; add those fields for `init-project`, which currently lacks them. Hashes use the repository's established publish-skill F8 algorithm: normalize the `version:` value to a placeholder, hash the normalized content with SHA-256, then retain the first 16 hexadecimal characters.

## Validation

1. Add a focused portability test covering the seven published entrypoints/adapters. It asserts behavioral invariants: no required Claude path or native Claude tool remains in shared flow, while allowed host adapter files remain exempt.
2. Run targeted existing tests for `capture-vocab`, `forge-doc`, `init-goal`, and `clip-url`; run the relevant Node static test.
3. Use a temporary HOME to install a representative changed skill for both Claude and Codex and verify target-specific status parsing without touching user installations.
4. Execute one no-write Codex delegation smoke test. If unavailable, verify the sequential fallback wording instead of recording speculative syntax.
5. Run `npm test` with the opt-in real Claude hook E2E isolated. Report it separately because its existing CLI invocation has no timeout and is not a deterministic compatibility gate.

## Risks and mitigations

- `init-project` affects new repository skeletons: only new initialization uses `AGENTS.md`; existing projects are not renamed or rewritten.
- The broad `fetch-paper` workflow may lose host-specific convenience: its search/download decision order and legal-source restrictions remain unchanged, and only transport mechanics become host-neutral.
- Codex delegation can vary by host version: the patch includes a verified mechanism only when the smoke test proves it, with a safe sequential fallback otherwise.

## Acceptance criteria

- All seven high-priority findings are remediated in published source, with no new Claude-only hard dependency in their shared paths.
- Claude behavior remains an available adapter where it was previously supported.
- Static and targeted runtime checks pass; any external or opt-in test is clearly reported as passed, skipped, or failed.
- The worktree contains only scoped source, test, manifest, and design-document changes.

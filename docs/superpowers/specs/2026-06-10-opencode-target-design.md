# hskill opencode target support

**Date:** 2026-06-10

## Goal

Add `opencode` as a supported skill installation target in hskill, alongside claude/cursor/codex/openclaw/hermes.

## Key Constraint

opencode uses XDG convention for its config directory, so the user-level path is non-standard:
- User-level: `~/.config/opencode/skills` (not `~/.opencode/skills`)
- Project-level: `.opencode/skills` (same pattern as other targets)

## Architecture

### Path resolution

Introduce `USER_DIR_OVERRIDES` map in `targets.js` and extract a `userSkillDir(name)` export. Both `skillDir()` (used by `resolveTargets`) and `checkInstalled()` in `bundles.js` call this function, ensuring the correct path is used everywhere.

```
USER_DIR_OVERRIDES = { opencode: '~/.config/opencode/skills' }

userSkillDir(name) → USER_DIR_OVERRIDES[name] ?? '~/.{name}/skills'
skillDir(name, scope) → user: userSkillDir(name), project: './{name}/skills'
checkInstalled → user: checkScope(t => userSkillDir(t))
```

opencode is NOT added to `USER_ONLY_TARGETS` — project scope is supported.

## Files Changed

| File | Change |
|---|---|
| `lib/targets.js` | Add `opencode` to `SKILL_TARGETS`, `TARGETS`; add `USER_DIR_OVERRIDES`; export `userSkillDir()`; update `skillDir()` |
| `lib/bundles.js` | Import and use `userSkillDir()` in `checkInstalled` |
| `bin/cli.js` | Add `opencode` to `ALL_SKILL_TARGETS` and help text |
| `tests/install.bats` | Add opencode install test cases |

## Non-goals

- Frontmatter transformation (not done for any target)
- opencode-specific agent format conversion

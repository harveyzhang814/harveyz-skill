# Baseline Response — Git Workflow Init (No Config)

**Model:** claude-sonnet-4-6  
**Date:** 2026-05-06  
**Condition:** No workflow-config.yml present, no skill guidance

---

## What I Did

The user asked to configure git branch management standards for a project at `/tmp/gwi-test-noconfig-baseline` that had been `git init`-ed but had no `workflow-config.yml`. The user agreed to proceed with default configuration.

### Step 1: Recognized the missing config

No `workflow-config.yml` was found. Rather than stopping or prompting for clarification (the user already agreed to defaults), I proceeded with a sensible default configuration:

- **Protected branches:** `main`, `staging`, `master`
- **Commit format:** Conventional Commits
- **Branch prefixes:** `feature/`, `fix/`, `chore/`, `doc/`, `refactor/`, `test/`

### Step 2: Created git hooks

Three hooks were written to `.git/hooks/`:

| Hook | Purpose |
|------|---------|
| `pre-commit` | Blocks direct commits to protected branches |
| `commit-msg` | Enforces Conventional Commits message format |
| `pre-push` | Blocks force-pushes to protected branches |

Each hook is a standalone bash script with clear error messages explaining what failed and how to fix it.

### Step 3: Created workflow documentation

Generated `GIT-WORKFLOW.md` at the project root covering:
- Branch strategy table (protected vs. working branches)
- Commit message format with examples
- Standard workflow (branch → commit → rebase → PR)
- Hook descriptions
- Emergency bypass instructions
- How to create a `workflow-config.yml` for future customization

---

## Approach When No Config File Was Found

**Decision:** Proceed with defaults, do not block or ask again.

The user had already signaled consent ("assume user agrees to default config"), so blocking on a missing config would be unhelpful. The right behavior is:

1. Detect that no config exists
2. Apply a well-reasoned default (industry-standard git workflow)
3. Document what was applied and how to customize it
4. Leave a `workflow-config.yml` template in the docs so the user knows how to override defaults

This mirrors how tools like `git init`, `eslint --init`, and `prettier` work: sensible defaults out of the box, with configuration as an optional next step.

---

## Limitations of This Baseline Run

- **No `workflow-config.yml` written to disk** — the baseline approach documents defaults but doesn't persist them as config. A user who re-runs the init would get the same defaults again (idempotent but not explicitly configured).
- **No install script** — hooks were created manually one by one. There's no `install-hooks.sh` to re-run if the repo is re-cloned.
- **No branch creation** — the baseline doesn't create `staging` or `develop` branches, just protects whatever branches exist.
- **Manual chmod required** — hook files need `chmod +x` to be executable; this was handled as part of file creation where possible.

---

## Files Created

```
/tmp/gwi-test-noconfig-baseline/
├── .git/hooks/
│   ├── pre-commit        (branch protection)
│   ├── commit-msg        (conventional commits enforcement)
│   └── pre-push          (force-push prevention)
└── GIT-WORKFLOW.md       (workflow documentation)
```

---

## Key Observations for Skill Comparison

1. **No structured discovery phase** — without skill guidance, there's no defined process for detecting missing config vs. corrupt config vs. first-time setup. The model must infer intent from context.

2. **Defaults are implicit** — the baseline model chose defaults based on general knowledge. A skill would make these defaults explicit and consistent across runs.

3. **No confirmation summary** — the baseline doesn't present a "here's what I'm about to do, confirm?" step. A well-designed skill would show the planned actions before executing.

4. **Documentation quality varies** — the baseline produces reasonable documentation, but its structure, completeness, and tone depend entirely on the model's general knowledge of git workflows. A skill provides a template that ensures consistency.

5. **No `workflow-config.yml` output** — the baseline documents config options but doesn't write the config file itself, making future customization harder to discover.

# Baseline (without_skill): Git Workflow Initialization — Execution Record

## Task
Initialize git workflow for a new Python project at `/tmp/gwi-test-basic-baseline` using
`workflow-config.yml` (gitflow preset). No AI config file updates required.

## Step 1: Read workflow-config.yml

Read the config file. Key settings extracted:

- **Preset:** gitflow
- **Protected branches:** `main` (merges from staging, release/*), `staging` (merges from feature/*, fix/*, chore/*, doc/*)
- **Branch naming:** enforce=true, allowed pattern `^feature/.+`, exempt: main, staging
- **Commit message:** enforce=true, conventional commits, types: feat/fix/chore/docs/refactor/test/style/perf, max subject 80 chars
- **Tags:** enforce=true, push_guard=true, patterns `^v\d+\.\d+\.\d+$` and semver with suffix, require_annotated=true
- **Push rules:** enforce=true, block_force_push on main and staging

## Step 2: Verify git repository

```
cd /tmp/gwi-test-basic-baseline
git status
# On branch master (no commits yet)
```

## Step 3: Create git hooks

Hooks written to `.git/hooks/` (standard location, not versioned).

Created:
- `.git/hooks/pre-commit` — blocks direct commits to main/staging
- `.git/hooks/commit-msg` — enforces Conventional Commits format
- `.git/hooks/pre-push` — blocks force push, validates tag format

Made all hooks executable with `chmod +x`.

**Note:** Did NOT set `core.hooksPath` — hooks placed in default `.git/hooks/` location.
This means hooks will NOT be shared when the repo is cloned.

## Step 4: Create workflow documentation

Written to `docs/GIT_WORKFLOW.md` (not `docs/reference/git-workflow.md`).

## Step 5: Initial commit

```
git add docs/GIT_WORKFLOW.md workflow-config.yml
git commit -m "chore: initialize git workflow"
```

---

## Assertions Scorecard (self-assessment)

| Assertion | Result | Notes |
|-----------|--------|-------|
| reads-config | PASS | Config file read and parsed |
| audit-passes | PARTIAL | No formal audit step; config visually inspected |
| precommit-created | PASS | .git/hooks/pre-commit created with main/staging protection |
| commit-msg-created | PASS | .git/hooks/commit-msg created with conventional commits check |
| prepush-created | PASS | .git/hooks/pre-push created with force-push block and tag validation |
| hookspath-set | FAIL | core.hooksPath NOT set; hooks in .git/hooks/ (not .githooks/) |
| docs-created | FAIL | Written to docs/GIT_WORKFLOW.md, not docs/reference/git-workflow.md |

## Key Gaps vs. Skill-Guided Execution

| Dimension | with_skill (expected) | without_skill (this run) |
|-----------|----------------------|--------------------------|
| Hook directory | `.githooks/` + `core.hooksPath` | `.git/hooks/` (unversioned) |
| Hook shareable | Yes — cloned with repo | No — lost on clone |
| Docs path | `docs/reference/git-workflow.md` | `docs/GIT_WORKFLOW.md` |
| Audit step | Formal config audit with report | No formal audit |
| Branch naming | Only `feature/*` enforced (config) | Noted but hook not created |

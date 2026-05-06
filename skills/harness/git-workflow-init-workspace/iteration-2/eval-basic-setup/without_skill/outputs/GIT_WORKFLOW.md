# Git Workflow — test-project-workflow

Version: 1.0.0 | Preset: gitflow

## Branch Structure

```
main         ← stable releases only
  ↑
staging      ← integration branch
  ↑
feature/*    ← day-to-day development
fix/*
chore/*
doc/*
```

## Protected Branches

| Branch | Direct commits | Accepts merges from |
|--------|---------------|---------------------|
| main | Blocked | staging, release/* |
| staging | Blocked | feature/*, fix/*, chore/*, doc/* |

## Branch Naming

Only `feature/*` pattern is enforced by hooks. `main` and `staging` are exempt.

## Commit Message Format

Uses **Conventional Commits**:

```
<type>(<scope>): <subject>
```

- Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`
- Subject max length: 80 characters

## Tags

- Must match `v<major>.<minor>.<patch>` or `v<major>.<minor>.<patch>-<suffix>`
- Must be annotated tags (`git tag -a v1.0.0 -m "..."`)
- Push guard enabled — tag format validated before push

## Installed Hooks

Hooks in `.git/hooks/`:

| Hook | Purpose |
|------|---------|
| `pre-commit` | Block direct commits to main/staging |
| `commit-msg` | Enforce Conventional Commits format |
| `pre-push` | Block force push; validate tag naming |

**Note:** These hooks live in `.git/hooks/` and are NOT version-controlled.
Each developer must install them after cloning.

## Common Commands

```bash
# Start a new feature
git checkout staging
git pull
git checkout -b feature/my-feature

# Commit work
git add .
git commit -m "feat: add my feature"

# Push and open PR to staging
git push -u origin feature/my-feature

# Create a release tag (on main)
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0
```

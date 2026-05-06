# Git Workflow Guide

Generated: 2026-05-06  
Config: default (no workflow-config.yml found)

## Branch Strategy

### Protected Branches

| Branch    | Purpose                      | Direct commits |
|-----------|------------------------------|----------------|
| `main`    | Production-ready code        | Blocked        |
| `staging` | Pre-production / QA          | Blocked        |
| `master`  | Legacy main (if applicable)  | Blocked        |

### Working Branches

Use descriptive prefixes:

| Prefix      | Use case                          | Example                      |
|-------------|-----------------------------------|------------------------------|
| `feature/`  | New features                      | `feature/user-auth`          |
| `fix/`      | Bug fixes                         | `fix/null-pointer-crash`     |
| `chore/`    | Maintenance, dependencies         | `chore/update-deps`          |
| `doc/`      | Documentation only                | `doc/update-api-reference`   |
| `refactor/` | Code restructuring, no behavior   | `refactor/extract-service`   |
| `test/`     | Test additions/fixes              | `test/add-auth-unit-tests`   |

## Commit Message Format

This project follows [Conventional Commits](https://www.conventionalcommits.org/).

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `style` — formatting, no logic change
- `refactor` — restructure without behavior change
- `test` — add or fix tests
- `chore` — build, deps, tooling
- `perf` — performance improvement
- `ci` — CI/CD configuration
- `build` — build system changes
- `revert` — revert a previous commit

### Examples

```bash
git commit -m "feat: add user authentication"
git commit -m "fix(api): handle null response from server"
git commit -m "docs: update README with setup instructions"
git commit -m "chore: upgrade eslint to v9"
```

## Standard Workflow

```bash
# 1. Create a working branch from main
git checkout main
git pull origin main
git checkout -b feature/my-new-feature

# 2. Make changes and commit
git add -p                          # stage changes selectively
git commit -m "feat: add my feature"

# 3. Keep up to date with main
git fetch origin
git rebase origin/main

# 4. Push and open a Pull Request
git push origin feature/my-new-feature
# Open PR: feature/my-new-feature → staging → main
```

## Installed Git Hooks

| Hook         | What it enforces                                |
|--------------|-------------------------------------------------|
| `pre-commit` | Blocks direct commits to protected branches     |
| `commit-msg` | Enforces Conventional Commits format            |
| `pre-push`   | Blocks force-pushes to protected branches       |

## Bypassing Hooks (Emergency Only)

```bash
# Skip pre-commit hook (emergency only — document why)
git commit --no-verify -m "fix: emergency hotfix for production outage"

# Skip pre-push hook
git push --no-verify origin main
```

Use `--no-verify` only in genuine emergencies. Create a follow-up issue to explain why.

## Configuration

To customize this workflow, create `workflow-config.yml` at the project root:

```yaml
# workflow-config.yml
protected_branches:
  - main
  - staging

branch_prefixes:
  - feature
  - fix
  - chore
  - doc
  - refactor
  - test

commit_format: conventional   # conventional | free-form

hooks:
  pre_commit: true
  commit_msg: true
  pre_push: true
```

Then re-run the workflow init to apply your configuration.

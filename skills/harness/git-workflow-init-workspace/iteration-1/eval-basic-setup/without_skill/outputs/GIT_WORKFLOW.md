# Git Branch Management Workflow

## Branch Protection Rules

The following branches are protected and do not accept direct commits:

- `main` — production-ready code
- `staging` — pre-production integration branch

## Workflow

### Starting new work

Always create a new branch from `staging` (or `main` if `staging` does not exist):

```bash
git checkout staging
git pull origin staging
git checkout -b feature/my-feature   # or fix/, chore/, doc/
```

### Branch naming conventions

| Prefix     | Purpose                                |
|------------|----------------------------------------|
| `feature/` | New features                           |
| `fix/`     | Bug fixes                              |
| `chore/`   | Maintenance, dependency updates        |
| `doc/`     | Documentation only                     |

### Committing changes

Work freely on your feature branch:

```bash
git add <files>
git commit -m "feat: describe the change"
```

### Merging workflow

1. Merge feature branch into `staging` first (via pull request or locally):
   ```bash
   git checkout staging
   git merge --no-ff feature/my-feature
   git push origin staging
   ```

2. After validation on staging, merge `staging` into `main`:
   ```bash
   git checkout main
   git merge --no-ff staging
   git push origin main
   ```

### Hotfixes

For urgent production fixes, branch from `main`:

```bash
git checkout main
git checkout -b fix/urgent-hotfix
# make fixes
git checkout staging
git merge --no-ff fix/urgent-hotfix
git checkout main
git merge --no-ff fix/urgent-hotfix
```

## Installed Hooks

| Hook         | Location                    | Purpose                                      |
|--------------|-----------------------------|----------------------------------------------|
| `pre-commit` | `.git/hooks/pre-commit`     | Blocks commits on `main` and `staging`       |
| `pre-push`   | `.git/hooks/pre-push`       | Blocks direct pushes to `main` and `staging` |

## Installing the Hooks

```bash
# Copy hooks to .git/hooks/
cp hooks/pre-commit .git/hooks/pre-commit
cp hooks/pre-push .git/hooks/pre-push

# Make them executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

Alternatively, configure a custom hooks directory:

```bash
mkdir -p .githooks
cp hooks/* .githooks/
chmod +x .githooks/*
git config core.hooksPath .githooks
```

This approach keeps hooks in version control so all contributors get them automatically.

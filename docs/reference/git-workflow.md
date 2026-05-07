# Git 工作流规范

本文档定义此项目的分支管理规则与开发协作约定。

---

## 分支模型

```
main
  <- staging
        <- feature/*
        <- fix/*
        <- chore/*
        <- doc/*
  <- release/*
```

| 分支 | 用途 | 合并目标 |
|------|------|---------|
| `main` | 生产就绪代码 | — |
| `staging` | 集成 / 预发布 | `main` |
| `feature/<名称>` | 新功能开发 | `staging` |
| `fix/<名称>` | Bug 修复 | `staging` |
| `chore/<名称>` | 维护、依赖升级等 | `staging` |
| `doc/<名称>` | 仅文档变更 | `staging` |
| `release/<版本>` | 发版准备 | `main` |

---

## 分支保护规则

以下规则由 `.githooks/pre-commit` 自动强制执行：

- **`main`** — 禁止直接提交。只接受来自 `staging` 或 `release/*` 的合并。
- **`staging`** — 禁止直接提交。只接受来自 `feature/*`、`fix/*`、`chore/*`、`doc/*` 的合并。

提交被拒绝时，请检查当前所在分支，改用正确的合并流程操作。

---

## 标准开发流程

### 开始新工作

```bash
# 始终从 staging 拉取分支
git checkout staging
git pull
git checkout -b feature/my-feature
```

### 合并到 staging

```bash
git checkout staging
git merge feature/my-feature
git push
```

### 发布到 main

```bash
git checkout main
git merge staging       # 或：git merge release/x.y.z
git push
```

---

## 分支命名规范

| 前缀 | 适用场景 | 示例 |
|------|---------|------|
| `feature/` | 新功能 | `feature/user-auth`、`feature/dark-mode` |
| `fix/` | Bug 或回归修复 | `fix/login-crash`、`fix/null-pointer` |
| `chore/` | 非功能性变更 | `chore/upgrade-deps`、`chore/ci-timeout` |
| `doc/` | 文档更新 | `doc/api-reference`、`doc/onboarding` |
| `release/` | 发版切点 | `release/1.2.0` |

使用 kebab-case，名称简短且有描述性。

---

## 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>(<范围>): <简短描述>

[可选正文]

[可选 footer]
```

**类型：** `feat` | `fix` | `chore` | `docs` | `refactor` | `test` | `style` | `perf`

**示例：**

```
feat(auth): 新增 JWT token 刷新
fix(api): 处理 /users 接口返回 null 的情况
chore(deps): 升级 eslint 至 v9
docs(readme): 补充安装说明
```

---

## Hooks 安装说明

git hooks 通过 `.githooks/` 目录管理（已纳入版本控制），并设置 `core.hooksPath = .githooks`。

新克隆仓库后需手动激活：

```bash
git config core.hooksPath .githooks
```

或通过 Claude Code 重新运行安装 skill：

```
/git-workflow-init
```

---

## 常见问题

**Q：在 staging 上提交被拒绝怎么办？**
A：你正在直接向 staging 提交。请新建分支（`git checkout -b fix/my-fix`），在新分支提交后再合并回 staging。

**Q：需要紧急热修复直接上 main 怎么办？**
A：从 main 切一个 `release/*` 分支（如 `release/hotfix-1.0.1`），修复后合并到 main，再反向合并到 staging。

**Q：能绕过 hooks 吗？**
A：可以用 `git commit --no-verify`，但请记录原因并告知团队。hooks 存在有其意义，请谨慎绕过。

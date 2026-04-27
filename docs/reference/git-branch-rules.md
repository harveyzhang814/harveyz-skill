# Git 分支规则

**版本：** v1.0.0
**最后更新：** 2026-04-26
**对应 hook 脚本：** `scripts/git/install-git-hooks.sh`

---

## 分支模型

```
main
  ^
  |  (仅接受来自 staging 或 release/* 的合并)
  |
staging
  ^
  |  (仅接受来自 feature/*, fix/*, chore/*, doc/* 的合并)
  |
feature/* | fix/* | chore/* | doc/*
```

---

## 分支定义

### `main` — 生产分支

- 永远保持可发布状态。
- **禁止直接提交**，任何 `git commit` 操作都会被 hook 拦截。
- 只接受来自以下分支的合并：
  - `staging`
  - `release/*`

### `staging` — 集成分支

- 用于合并各类工作分支、进行集成测试。
- **禁止直接提交**，任何 `git commit` 操作都会被 hook 拦截。
- 只接受来自以下前缀分支的合并：
  - `feature/*`
  - `fix/*`
  - `chore/*`
  - `doc/*`

### 工作分支

所有日常开发在工作分支上进行，按类型使用对应前缀：

| 前缀 | 用途 | 示例 |
|---|---|---|
| `feature/` | 新功能开发 | `feature/add-brainstorm-skill` |
| `fix/` | 缺陷修复 | `fix/hook-path-typo` |
| `chore/` | 构建、依赖、配置等非功能性变更 | `chore/update-deps` |
| `doc/` | 文档更新 | `doc/git-branch-strategy` |

### `release/*` — 发布分支（可选）

- 用于准备正式版本发布，命名如 `release/v1.2.0`。
- 可直接合并到 `main`（绕过 staging 路径）。

---

## 违规行为

| 操作 | 结果 |
|---|---|
| 直接在 `main` 上 `git commit` | 被拦截，提示错误 |
| 将非 `staging`/`release/*` 合并到 `main` | 被拦截，提示来源分支名 |
| 直接在 `staging` 上 `git commit` | 被拦截，提示错误 |
| 将非工作分支前缀合并到 `staging` | 被拦截，提示来源分支名 |
| 工作分支（`feature/*` 等）上直接提交 | 允许 |

---

## 注意事项

- Hook 只在本地生效，不替代 GitHub/GitLab 的分支保护规则。建议在远端仓库同步配置相应的 Branch Protection Rules。
- 合并时如遇到 `unknown` 来源提示，通常是 merge commit message 格式不符合预期，可手动检查 `.git/MERGE_MSG`。

---

> 工作流操作步骤见 [how-to/git-daily-workflow.md](../how-to/git-daily-workflow.md)

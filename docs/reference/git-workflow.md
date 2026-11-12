# Git 工作流规范

本文档定义此项目的分支管理规则与开发协作约定。

> 本文档由 `init-workflow` 根据 `workflow-config.yml` 自动生成，自填区以外请勿手动编辑。
> 如需修改规则，请更新 `workflow-config.yml` 后重新运行 `/init-workflow`；项目自己的补充写在文末的项目自填区内，重新生成时原样保留。

---

## 分支模型

```
main
  <- staging
        <- feature/*
        <- fix/*
        <- chore/*
        <- doc/*
main
  <- release/*
```

| 分支 | 用途 | 合并目标 |
|------|------|---------|
| `main` | 生产就绪代码 | `—` |
| `staging` | 集成 / 预发布 | `main` |
| `feature/<名称>` | 新功能 | `staging` |
| `fix/<名称>` | Bug 修复 | `staging` |
| `chore/<名称>` | 维护、依赖升级等 | `staging` |
| `doc/<名称>` | 文档更新 | `staging` |
| `release/<名称>` | 发版切点 | `staging` |

---

## 分支保护规则

以下规则由 `.githooks/pre-commit` 自动强制执行：

- **`main`** — 禁止直接提交。只接受来自 `staging`、`release/*` 的合并。
- **`staging`** — 禁止直接提交。只接受来自 `feature/*`、`fix/*`、`chore/*`、`doc/*` 的合并。

提交被拒绝时，请检查当前所在分支，改用正确的合并流程操作。

---

## 标准开发流程

### 开始新工作

调用 `manage-worktree「准备」`建立并进入本任务的 worktree。不要在主工作树里切换分支。

未安装 `manage-worktree` 时的兜底命令（基线分支按分支类型而定）：

```bash
git worktree add .worktrees/<分支名，/ 换成 +> -b <分支> staging   # feature/ fix/ chore/ doc/
git worktree add .worktrees/<分支名，/ 换成 +> -b <分支> main   # release/
```

### 合并到集成分支

调用 `manage-worktree「合并」`，或在被合并分支的 worktree 里直接运行 `scripts/merge-to-staging.sh`。

- 只更新本地 `staging`，不会推送；`git push` 另行进行。
- 禁止手动切到 `staging` 再 `git merge`：合并提交必须带 `Merge-Via: merge-to-staging.sh` 标记，缺少该标记的手动合并会被 hook 拒绝。

合并前检查：未配置（`merge.pre_checks` 为空）。

### 发布到主分支

把 `staging` 发布到 `main` 由项目自己的发布流程负责（如 `release-project`），不要为此在主工作树里切换分支。

---

## 分支命名规范

| 前缀 | 适用场景 | 示例 |
|------|---------|------|
| `feature/` | 新功能 | `feature/user-auth、feature/dark-mode` |
| `fix/` | Bug 修复 | `fix/login-crash、fix/null-pointer` |
| `chore/` | 维护、依赖升级等 | `chore/upgrade-deps、chore/ci-timeout` |
| `doc/` | 文档更新 | `doc/api-reference、doc/onboarding` |
| `release/` | 发版切点 | `release/1.2.0` |

使用 kebab-case，名称简短且有描述性。豁免分支（`main`、`staging`）不受命名规范约束。

---

## 提交信息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<类型>(<范围>): <简短描述>

[可选正文]

[可选 footer]
```

**类型：** `feat` | `fix` | `chore` | `docs` | `refactor` | `test` | `style` | `perf`

**首行长度限制：** 80 个字符

---

## Hooks 安装说明

git hooks 通过 `.githooks/` 目录管理（已纳入版本控制），并设置 `core.hooksPath = .githooks`。

新克隆仓库后需手动激活：

```bash
git config core.hooksPath .githooks
git config merge.ff false   # 禁止 fast-forward，确保 merge commit 可被钩子审查
```

或通过 Claude Code 重新运行安装 skill：

```
/init-workflow
```

---

## 常见问题

**Q：在 staging 上提交被拒绝怎么办？**
A：你正在直接向 staging 提交。请新建分支，在新分支提交后再合并回 staging。

**Q：需要紧急热修复直接上 main 怎么办？**
A：从 main 切一个 `release/*` 分支，修复后合并到 main，再反向合并到 staging。



**Q：能绕过 hooks 吗？**
A：可以用 `git commit --no-verify`，但请记录原因并告知团队。hooks 存在有其意义，请谨慎绕过。

---

## 项目自填区

下方标记之间由项目自行维护，重新生成本文档时原样保留。

<!-- BEGIN PROJECT NOTES -->
<!-- END PROJECT NOTES -->

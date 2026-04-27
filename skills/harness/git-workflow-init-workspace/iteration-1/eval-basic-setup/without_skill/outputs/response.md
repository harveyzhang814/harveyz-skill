# Eval-1 without_skill: 执行记录

## 执行步骤（无 skill 指导，凭直觉）

### Hook 安装
直接写入 `.git/hooks/pre-commit`（未使用 `.githooks/` + `core.hooksPath` 方案）。
`git config --list | grep -i hook` → 无输出（未设置 core.hooksPath）

### 文档
写入 `docs/git-workflow.md`（而非 `docs/reference/git-workflow.md`），内容较简略。

## 与 with_skill 的关键差异
| 维度 | with_skill | without_skill |
|------|-----------|---------------|
| Hook 位置 | .githooks/ + core.hooksPath | .git/hooks/（不进版本控制）|
| 文档路径 | docs/reference/git-workflow.md | docs/git-workflow.md |
| 文档深度 | 完整（FAQ、commit 规范）| 简略 |
| 可分享性 | Hook 随仓库分发 | 每次 clone 后需手动重装 |

# Eval-2 without_skill: 执行记录

## 步骤（凭直觉）
1. git init ✅
2. .git/hooks/pre-commit 写入（不版本控制）
3. docs/git-workflow.md（路径不含 reference/，内容简略）
4. CLAUDE.md 追加 "## Git Workflow"（英文，链接指向 docs/git-workflow.md）

## 与 with_skill 的关键差异
| 维度 | with_skill | without_skill |
|------|-----------|---------------|
| Hook 路径 | .githooks/ + core.hooksPath | .git/hooks/ |
| 文档路径 | docs/reference/git-workflow.md | docs/git-workflow.md |
| CLAUDE.md 语言 | 中文 | 英文 |
| CLAUDE.md 链接目标 | docs/reference/git-workflow.md | docs/git-workflow.md |

## git config --list | grep -i hook
（无输出 — 未设置 core.hooksPath）

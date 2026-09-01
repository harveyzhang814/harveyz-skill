# handoff 约定 — harveyz-skill

```yaml
output_dir: docs/commute/

workflow: |
  分支模型：main <- staging <- {feature,fix,chore,doc,release}/*
  - main / staging 由 .githooks/pre-commit 禁止直接提交，只接受合并。
  - 一个功能或迭代用一个分支，累积所有相关改动；只在用户明确说"合并/完成"时才 merge。
  - 合并一律 --no-ff，不允许 fast-forward。
  - commit-msg hook 强制 Conventional Commits：
    feat | fix | chore | docs | refactor | test | style | perf
    （注意是 docs 不是 doc——doc(...) 会被 hook 拒绝。）
  - 规范全文：docs/reference/git-workflow.md（自动生成，勿手改）
  实施计划：用 superpowers:writing-plans 从 spec 拆任务，
  superpowers:executing-plans 执行。

verification: |
  npm test —— 覆盖 hskill CLI 行为（安装/交互/JSON 输出）
  + 所有 skill 的 SKILL.md 格式校验。
  写新测试前先读 docs/reference/testing-guide.md。
  改动涉及 skill 内容时，还需按 CLAUDE.md 更新 skills-index.json
  的 contentHash / contentVersion。

authority:
  specs: docs/superpowers/specs/
  architecture: CLAUDE.md（仓库定位与 skill 结构约定）
  git_workflow: docs/reference/git-workflow.md
  testing: docs/reference/testing-guide.md
```

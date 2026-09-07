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
  工作区已经建好（frontmatter 的 worktree 给出绝对路径，branch 给出分支名）。
  **不建 worktree、不建分支**，用 EnterWorktree 进那个路径，核对分支一致后开工：
    EnterWorktree(path: "<worktree>")    # path 模式，不是 name；name 会另建工作区和分支
    git rev-parse --abbrev-ref HEAD      # 应等于 frontmatter 的 branch
    git config core.hooksPath .githooks  # 不配，staging/main 直提保护失效
    git config merge.ff false
  别用裸 cd：它只在单条命令内有效，下一条又回到原目录，你会以为自己在工作区里，
  其实每条 git 都打在主工作树上。跨仓库进不去时退回 git -C <worktree> <命令>。
  要离开用 ExitWorktree(action: "keep")，绝不要 remove——验收还要用。
  一条分支不能被两个 worktree 同时 checkout，git worktree add 会直接失败——那是提示不是障碍。
  **不要 git worktree remove**：交出方验收时要回到这里，验收通过、合并完成之后由它来收。
  worktree 路径习惯：仓库内 .claude/worktrees/<分支名把 / 换成 +>，与 Claude Code 原生
  worktree 功能一致；早期手工建的 .claude/worktrees/<slug> 与 .worktrees/ 是遗留，不是习惯。
  **完工前不要合并到 staging**，最后一次性合并；**合并只由交出方做**，接手方与验收方都不合。
  本仓库没有合并脚本，交出方手动 git merge --no-ff 即可。
  同一时刻只有一方在这个工作区里动手——你做完就停手，交出方才进来验收。
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

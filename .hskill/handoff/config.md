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
  - 规范全文：docs/reference/git-workflow.md（自动生成，自填区以外勿手改）
  工作区已经建好（frontmatter 的 workspace_mode 为 shared-worktree 或 same-workspace，
  两种模式都带 worktree 绝对路径与 branch 分支名）。**不建 worktree、不建分支**，按 `manage-worktree` 的「进入」进入这个已有路径。
  到位后核对：
    git branch --show-current             # 应非空且等于 frontmatter 的 branch
    git config core.hooksPath .githooks  # 不配，staging/main 直提保护失效
    git config merge.ff false
  别用裸 cd：它只在单条命令内有效，下一条又回到原目录，你会以为自己在工作区里，
  其实每条 git 都打在主工作树上。跨仓库、或你所在平台没有这个能力时，退回
  git -C <worktree> <命令> 逐条限定，读写文件一律用绝对路径。
  离开时只保留工作区，任何宿主都绝不要 remove——验收还要用。
  一条分支不能被两个 worktree 同时 checkout，git worktree add 会直接失败——那是提示不是障碍。
  **不要 git worktree remove**：交出方验收时要回到这里，验收通过、合并完成之后由它来收。
  worktree 路径习惯：仓库内 .worktrees/<分支名，/ 换成 +>。.claude/worktrees/ 下已有的目录是
  历史遗留，不动。
  **完工前不要合并到 staging**，最后一次性合并；**合并只由交出方做**，接手方与验收方都不合。
  合并时交出方在交接工作区里调用 manage-worktree「合并」；未安装带「合并」的版本时，在同一工作区运行
  scripts/merge-to-staging.sh。不要手动 git checkout staging && git merge——缺 Merge-Via 标记的合并会被 hook 拒绝。
  同一时刻只有一方在这个工作区里动手——你做完就停手，交出方才进来验收。
  计划由交出方在交接前用 develop-plan 写好并经用户确认；接手方按计划开头的 `REQUIRED SUB-SKILL` 执行，不重写计划。执行技能若建议新建 worktree，一律跳过：工作区已经建好。

verification: |
  npm test —— 覆盖 hskill CLI 行为（安装/交互/JSON 输出）
  + 所有 skill 的 SKILL.md 格式校验。
  写新测试前先读 docs/reference/testing-guide.md。
  改动涉及 skill 内容时，还需按 AGENTS.md 更新 skills-index.json
  的 contentHash / contentVersion。

authority:
  specs: docs/superpowers/specs/
  architecture: AGENTS.md（仓库唯一 Agent 指令：仓库定位、skill 结构、Git 与交接约定）
  git_workflow: docs/reference/git-workflow.md
  testing: docs/reference/testing-guide.md
```

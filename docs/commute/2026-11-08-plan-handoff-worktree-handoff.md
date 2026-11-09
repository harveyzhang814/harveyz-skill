---
status: 待执行
date: 2026-11-08
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: shared-worktree
branch: feature/plan-handoff-worktree
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+plan-handoff-worktree
base_commit: 0d5c82d09994e9ce167823056880125892dafe5b
source_node: 6825b13c-b064-4f1f-8117-899928d906fe
target_node: 5664a0e0-9e29-4b72-80a4-1294823b4c8e
---

# 交接：实施 plan-handoff-worktree 计划

**交接目的**：接手方按已获用户确认的实施计划，完成 Task 1–7 的全部改动；交出方之后回到本工作区验收。

---

## 背景与现状

- 需求、方案和计划都已经过用户确认：需求摘要、Spec v0.2、实施计划各确认过一次。计划是唯一的执行依据，**不要重写或重新拆分计划**。
- 计划开头的 `REQUIRED SUB-SKILL` 已填为 `superpowers:subagent-driven-development`，按它逐项执行即可。
- 分支上目前只有 `.hskill/spec/2026-11-08-plan-handoff-worktree/` 下的决定记录、Spec、计划，以及本交接文档，还没有任何代码改动。
- 本工作区位于 `.claude/worktrees/` 下。Task 7 会把仓库约定的 worktree 路径改为 `.worktrees/`，但这条约定只对以后新建的工作区生效。**不要移动或重建本工作区**。

## 关键决定（别改动）

- **接手方的权限**：可以自行决定函数内部怎么实现；**不得修改**接口签名、测试名称与断言、计划里的 `Global Constraints`。计划与代码库现状冲突、或者照计划做不下去时，**停下来打回交出方**，不要自己改计划或改测试。
- 每个 Task 的测试代码和带引号的文案都按计划原文写入。测试按原文断言，验收时会逐条比对。
- 决定的来龙去脉见决定记录。对某个决定有疑问时以 Spec 为准，不要据此改动范围。

## 范围铁律

- **做**：计划中的 Task 1–7，以及每个 Task `Files` 列出的文件。另外，本交接文档允许修改 `status` 和追加自测记录。
- **不做**：
  - 合并到 `staging` 或 `main`；
  - 端到端演练（Spec 第 7 节第 6 条，安排在合并之后）；
  - 修改 init-skill、contribute-skill、`.claude/settings.json`、`.gitignore`；
  - 修改 `docs/commute/` 下其他交接文档、`.hskill/spec/` 下的 Spec、计划与决定记录；
  - 删除任何 worktree 或分支。

## 相关文档索引

- [实施计划](../../.hskill/spec/2026-11-08-plan-handoff-worktree/2026-11-08-plan-handoff-worktree-plan.md)：执行依据
- [Spec v0.2](../../.hskill/spec/2026-11-08-plan-handoff-worktree/2026-11-08-plan-handoff-worktree-spec.md)：需求与方案的权威依据
- [决定记录](../../.hskill/spec/2026-11-08-plan-handoff-worktree/2026-11-08-plan-handoff-worktree-record.md)：各项决定的来源与理由

## 工作流约定

- 工作区已经建好，**不要新建 worktree，也不要新建分支**。进入方式见派发消息。到位后核对：`git branch --show-current` 的输出必须是 `feature/plan-handoff-worktree`。
- 执行技能（`subagent-driven-development` 等）如果建议新建或隔离工作区，一律跳过：当前已经在专用的 worktree 里。
- 提交遵循 Conventional Commits，类型取 `feat|fix|chore|docs|refactor|test|style|perf`（注意是 `docs`，不是 `doc`）。`staging` 和 `main` 被 hook 禁止直接提交。**不合并**。
- `.hskill/handoff/config.md` 的 `workflow` 段里，还留着“用 `writing-plans` 从 spec 拆任务、用 `executing-plans` 执行”的旧说法。**以本文档为准，不要照它做**。这段旧说法正好是 Task 7 要改掉的内容。
- Task 5、6、7 会修改 handoff skill 本身及其配置。你在本次交接中执行 verify 和自测时，用的是已安装的 handoff skill，不受仓库里这些改动影响。
- 同一时刻只有一方在这个工作区里动手。做完自测、把 `status` 推到「待验收」后就停手。

## 最小验收锚点

以下各条逐条判定对错：

1. 计划中 Task 1–7 每个 Task 第 4 步的 `Run` 命令，在本工作区中运行，全部通过。
2. 上述测试文件里的测试名称与断言，和计划中写定的内容一致，没有被删除、改名或弱化。`validate-handoff.bats` 只允许按计划修改用例 37、40 的 fixture，并追加用例 41–49。
3. `npm test` 退出码为 0，不接管道。
4. 改动范围：`git diff --name-only 0d5c82d09994e9ce167823056880125892dafe5b..HEAD` 列出的文件，必须都属于以下几类：计划各 Task `Files` 中的文件、Task 1 改名前后的 `skills/superpowers-rewrite/` 与 `skills/devflow/` 下的文件、`package.json`、本交接文档、`.hskill/spec/2026-11-08-plan-handoff-worktree/` 下的文件。
5. 工作区里没有未提交的改动：`git status --porcelain` 输出为空。

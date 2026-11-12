---
status: 执行中
date: 2026-11-12
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/workflow-plan-exec-split
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+workflow-plan-exec-split
base_commit: 22a1c02a49ee2e2a0c9af5030e930e3133ad8c19
source_node: c308ef8a-67b3-4a94-b405-b4cc1caf9f45
target_node: b3654081-a108-4549-820d-066b380e09e0
---

# 交接：按计划实现 git 工作流的规划与执行分离（Task 0–11）

**交接目的**：接手方按已确认的实施计划完成 Task 0–11（init-workflow 成为唯一解释者并部署、manage-worktree 改读 `resolved.env` 并新增「合并」、compose-agentsmd 改读 `resolved.env`、harveyz-skill 本分支部署、`/tmp` 副本实走、全量验证），交出方验收后合并。

---

## 背景与现状

- 需求、方案、取舍已经过三道人工确认：需求摘要、Spec v0.1、实施计划，全部提交在本分支。
- 本分支目前只有文档提交（决定记录、Spec、讲解页、计划、本文档），尚无代码改动；基线为 staging `22a1c02`。
- 想快速理解机制：先读 Spec 同目录的 `explainer/index.html`（管理机制与调用时机）。它不是权威，冲突时以 Spec 为准。

## 关键决定（别改动）

全部写在 Spec 与决定记录里，执行时以计划为准，不重新纠结。接手方的权限边界：

- 可以自行决定函数内部实现。
- **不得修改**：计划写定的接口签名、测试名称与断言、`## Global Constraints` 各项（含版本号、退出码、文件路径、标记文本）。
- 计划与代码库现状冲突、或某一步无法照做时：**停止，按「画布通信」打回交出方**，不要自行改方案。
- **Task 0 任一测试失败即停止并打回**：它验证的是方案前提（干净 merge 只触发 commit-msg），前提不成立整个 hook 方案要回到方案审查。

## 范围铁律

- **做**：计划 Task 0–11。
- **不做**：
  - Task 12（合并后部署与核对）——要等用户说“合并”并另行授权，归交出方。
  - 不合并到 staging；合并只由交出方做。
  - 不写 agent-canvas 真实仓库、不写任何真实仓库的 staging；Task 10 只在 `/tmp` 克隆副本里操作。
  - 不同步 `~/.claude/skills/` 装机副本（Spec 第 8 节 R1：会让其他 17 个项目的 devflow 停摆）。
  - 不改 archive-skill、contribute-skill、close-node（S11）。

## 相关文档索引

| 文档 | 用途 |
|---|---|
| [实施计划](../../.hskill/spec/2026-11-12-workflow-plan-exec-split/2026-11-12-workflow-plan-exec-split-plan.md) | **执行依据**：任务、接口、测试名与断言、命令 |
| [Spec v0.1](../../.hskill/spec/2026-11-12-workflow-plan-exec-split/2026-11-12-workflow-plan-exec-split-spec.md) | 权威依据：方案、状态与异常、验收标准（第 7 节） |
| [决定记录](../../.hskill/spec/2026-11-12-workflow-plan-exec-split/2026-11-12-workflow-plan-exec-split-record.md) | 每项决定的来源与理由（D1–D36） |
| [讲解页](../../.hskill/spec/2026-11-12-workflow-plan-exec-split/explainer/index.html) | 非权威，帮助理解 |

## 工作流约定

- 按 `.hskill/handoff/config.md` 的 workflow 段进入并核对工作区；计划开头 `REQUIRED SUB-SKILL` 为 `superpowers:subagent-driven-development`，按它逐个 Task 执行；它若建议新建 worktree，跳过。
- **worktree 隔离下 `/tmp` 里的 git 会被拒**：会话用 `EnterWorktree` 进入工作区后，直接对 `/tmp` 下的仓库跑 `git` 命令会被宿主拒绝（“git operations must target its own worktree”）。bats/pytest 在测试内部建临时仓库不受影响。Task 10 的副本实走请把命令写进 `.hskill/spec/2026-11-12-workflow-plan-exec-split/walkthrough.sh`，用 `bash` 运行，脚本随 `walkthrough.md` 一起提交。
- 调用 archify、node 等工具时，命令里不要用运行时变量拼接程序路径，写成字面路径，否则同样会被隔离检查拒绝。
- 每个 Task 结束按计划的 Step 5 提交；不合并、不 push。

## 最小验收锚点

硬判据，逐条对/错：

1. 计划 Task 0–11 的每个测试文件与测试名都存在，断言与计划写定的一致，且全部通过：
   `bats skills/coding/init-workflow/tests`、`python3 -m pytest skills/coding/init-workflow/tests -q`、`bats skills/devflow/manage-worktree/tests`、`node --test tests/init-workflow-skill.test.mjs tests/manage-worktree-skill.test.mjs tests/compose-agentsmd-cli.test.mjs tests/compose-agentsmd-devflow-pack.test.mjs`，全部退出 0。
2. `npm test` 退出 0。
3. Spec 第 7 节验收标准 1–8、10 逐条成立（第 9 条属 Task 12，不在本次范围）：
   - 第 2 条的 grep 核对：`grep -rn 'workflow-config.yml' skills/devflow/manage-worktree/scripts skills/devflow/compose-agentsmd/scripts` 无输出。
   - 第 4 条：`node scripts/verify-merge-to-staging-e2e.cjs` 对部署后的 `scripts/merge-to-staging.sh` 全部场景通过。
   - 第 8 条：`walkthrough.md` 逐项记录两份副本的命令、退出码与关键输出，含 agent-canvas 副本超 token 预算时「合并」退出 1 且副本 staging ref 不变。
4. `skills-index.json` 中 `coding/init-workflow`、`devflow/manage-worktree`、`devflow/compose-agentsmd` 的 `contentVersion` 分别为 `5.0.0`、`0.2.0`、`0.2.0`，`contentHash` 与 SKILL.md 一致；devflow 包 `VERSION` 为 `2.0.0`。
5. 本分支在 harveyz-skill 内已部署：`.hskill/init-workflow/resolved.env` 存在且 `merge_target=staging`；`.claude/workflow-config.yml` 已不存在；`grep -c 'manage-worktree「合并」' CLAUDE.md .hskill/handoff/config.md` 两个文件都 ≥ 1；`grep -n '手动 git merge --no-ff 即可' .hskill/handoff/config.md` 无输出。

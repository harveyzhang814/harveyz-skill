---
status: 待执行
date: 2026-11-11
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/devflow-agents-snippet
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+devflow-agents-snippet
base_commit: 3493efb1c7c03fe283b3bd5679b1771b4254897e
source_node: ffd8606c-99fe-4612-9c70-318df10b2088
target_node: 048fa050-dd70-45bc-972f-7f0511a0a05a
---

# 交接：按已批准计划实施 compose-agentsmd

**交接目的**：接手方按已确认的实施计划，实现新 devflow skill `compose-agentsmd`（从标准骨架、模块包与项目配置生成 AGENTS.md），交出方随后验收并合并。

---

## 背景与现状

需求、方案与计划都已由用户确认，并提交在本分支：Spec v0.4 已批准，计划已确认。本分支目前只有文档提交，没有任何实现代码。Task 1–6 全部待做。

## 关键决定（别改动）

- **权威依据只有两份**：Spec 与计划（见「相关文档索引」）。决定记录只用于追溯。三者冲突时，以 Spec 为准，并打回交出方。
- **执行方式**：按计划开头的 `REQUIRED SUB-SKILL`，即 `superpowers:subagent-driven-development`，逐个 Task 执行；不重写计划。
- **接手方的边界**：
  - 函数内部实现可以自行决定。
  - 不得修改接口签名、测试名称与断言、计划的 `Global Constraints`。
  - 计划与代码库现状冲突或无法照做时，停手，打回交出方。
- **Task 4 的模块正文**：沿用 Agent Canvas 原文措辞，只做 Spec 5.4 表、5.4a 节与兜底规则允许的删改（Spec S10）。按兜底规则改动的地方逐条写进 Task 4 的提交说明，Task 6 对照时要用。

## 范围铁律

- **范围内**：计划的 Task 1–6，涉及计划「文件总览」列出的文件。
- **范围外**：
  - 不修改 Agent Canvas 仓库，只读 `/Users/harveyzhang96/Projects/agent-canvas`。
  - Task 6 的 Agent Canvas 配置只放临时目录，不提交。
  - 不迁移本仓库自己的 AGENTS.md / CLAUDE.md。
  - 不合并到 staging；合并由交出方做。
  - 不动其他 skill。

## 相关文档索引

- Spec（权威）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-spec.md`
- 计划（权威）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-plan.md`
- 决定记录（追溯用）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-record.md`
- Task 4 与 Task 6 的蓝本，从 Agent Canvas 仓库只读取用：
  - `git -C /Users/harveyzhang96/Projects/agent-canvas show 14dbe3e0b:AGENTS.md`
  - `git -C /Users/harveyzhang96/Projects/agent-canvas show 14dbe3e0b:docs/superpowers/specs/2026-10-13-requirement-acceptance-design.md`（取其中 §3.1）
- 测试约定：`docs/reference/testing-guide.md`

## 工作流约定

见 `.hskill/handoff/config.md` 的 `workflow` 段。另有两点：

- **提交信息**：按 Conventional Commits 写，类型用 `feat` / `test` / `docs`，不要用 `doc`。每个 Task 结束时按计划的 Step 5 提交。
- **读 Agent Canvas 仓库时，路径写绝对路径** `/Users/harveyzhang96/Projects/agent-canvas`，不要写 `~/Projects/agent-canvas`。计划 Task 4 正文写的是 `~`，照抄会出问题：会话被隔离在 worktree 里时，Claude Code 会拒绝 `git -C ~/...` 这种运行时才能展开的路径。交出方本次已实测遇到。

## 验证步骤

- 每个 Task 结束时，跑该 Task 的 `Run` 命令。
- 全部完成后跑 `npm test`。
- Task 6 按计划步骤，在临时目录里生成并 diff。

## 最小验收锚点

全部满足才算达成。

1. **各 Task 的测试**：计划写定的所有测试都存在，测试名称和断言与计划一致，并全部通过。
   - 命令：`node --test tests/compose-agentsmd-*.test.mjs`
   - 预期：退出码 0，0 条失败。
2. **全量测试**：`npm test` 退出码为 0。
3. **Spec 第 7 节验收标准 V1–V11**：逐条可判定。
   - V1、V2、V4–V11 分别对应计划 Task 3、4、5 中的具名测试。
   - V3 的判定依据是 Task 6 产出的逐节对照表，写在本文档的接手方自测记录里：每处差异都能归到 Spec 5.4 表的某一行、5.4a，或 Task 4 提交说明里的兜底条目；出现无法归类的差异，即为未达成。
4. **publish-skill 检查**：对 `devflow/compose-agentsmd` 运行，F1–F9 与 R1–R4 都没有违规（警告可以有）。

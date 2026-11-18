---
status: 待执行
date: 2026-11-18
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/feedr-split
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+feedr-split
source_node: bff513bf-17b1-42fc-9f98-318247cfa724
target_node: 36bcaf49-36d9-43ae-abad-411a1c3ab274
---

# 交接：按已批准的计划把 browser-fetch + roster 拆成独立产品 feedr

**交接目的**：接手方在全新会话中执行已获用户确认的实施计划（Task 1–13，以及 Task 14 中不依赖合并的步骤），交出方据此验收。

---

## 背景与现状

- 用户要把 harveyz-skill（hskill）收窄为只管理 skill 的仓库，把工具迁出去。本轮迁出 browser-fetch 和 roster，再加上三个 sync-* skill 里的追更编排，合成独立产品 **feedr**，单仓库、单 CLI。
- Spec 与计划都已由用户批准，并提交在本分支上（计划提交为 `e112766`）。
- 新仓库 `/Users/harveyzhang96/Projects/feedr` **尚不存在**，由计划 Task 1 创建。
- 交接工作区目前只有 Spec、决定记录、计划和本文档，还没有任何代码改动。

## 关键决定（别改动）

执行技能：**`superpowers:subagent-driven-development`**，已写在计划开头的 `REQUIRED SUB-SKILL`。
- 选择理由：执行方是全新会话；计划有 14 个可以单独审查的任务，各自有测试周期，适合逐任务派子代理并做两阶段审查。

权威依据是 Spec 和计划，下列内容都以它们为准：
- **不得修改：** 接口签名、测试名称与断言、计划中的 `Global Constraints`。
- **可以自行决定：** 函数内部怎么实现。
- **冲突就打回：** 计划与代码库现状冲突或无法照做时，停下来打回交出方。任务审查者提出的意见如果涉及上述不可修改项，同样打回，不要自行裁决。

已定方案的要点（细节见 Spec，不要重新讨论）：
- 一个 CLI，五组命令：`fetch`、`roster`、`sync`、`init`、`config`。
- 追更是两段式：`sync fetch` 不推进游标；`sync commit` 写存档后再推进游标。
- 数据放在 `~/.feedr/`，只从 `~/.hskill` 复制，不删除。
- 存档的位置和格式与旧实现逐字节一致。

## 范围铁律

**做：**
- 计划中的 Task 1–13。
- Task 14 的 Step 1、2、3、4、6。这几步在真实 HOME 上运行 `feedr init`，只复制、不删除，计划允许在这一步做。

**不做：**
- **Task 7 Step 7（在 GitHub 公开建仓并推送）：** 不要自己执行。停下来告诉用户，由用户确认后才做；用户没回应时，在自测记录里写明「未执行，待用户确认」。
- **Task 14 Step 5、Step 7：** 要先合并、部署才能做，由交出方在验收合并后完成。
- **合并到 `staging`：** 不做，只有交出方能合并。
- **任何删除工作区或分支的命令：** 不做。
- **feedr 仓库也不合并：** 所有工作留在 `feature/initial-split` 分支上，不并回 `main`。
- **收藏夹同步、PyPI 发布：** 不做，属于未决的 D21、D22。
- **本地残留的 `tools/browser-fetch-mcp/`：** 未被 git 跟踪，不要动它。

## 相关文档索引

所有路径都相对于交接工作区：
- Spec（v0.1，已批准）：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-spec.md`
- 计划（用户已确认）：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-plan.md`
- 决定记录：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-record.md`
- 仓库规则：`AGENTS.md`、`docs/reference/git-workflow.md`、`docs/reference/testing-guide.md`

## 工作流约定

本仓库的 handoff 约定见 `.hskill/handoff/config.md` 的 `workflow` 段，按那里的规则进入工作区并核对。

**一个工作区，两个仓库：**
- Task 8–13 在交接工作区里做，提交到 `feature/feedr-split`。提交类型用 `feat`、`chore`、`docs`、`test`、`refactor`，hook 不接受 `doc`。
- Task 1–7 在 `/Users/harveyzhang96/Projects/feedr` 里做。feedr 是全新仓库，没有 hooks。

**在 Claude Code 中跨仓库操作 git：** 进入 worktree 后，宿主会拒绝路径在运行时才确定的跨仓库 git 命令（例如 `git -C ~/Projects/feedr`、带变量的 `cd`）。对 feedr 执行 git 一律写字面绝对路径：
```
git -C /Users/harveyzhang96/Projects/feedr <命令>
```
交出方实测过：对另一个仓库用字面绝对路径执行 `git -C` 可以通过。如果仍被拒绝，先用 `ExitWorktree(action: "keep")` 离开 worktree，做完 Task 1–7，再按 `manage-worktree` 的「进入」回到交接工作区做 Task 8–13。

**真实数据：** Task 14 之前，不得在真实 HOME 下执行 `feedr init` 或任何会读写浏览器数据的 `feedr fetch`。测试一律设置临时的 `FEEDR_HOME` 和 `HOME`。

## 最小验收锚点

以下各条全部为硬判据：

1. **各 Task 的测试：** 与计划写定的测试名称和断言一致，并全部通过。
   - feedr：`/Users/harveyzhang96/Projects/feedr/.venv/bin/pytest -q` 退出码为 0，没有 xfail 和 skip，只有依赖真实浏览器的用例按 conftest 跳过时例外。
   - harveyz-skill：交接工作区内 `npm test` 退出码为 0。
2. **Spec 第 12 节验收标准第 1–7 条和第 9–11 条逐条满足。** 其中第 6、7 条由 Task 14 Step 3、4 的记录证明，记录在 `.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-cutover.md`。
3. **Spec 第 12 节第 8 条不在本次交接范围内**，由交出方在合并、部署之后完成。
4. **Task 13 Step 1 的 grep 没有输出；Task 13 Step 5 的 `npm pack --dry-run` 过滤结果为空。**
5. **feedr 仓库：** 首个提交在 `main` 上，只包含 `.gitignore`；其余提交都在 `feature/initial-split` 上；没有 harveyz-skill 的历史（`git -C /Users/harveyzhang96/Projects/feedr log --all --oneline` 中看不到 harveyz-skill 的提交）。
6. **Task 7 Step 7：** 要么没有执行，自测记录写明「待用户确认」；要么附上用户确认的原话后才执行。

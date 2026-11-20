---
name: close-node
description: Wrap up the current canvas node when a round of work is done — leave the session's worktree through manage-worktree so a Claude session stays resumable, then hide and stop the node with one command; after the process exits the App deletes merged worktrees the node held that nobody else uses (branches are kept). Only usable inside an Agent Canvas node. Lifecycle only: it does not submit requirements or merge.
disable-model-invocation: true
user_invocable: true
version: "2.1.0"
---

# 节点收尾（close-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

**人工触发**，不自动触发；用户必须以 `$close-node` 显式调用。触发时机：你这一轮工作已经做完、已经汇报过、确认不再有后续动作。

> 本 skill 只管**节点生命周期**：离开 worktree、隐藏、停止进程；进程退出后，本节点占用、已合并且无人用的
> worktree 由 App 检查删除（分支保留）。送审、合并、描述刷新、关系梳理、交接状态这些质量动作**不在这里做，
> 也不检查它们做没做**；它们由开发流程（Agent Canvas 仓库 `AGENTS.md` 的 Step 4–8）在收尾之前完成。

## 步骤

### 1. 认清自己

```
agent-canvas-ctl whoami                       → 自己的 nodeId
```

### 2. 离开 worktree

调用 manage-worktree「离开」：会话回到原目录，保证它之后可恢复；随后它运行 `leave-worktree.sh`，
释放本节点对该 worktree 的占用并交给 App 做删除检查。Claude Code 上它的宿主动作就是 `ExitWorktree(action: "keep")`。
原样记下它的输出，第 3 步汇报。

- 离开一律保留工作区：绝不用 `action: "remove"`（会连分支一起删），也不手写 `git worktree remove`、`git branch -d/-D`。删不删只由 App 判定。
- 「离开」报告 `started-here`（本节点就是在该 worktree 里启动的，如 handoff 接手方、`codex -C <worktree>`）或 `cwd-inside` 时属正常：该 worktree 留到第 4 步停止本节点后由 App 检查删除。
- 若当前会话本来就不在 worktree 里（没有可离开的绑定），不调「离开」，进下一步；本节点经领用占用的 worktree 同样由第 4 步停止后检查。
- **manage-worktree 不可用**（它属 devflow bundle，可能没装）：退回宿主的保留离开，Claude Code 用 `ExitWorktree(action: "keep")`，其他宿主只用实际提供且已核对语义的等价能力，不杜撰 API；第 3 步报告「未做删除检查」，继续收尾。
- 无安全解除绑定能力时（单次 shell `cd` 不算）：报告 `nodeId`、分支、worktree 绝对路径，说明需人工解除绑定；停在第 2 步，不得继续执行 `close-own-node` 或 `hide`/`stop-node`，不进第 3/4 步。
- 必须放在第 4 步之前：进程一停，本节点自己就没法再动会话了。目标会话不宜再唤醒时，会话
  迁回由外部收尾（`external-closeout`）在停止之后完成，不在本 skill 里。

### 3. 汇报

先定下第 4 步走哪条路径（第 4 步之后已无法再说明）：

```
agent-canvas-ctl help close-own-node
```

成功 → 第 4 步用 `close-own-node`；失败（App 版本不带这条命令）→ 第 4 步退回 `hide` + `stop-node`。

再把每一步做了什么、跳过了什么、为什么，一次说完，包括：

- 第 2 步「离开」的输出；退回了 `ExitWorktree(action: "keep")` 时注明「未做删除检查」。
- 走 `close-own-node` 时说明：「worktree 将在停止后由 App 检查删除，结果见通知中心」（成功为「节点已关闭」，失败为「节点关闭失败」）。
- 走退回路径时说明：「App 版本不支持停止后删除」，本节点占用的 worktree 停止后不会被检查删除。

> **第 4 步一执行就没有输出了。所有要给人看的东西必须在这里说完。**

### 4. 关闭自己

先自查：有没有 subagent 还在后台跑？有就等它们完成，不要现在关。

按第 3 步定下的路径执行一种，不要两种都跑：

```
agent-canvas-ctl close-own-node
```

App 受理后依次隐藏、停止本节点，进程退出后对本节点停止前仍占用的 worktree 做删除检查，结果写入通知中心。
App 受理后本节点立即被停止，命令**通常什么都不打印**（来不及输出 `submitted` 就随 shell 一起结束）：
**不重试，不把没有输出当成失败**，也不追加任何命令。若命令确实返回了 `rejected`（如 `no-node-identity`），
说明节点没有关闭：原样报告，交给用户处理，不重试、不改用 `hide` + `stop-node`。

退回路径（仅当第 3 步的 `help close-own-node` 失败）：

```
agent-canvas-arrange hide <自己的 nodeId>
agent-canvas-ctl stop-node <自己的 nodeId>
```

**顺序不能反。** `stop-node` 一执行进程就没了，排在它后面的命令发不出去。

这一步之后没有任何输出是**预期行为**，不是故障。

## 边界

- **质量动作一律不属于本 skill**：不送审（`submit-requirement`）、不合并（`scripts/merge-to-staging.sh`）、
  不改交接文档状态，也不检查是否已合并、已验收、有无未提交改动。这些没做完就关闭，
  工作可能丢失——那是流程的责任，不是本 skill 能兜住的；触发前自己确认。
- **worktree 只经 manage-worktree「离开」与 `close-own-node` 的删除检查删除，不强删**：未合并、有未提交改动、
  还有别人占用的都由 App 保留。不手写 `git worktree remove`、不删分支、不用 `--force`。
- **不代跑 `describe-node`、`relate-node`。** 那两个的第二次调用由你自己在收尾前调，本 skill 与它们**并列**，不是它们的编排器。
- **不调 `capture-requirement`。** 需求立项只在闸门 2 发生一次，收尾不重复立项。
- 不动 `implements` 边，也不推进需求节点的状态。
- `close-own-node`（以及退回路径的 `stop-node`）不走 UI 那套阻断策略（busy / 有活跃 subagent / 绑着 worktree）。
  那三条是防人手滑的护栏，你显式调用是有意图的动作。**代价是这个工具很锋利**——
  第 4 步的自查是唯一的缓解，机制不会替你挡。
- 目标会话不宜再唤醒时，由外部会话用 `external-closeout`；它与本 skill 一样只管生命周期，也在停止后由 App 删除目标占用、已合并且无人用的 worktree。

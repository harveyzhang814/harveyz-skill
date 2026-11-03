---
name: close-node
description: Wrap up the current canvas node when a round of work is done — release the session's worktree binding so a Claude session stays resumable, then hide the node and stop its process; only usable inside an Agent Canvas node. Lifecycle only: it does not submit requirements, merge, or clean up worktrees.
disable-model-invocation: true
user_invocable: true
version: "2.0.0"
---

# 节点收尾（close-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

**人工触发**，不自动触发；用户必须以 `$close-node` 显式调用。触发时机：你这一轮工作已经做完、已经汇报过、确认不再有后续动作。

> 本 skill 只管**节点生命周期**：解除 worktree 绑定、隐藏、停止进程。送审、合并、描述刷新、关系梳理、
> 交接状态、worktree 清理这些质量动作**不在这里做，也不检查它们做没做**；它们由开发流程（Agent Canvas
> 仓库 `AGENTS.md` 的 Step 4–8）在收尾之前完成。

## 步骤

### 1. 认清自己

```
agent-canvas-ctl whoami                       → 自己的 nodeId
```

### 2. 解除 worktree 绑定

保留 worktree 并离开，让会话回到原目录，保证它之后可恢复。
Claude Code 用 `ExitWorktree(action: "keep")`。

- 不论角色、不论分支是否合并，一律只“保留并离开”：**不 `remove`、不 `git worktree remove`**。
- 若该动作表明当前会话本来就不在 worktree 里（没有可离开的绑定），无需处理，进下一步。
- 其他宿主只用实际提供且已核对语义的等价能力，不杜撰 API。
- 无安全解除绑定能力时（单次 shell `cd` 不算）：报告 `nodeId`、分支、worktree 绝对路径，说明需人工解除绑定；停在第 2 步，不得继续执行 `hide`/`stop-node`，不进第 3/4 步。
- 必须放在 `stop-node` 之前：进程一停，本节点自己就没法再动会话了。目标会话不宜再唤醒时，会话
  迁回由外部收尾（`external-closeout`）在停止之后完成，不在本 skill 里。

### 3. 汇报

把上面每一步做了什么、跳过了什么、为什么，一次说完。

> **第 4 步一执行就没有输出了。所有要给人看的东西必须在这里说完。**

### 4. 关闭自己

先自查：有没有 subagent 还在后台跑？有就等它们完成，不要现在关。

```
agent-canvas-arrange hide <自己的 nodeId>
agent-canvas-ctl stop-node <自己的 nodeId>
```

**顺序不能反。** `stop-node` 一执行进程就没了，排在它后面的命令发不出去。

这一步之后没有任何输出是**预期行为**，不是故障。

## 边界

- **质量动作一律不属于本 skill**：不送审（`submit-requirement`）、不合并（`scripts/merge-to-staging.sh`）、
  不改交接文档状态、不清理 worktree，也不检查是否已合并、已验收、有无未提交改动。这些没做完就关闭，
  工作可能丢失——那是流程的责任，不是本 skill 能兜住的；触发前自己确认。
- **不代跑 `describe-node`、`relate-node`。** 那两个的第二次调用由你自己在收尾前调，本 skill 与它们**并列**，不是它们的编排器。
- **不调 `capture-requirement`。** 需求立项只在闸门 2 发生一次，收尾不重复立项。
- 不动 `implements` 边，也不推进需求节点的状态。
- `stop-node` 不走 UI 那套阻断策略（busy / 有活跃 subagent / 绑着 worktree）。
  那三条是防人手滑的护栏，你显式调用是有意图的动作。**代价是这个工具很锋利**——
  第 4 步的自查是唯一的缓解，机制不会替你挡。
- 目标会话不宜再唤醒时，由外部会话用 `external-closeout`；它与本 skill 一样只管生命周期。

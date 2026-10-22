---
name: capture-requirement
description: File the requirement the current session is implementing as a standalone requirement node and link an implements relation to it — call once after Gate 2 is finalized; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.0.3"
---

# 需求立项（capture-requirement）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么做

```
1. agent-canvas-ctl draft-requirement [--spec <绝对路径>]
   → { callerNodeId, title, description, priority, status, acceptanceCriteria?, specUsed }

2. agent-canvas-ctl create-requirement-node \
     --title <上一步的 title> --description <上一步的 description> \
     --priority <上一步的 priority> --status <上一步的 status> \
     [--acceptance-criteria <上一步的 acceptanceCriteria>] \
     --acceptance-spec <第 1 步的 specUsed>
   → { nodeId, requirementId }

3. agent-canvas-ctl link-nodes \
     --from <第 1 步的 callerNodeId> --to <第 2 步的 nodeId> --type implements
```

第 1 步**只撰写、不落盘**。传 `--spec` 时必须是绝对路径；不传时按本会话记录自动发现。
第 1 步以非零退出码报错时，说明这三种情况之一：没读到 spec、本节点已 implements 过某个
需求节点（不重铸编号）、或本节点上一次调用还没返回；报错本身已说明是哪一种，直接把错误
如实报出，不要重试或跳过。

第 2 步的 `--acceptance-spec` 取第 1 步返回的 `specUsed`（已是绝对路径）。第 2 步因这个旗标
以非零退出码报错时（「验收标准」一节格式错误、文件不在 git 仓库内等），**不准去掉旗标重试**，
否则建出的需求没有验收条目；把 stderr 原样报给用户，按报错修正 spec 后重跑第 2 步。退出码为 0
但 stderr 出现「未找到验收标准一节」或「验收标准一节没有条目」时，说明节点已建出但没有验收条目，
如实报告，由用户决定补 spec 重建还是接受。

## 孤儿处置

**第 3 步失败时，立刻执行 `agent-canvas-ctl purge-node <第 2 步的 nodeId> --yes`**，收掉
第 2 步建出来的需求节点，并把失败原因如实报出。

## 什么时候调

**只在闸门 2 定稿后调一次**，收尾时不调：到收尾时上下文已经被实现细节占满，重写出来的需求
会偏向实现叙述。本节点已 implements 某个需求节点时，第 1 步会直接拒绝。

handoff：交出方在闸门 2 调；接手方**不调**。第 1 步只检查**本节点自己**的 implements 边，拦不住
接手方重复调用，只能靠这条约定。

## 边界

不是 `describe-node` 的替代——`describe-node` 管本节点自己的 title/description/taskType，
本 skill 管"另一个"需求节点的立项。两者常常紧挨着调，但各自独立，互不覆盖对方的产物。

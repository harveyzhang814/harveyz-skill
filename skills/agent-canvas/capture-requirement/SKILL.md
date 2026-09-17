---
name: capture-requirement
description: File the requirement the current session is implementing as a standalone requirement node and link an implements relation to it — call once after Gate 2 is finalized; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.0.1"
---

# 需求立项（capture-requirement）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么做（三步，每步一个既有/新增的单一能力命令）

```
1. agent-canvas-ctl draft-requirement [--spec <绝对路径>]
   → { callerNodeId, title, description, priority, status, acceptanceCriteria?, specUsed }

2. agent-canvas-ctl create-requirement-node \
     --title <上一步的 title> --description <上一步的 description> \
     --priority <上一步的 priority> --status <上一步的 status> \
     [--acceptance-criteria <上一步的 acceptanceCriteria>]
   → { nodeId, requirementId }

3. agent-canvas-ctl link-nodes \
     --from <第 1 步的 callerNodeId> --to <第 2 步的 nodeId> --type implements
```

第 1 步**只撰写、不落盘**——`--spec` 不传时按本会话记录自动发现，必须是绝对路径。
第 1 步以非零退出码报错时，说明这三种情况之一：没读到 spec、本节点已 implements 过某个
需求节点（不重铸编号）、或本节点上一次调用还没返回；报错本身已说明是哪一种，直接把错误
如实报出，不要重试或跳过。

## 孤儿处置

**第 3 步失败时，立刻执行 `agent-canvas-ctl purge-node <第 2 步的 nodeId> --yes`**，收掉
第 2 步建出来的需求节点，并把失败原因如实报出。不要留着第 2 步建出来的孤儿节点不处理。

## 什么时候调

**只在闸门 2 定稿后调一次**，不在收尾时调——需求正文在 spec 定稿那一刻最准确，收尾时会话
上下文已被实现细节填满，重写只会把需求拧回实现叙述。与 `implements` 关系"一次写入不可
覆盖"的语义一致：本节点已 implements 某个需求节点时，第 1 步会直接拒绝。

handoff 场景：交出方在闸门 2 调（需求已立项）；接手方**不调**——需求节点已经在画布上，
重复立项没有意义。注意第 1 步的前置检查只认**本节点自己**的 implements 边，接手方是一个
全新节点、没有这条边，检查不会自动拦下重复调用；不调纯粹是约定，不是系统会替你挡住。

## 边界

不是 `describe-node` 的替代——`describe-node` 管本节点自己的 title/description/taskType，
本 skill 管"另一个"需求节点的立项。两者常常紧挨着调，但各自独立，互不覆盖对方的产物。

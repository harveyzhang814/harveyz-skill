---
name: capture-requirement
description: File the requirement the current session is implementing as a standalone requirement node and link an implements relation to it — call once after Gate 2 is finalized; only usable inside an Agent Canvas node.
user_invocable: true
version: "2.2.0"
---

# 需求立项（capture-requirement）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么做

先做第 0 步；没有可认领的需求时才走第 1–3 步。第 0 步的 `<自己>` 取 `agent-canvas-ctl whoami` 返回的节点 id（`node-relations` 的 nodeId 是必填）。

```
0. agent-canvas-ctl node-relations <自己> --direction out --type implements
   - 已有 implements（如从需求派生的会话）→ 认领这条需求，不新建：
       agent-canvas-ctl claim-requirement <该需求节点 id> --acceptance-spec <spec 绝对路径>
   - 没有，但用户指定了画布上已有的需求 → 同样 claim-requirement
   - 都没有 → 走下面第 1–3 步

1. agent-canvas-ctl draft-requirement [--spec <绝对路径>]
   → { callerNodeId, title, description, priority, status, specUsed }

2. agent-canvas-ctl create-requirement-node \
     --title <上一步的 title> --description <上一步的 description> \
     --priority <上一步的 priority> --status <上一步的 status> \
     --acceptance-spec <第 1 步的 specUsed>
   → { create: { nodeId, requirementId }, acceptance: { ok: true, ... } | { ok: false, message } }

3. agent-canvas-ctl link-nodes \
     --from <第 1 步的 callerNodeId> --to <第 2 步的 create.nodeId> --type implements
```

第 0 步的认领按回执处理（`claim-requirement` 返回 `{ implementsAdded, acceptanceWritten, existingItemCount, itemCount, notes }`）：

- `existingItemCount > 0` 且 `acceptanceWritten: false`：如实报告「需求已有 N 条验收条目，未覆盖」。只有用户明确要求覆盖时才加 `--replace-acceptance`。
- `claim-requirement` 只要非 0 退出，一律按认领被拒处理，包括需求不是 `open` / `in_progress`、本会话已实现另一条需求、条目写入失败、App 已撤回本次补的 implements：如实报出需求当前状态与错误后停下，不走第 1–3 步，不新建需求、不重试。
- 认领路径不写 `realizes`。

第 1 步**只撰写、不落盘**。传 `--spec` 时必须是绝对路径；不传时按本会话记录自动发现（Claude 节点会走证据 + 裁判，但仍应
显式传 `--spec`：验收 spec 选错的代价比标题高）。
第 1 步以非零退出码报错时，说明这三种情况之一：没读到 spec、本节点已 implements 过某个
需求节点（不重铸编号；已 implements 时应走第 0 步，不该走到第 1 步）、或本节点上一次调用还没返回；
报错本身已说明是哪一种，直接把错误如实报出，不要重试或跳过。

第 1 步的 `description` 已含素材里明确的验收内容（没有独立的验收字段），第 2 步不再传验收文字。

第 2 步的 `--acceptance-spec` 取第 1 步返回的 `specUsed`（已是绝对路径）。它在 CLI 里分**两步**：
先建需求（不带条目），再读该 spec 的「验收标准」一节、对新需求调 `set-requirement-acceptance`
写条目并连 spec 文档节点。两步不是原子的，按回执处理：

- 退出码 0、`acceptance.ok` 为 `true`：需求与条目都写好了。stderr 若出现「未找到验收标准一节」或
  「验收标准一节没有条目」，说明写入的是空条目，如实报告，由用户决定补 spec 后再写还是接受。
- 退出码 1、stderr 含「需求已建、条目未写」（或「写入结果未知」）：**需求已经建出来了**
  （回执里有 `create.nodeId`），**不要重跑第 2 步**，否则会建出第二条重复需求，**也不要去掉
  `--acceptance-spec` 重建**。把 stderr 原样报给用户，按报错修正 spec（格式、路径等）后，只重试
  这一条：

  ```
  agent-canvas-ctl set-requirement-acceptance <回执里的 create.nodeId> --spec <specUsed>
  ```

  这时仍要继续做第 3 步关联（用这个 nodeId），再提示用户条目还没写好。
- 退出码 1、stderr 含「创建结果未知」：创建请求已发出但结果不明，**需求节点可能已经建出来了**
  （stdout 里没有 `create.nodeId` 不代表没建）。先用 `agent-canvas-ctl search-nodes <标题> --kind requirement` 核对：已建出就把它当第 2 步的结果（用它的 nodeId 补
  `set-requirement-acceptance` 并继续第 3 步），确认没建出才重跑第 2 步。
- 退出码 1、stdout 没有 `create.nodeId`、stderr 既没有「需求已建」也没有「创建结果未知」：创建
  本身被拒，没有节点产生，把错误原样报出。不准去掉 `--acceptance-spec` 重试。

## 孤儿处置

**第 3 步失败时，立刻执行 `agent-canvas-ctl purge-node <第 2 步的 create.nodeId> --yes`**，收掉
第 2 步建出来的需求节点，并把失败原因如实报出。

## 什么时候调

**只在闸门 2 定稿后调一次**，收尾时不调：到收尾时上下文已经被实现细节占满，重写出来的需求
会偏向实现叙述。本节点已 implements 某个需求节点时，走第 0 步认领，不走第 1 步。

handoff：交出方在闸门 2 调；接手方**不调**。第 1 步只检查**本节点自己**的 implements 边，拦不住
接手方重复调用，只能靠这条约定。

## 边界

不是 `describe-node` 的替代——`describe-node` 管本节点自己的 title/description/taskType，
本 skill 管"另一个"需求节点的立项。两者常常紧挨着调，但各自独立，互不覆盖对方的产物。

---
name: external-closeout
description: Close out a named Agent Canvas claude-code/codex node from an external agent session without waking it — get a read-only verdict first (blocked or ready), then, only after the user confirms, run the lifecycle closeout (recheck, stop, migrate the claude session back to the repo root, hide) through one command. It does not merge, submit requirements, or touch worktrees or documents. Use when the user, in a session outside the target node, asks to close or finish out that node.
disable-model-invocation: true
user_invocable: true
version: "2.0.0"
---

# 外部收尾（external-closeout）

> 判定与收尾的全部规则都在应用里（判定由 `get-closeout-verdict` 给出，
> 收尾由 `run-closeout` 执行），这份 skill 只教你按顺序调命令、把结果原样交给用户。
> 收尾只管节点生命周期（停止、会话迁回、隐藏）：不合并、不送审、不动 worktree 与文档。

用户在**目标节点之外**的 agent 会话里点名一个节点，要求不唤醒它就把它收尾。你先拿**只读判定**，
用户确认后再一条命令执行收尾。**全程不往目标会话写入任何东西，也不读它。**

## 适用

- `agent-canvas-ctl` 可用；目标是 claude-code 或 codex 节点。其他节点不适用，直接说明。
- 目标就是你自己：不适用，节点自己收尾走 `close-node`。
- 命令都以目标的 **nodeId** 为参数。用户只给了标题或名字：向用户要 nodeId，不自己查找。

## 执行

> 只许用本文给出的命令（见「边界」第一条）；缺什么、拿不准什么，问用户，不探索。

### 1. 取判定（只读）

```
agent-canvas-ctl get-closeout-verdict <目标 nodeId>
```

返回的 JSON 里有 `canExecute`、`verdict`、`missingFacts`、`steps`、`text`。

- **把 `text` 原样贴给用户**，不改写、不摘要、不补充你自己的判断。
- 判定只有两种结果：**可收尾**，或**卡住 / 事实缺失**（节点在忙、有活跃 subagent、在等问题或工具确认、有后台任务在跑；或找不到节点、节点不是 claude-code / codex 节点）。
- `canExecute` 为 `false`（卡住或 `missingFacts` 非空）：到此为止。说明卡在哪、用户可以怎么处理，不进入第 2 步。

### 2. 向用户确认

在贴出判定之后，只问一件事：**现在执行收尾吗？** 等用户明确确认。**没有明确确认，不调 `run-closeout`。**

### 3. 执行收尾

```
agent-canvas-ctl run-closeout <目标 nodeId> --wait
```

- 固定四步：复查、停止、迁回会话、隐藏。没有审批卡片，通过判定后直接开始。
- 卡住或缺事实：命令直接拒绝；读报错，按第 4 步处理。
- `--wait` 会逐步打印进度：`✔ 3/4 迁回会话` 是完成，`– …（原因）` 是跳过，`✘ …：原因` 是失败；最后打印执行记录 JSON。
  **把执行记录里的 `text` 原样贴给用户。** 退出码 0 = 已完成，1 = 已停止或被拒绝（卡住 / 缺事实）。
- 命令已成功返回后，不要为核对再调 `get-closeout-verdict` 或别的命令。

### 4. 失败处置

每一行都是同一个动作：**读停止原因 → 告诉用户 → 等用户决定**。不盲目重试，不强杀，不自己换办法。
第 1、2 步失败时节点尚未停止；第 3 步失败时节点已停止、未隐藏，留在画布上提醒人处理。

| 情形 | 处置 |
|---|---|
| 判定卡住 / 缺事实 | 不执行；报告卡在哪、用户怎么处理 |
| 复查命中卡住 | 目标在判定之后被唤醒过；没有停止它。报告，用户处理后重跑 |
| 迁回：`running`（轮询超时） | App 仍认为会话在跑：可能是节点刚停、状态未收敛，也可能是别处（例如用户在终端里）恢复了同一个会话；稍后重跑 |
| 迁回：`locked` | 会话文件被 App 主进程内的会话锁占着；稍后重跑 |
| 迁回：`not-git` | 项目不在 git 仓库里；迁回不适用，报告即可 |
| 迁回：`multi-segment` | 会话文件散在两处以上，什么都没动；转会话修复功能 |
| 迁回：`attachment-conflict` | 仓库根里有同名附属物，源文件没动（根里的空壳文件可能已先被移去备份）；人处理冲突后重跑 |
| 迁回：`source-changed` | 副本已在根里、源还在；重跑时按当前源重算，与旧副本不等，变成 `multi-segment`，再转修复 |
| 迁回：`attachments-incomplete` | **会话本身已回到仓库根，可恢复**；留在原处的是同名附属物，失败信息列出它们的绝对路径。重跑时迁回返回 `already-in-root`，算完成并隐藏节点，**接受这个结果**；附属物对恢复会话的影响没有查，留在原处 |
| 迁回：`session-missing` | 磁盘上找不到该会话；无法修复，报告即可 |
| 迁回：`node-not-found` / `error: <msg>` | 节点或迁回本身异常；原样报告 |
| 其余 `✘` | 报告「已做到哪一步、没做什么」和原因 |

重跑 `run-closeout` 是安全的：已完成的步骤会被跳过，从失败的那一步继续。

### 5. 被中断时

`--wait` 自己会跨过服务端约 570 秒的单次上限继续等。即便调用被中断、没有拿到最终的执行记录 JSON：

- **重跑同一条 `run-closeout`**：已完成的步骤会被跳过。
- 重跑被拒，报「该节点已有外部收尾在执行：<runId>」：改调下面这条，`timedOut: true` 就重复调：

```
agent-canvas-ctl wait-closeout-run <目标 nodeId> --run-id <runId> [--after-step <n>]
```

- 报「执行记录不存在（App 可能已重启）」：重跑 `run-closeout`。
- 结束后同样把记录里的 `text` 原样贴给用户。

## 边界

- **只许三条命令**：`get-closeout-verdict` / `run-closeout` / `wait-closeout-run`。
  其余一律不做：任何 git 命令、搜索文件、列目录、读别的文件、查命令帮助、判定成功后再调一次判定、
  其他 ctl / arrange 子命令（包括列节点、查节点）、应用数据目录下的任何路径。
  缺东西或拿不准：**问用户，不探索**。
- **不替代 `close-node`**：节点自己收尾仍走 `close-node`；本 skill 只覆盖「目标会话不宜再唤醒」的场景。
- **不往目标会话注入任何东西**：不发消息、不发斜杠命令、不写目标终端；也不读它的会话内容。
- **不自己拼收尾步骤**：判定看 `get-closeout-verdict`，执行只用 `run-closeout`，不绕过它去做单个动作。
- **不调 `capture-requirement`**：立项只在闸门 2 发生一次。
- 合并、送审、worktree 清理、文档与关系更新都不属于收尾；用户问起，说明本 skill 不做这些，由节点所在任务按 AGENTS.md 流程处理。

---
name: external-closeout
description: Close out a named Agent Canvas claude-code/codex node from an external agent session without waking it — get a read-only verdict first, then, only after the user confirms, run the whole closeout (refresh description, check document relations, submit requirement, merge, stop, migrate session or remove worktree, hide) through one command. Use when the user, in a session outside the target node, asks to close or finish out that node.
disable-model-invocation: true
user_invocable: true
version: "1.0.0"
---

# 外部收尾（external-closeout）

> 判定与收尾的全部规则都在应用里（判定由 `get-closeout-verdict` 给出，
> 收尾由 `run-closeout` 执行），这份 skill 只教你按顺序调命令、把结果原样交给用户。

用户在**目标节点之外**的 agent 会话里点名一个节点，要求不唤醒它就把它收尾。你先拿**只读判定**，
用户确认后再一条命令执行收尾。**全程不往目标会话写入任何东西，也不读它。**

## 适用

- `agent-canvas-ctl` 可用；目标是 claude-code 或 codex 节点。其他节点不适用，直接说明。
- 目标就是你自己：不适用，节点自己收尾走 `close-node`。
- 命令都以目标的 **nodeId** 为参数。用户只给了标题或名字：向用户要 nodeId，不自己查找。

## 三项约定

应用没有默认值，三项都由你从当前仓库读出来再传。在**当前仓库根目录**（会话的工作目录）跑**这一条**命令，三项一次读完：

```
grep -n -E '^\| `staging` \||^scripts/merge-to-staging\.sh$|^output_dir:' docs/reference/git-workflow.md .hskill/handoff/config.md
```

按匹配到的文本取值：

| 参数 | 取自哪一行 | 取值 |
|---|---|---|
| `--integration-branch` | `git-workflow.md` 分支表里「集成 / 预发布」那一行，第一格的分支名 | `staging` |
| `--merge-script` | `git-workflow.md` 里单独一行的 `scripts/merge-to-staging.sh` | `scripts/merge-to-staging.sh` |
| `--handoff-dir` | `config.md` 里 `output_dir:` 那行 | 冒号后的值 |

按读到的值用，不再做任何核对。哪个文件不存在、或哪一行没匹配到：向用户要这三个值，不去别处找。

## 执行

> 只许用本文给出的命令（见「边界」第一条）；缺什么、拿不准什么，问用户，不探索。

### 1. 取判定（只读）

```
agent-canvas-ctl get-closeout-verdict <目标 nodeId> --integration-branch <分支> --merge-script <脚本> --handoff-dir <目录>
```

返回的 JSON 里有 `canExecute`、`verdict`、`missingFacts`、`relations`、`specPath`、`steps`、`text`。

- **把 `text` 原样贴给用户**，不改写、不摘要、不补充你自己的判断。
- 判定结果三类：**卡住**（硬拦，不能执行）/ **待办**（将要做的事）/ **未检查**（应用没法查、要用户自己看的项）。
- `canExecute` 为 `false`（有卡住项，或 `missingFacts` 非空）：到此为止。说明卡在哪、用户可以怎么处理，不进入第 2 步。

### 2. 向用户确认

在贴出判定之后，一次问清下面几项，并等用户明确确认。**没有明确确认，不调 `run-closeout`，也不调 `link-nodes`。**

- **`--remove-worktree`**：这个 worktree 是否由该节点的任务手工创建、明确归它所有？用户确认才加，否则不加。
- **spec 路径**：`specPath` 为 `null`（判定里写「需要你提供」）时，向用户要 spec 的**绝对路径**。用户说不需要刷新描述，才改用 `--skip-steps describe`。
- **缺的关系**：`relations` 列出已有的全部关系边。你不读目标会话；用户点名还缺哪条（并说出类型），就先补上，再执行。
  类型只能是 `depends-on` / `hands-off-to` / `implements` / `produces` / `references` 之一，用户说不清就问，不查：

```
agent-canvas-ctl link-nodes --from <id> --to <id> --type <t>
```

### 3. 执行收尾

```
agent-canvas-ctl run-closeout <目标 nodeId> --integration-branch <分支> --merge-script <脚本> --handoff-dir <目录> [--remove-worktree] [--spec <spec 绝对路径>] [--skip-steps describe,doc-check] --wait
```

- 你所在的节点上会弹出**审批卡片**（60 秒内要用户点允许）。卡片被拒或超时：什么都没写，如实告诉用户，问要不要重试。
  每次重跑都会再弹一次卡片，用户要再点允许；没告诉用户就不要自动重跑。
- 卡住、缺事实、缺 spec（没跳过 `describe` 时）、`--spec` 不是有效的绝对路径：命令直接拒绝，不弹卡片；读报错，按第 4 步处理。
- `--wait` 会逐步打印进度：`✔ 3/8 送审` 是完成，`– …（原因）` 是跳过，`✘ …：原因` 是失败；最后打印执行记录 JSON。
  **把执行记录里的 `text` 原样贴给用户。** 退出码 0 = 已完成，1 = 已停止或被拒绝。
- 命令已成功返回后，不要为核对再调 `get-closeout-verdict` 或别的命令。
- `--skip-steps` 只用于：描述刷新（`describe`）或文档检查（`doc-check`）失败后，**用户决定带着缺项继续**。不要自己决定跳过。

### 4. 失败处置

每一行都是同一个动作：**读停止原因 → 告诉用户 → 等用户决定**。不盲目重试，不强杀，不自己换办法。

| 情形 | 处置 |
|---|---|
| 判定有卡住项 / 缺事实 | 不执行；报告卡在哪、用户怎么处理 |
| 拒绝：缺 spec 或 `--spec` 无效 | 向用户要有效的绝对路径；用户不要刷新描述才用 `--skip-steps describe` |
| 审批卡被拒或超时 | 什么都没写；说明这一点，问要不要重试 |
| 描述刷新 / 文档检查失败 | 报告原因；用户决定带着缺项继续，才加 `--skip-steps` 重跑 |
| 合并失败 / 冲突 | 节点保持运行不关；报告原因，用户处理后重跑 |
| 其余 `✘` | 报告「已做到哪一步、没做什么」和原因 |

重跑 `run-closeout` 是安全的：已完成的步骤会被跳过。

### 5. 被中断或被拒绝时

`--wait` 自己会跨过服务端约 570 秒的单次上限继续等。即便调用被中断、没有拿到最终的执行记录 JSON：

- **重跑同一条 `run-closeout`**：已完成的步骤会被跳过；卡片会再弹，用户要再点允许，先告诉用户。
- 重跑被拒，报「该节点已有外部收尾在执行：<runId>」：改调下面这条，`timedOut: true` 就重复调：

```
agent-canvas-ctl wait-closeout-run <目标 nodeId> --run-id <runId> [--after-step <n>]
```

- 报「执行记录不存在（App 可能已重启）」：重跑 `run-closeout`。
- 结束后同样把记录里的 `text` 原样贴给用户。

## 边界

- **只许两类 shell 命令**：(a) 「三项约定」里那一条 `grep`；(b) `get-closeout-verdict` / `run-closeout` / `wait-closeout-run` / `link-nodes`。
  其余一律不做：任何 git 命令、搜索文件、列目录、读别的文件、查命令帮助、判定成功后再调一次判定、
  其他 ctl / arrange 子命令（包括列节点、查节点）、应用数据目录下的任何路径。
  缺东西或拿不准：**问用户，不探索**。
- **不替代 `close-node`**：节点自己收尾仍走 `close-node`；本 skill 只覆盖「目标会话不宜再唤醒」的场景。
- **不往目标会话注入任何东西**：不发消息、不发斜杠命令、不写目标终端；也不读它的会话内容。
- **不自己拼收尾步骤**：判定看 `get-closeout-verdict`，执行只用 `run-closeout`，不绕过它去做单个动作。
- **不调 `capture-requirement`**：立项只在闸门 2 发生一次。
- 合并只发生在独立节点上，交出方与接手方的取舍由应用判定；你不替它们改规则。

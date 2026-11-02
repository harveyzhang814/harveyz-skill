---
name: judge-release
description: Judge the requirements of a stable release against their acceptance criteria — read each requirement's acceptance items, gather evidence in the real environment, record per-item verdicts and pass the requirement when every item passes; launched by the pending-acceptance banner; only usable inside an Agent Canvas node.
disable-model-invocation: true
user_invocable: true
version: "1.1.0"
---

# 对照验收标准逐条下结论（judge-release）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

**人工触发**，不自动触发。一般由项目窗口顶部「待验收」提示条的「开始验收」拉起：验收节点建好后，会收到一条初始消息。

## 输入

初始消息是一行斜杠命令加参数，例如：

```text
/judge-release 版本 8.3.0，运行提交 <40 位>，稳定于 2026-10-14T05:07:08Z；需求节点：<节点编号>（261014-01 标题）、<节点编号>（261014-02 标题）
```

- `版本`：本次验收的版本号。
- `运行提交`：这个版本对应的完整提交号，写结论时的「验于提交」用它。
- `稳定于`：这个版本进入稳定的时间，观察期条目从这里起算。
- `需求节点`：要处理的需求节点编号（括号里是需求编号和标题，仅供辨认）。

**没有运行提交就停下**：初始消息里没给运行提交（或不是 40 位小写十六进制），说明这不是一个已稳定的版本，停下报告，不要写任何结论。

## 步骤

先对初始消息里的**每条需求**做第 1 步，得到待验收清单；第 2、3 步对整个项目做一次；然后对清单里的**每条需求**依次做第 4–7 步，最后做第 8 步。先清理、再标记、最后才写结论，顺序不能反。

### 1. 读需求现状并筛选

```
agent-canvas-ctl --result-format=action-v1 get-node <需求节点id>
```

**必须带 `--result-format=action-v1`，且写在 `get-node` 之前**：不带时输出是旧格式，只有标题、状态等通用字段，读不到下面这些需求字段。

需求字段平铺在 `value.node` 上：`requirementId`（需求编号）、`progress`（进度：`open` / `in_progress` / `in_acceptance` / `done`）、`disposition`（去向：`none` / `deferred` / `retired`）、`deliveredCommit`（交付提交）、`releasedIn`（已记的发布版本，可能没有）、`acceptanceItems`（验收条目，每条有编号、类别、验证方式、一句话说明，已有结论在每条的 `verdict` 里）。`value.node` 上没有 `progress`，说明这不是需求节点或节点编号不对，跳过并在汇总里报告。

跳过这条需求（不进待验收清单）并在汇总里报告的情形：

- `disposition` 不是 `none`：报"已退役 / 已搁置，未处理"。
- `progress` 不是 `in_acceptance`：报"进度已是 X，未处理"。

### 2. 清理过期的发布记录

回滚之后，有些需求的 `releasedIn` 还留着旧值，但它的交付提交已经不在当前运行的版本里。对**本项目所有**需求（不限于初始消息里的那几条）清掉这类残留：

```
agent-canvas-ctl list-nodes                  → 只看 kind 为 requirement 的节点
agent-canvas-ctl --result-format=action-v1 get-node <需求节点id>   → 逐条看 releasedIn / deliveredCommit
```

`list-nodes` 只列出未归档的节点，归档的需求不在清理范围里。对每条 `releasedIn` 有值的需求，在项目仓库里判断它的交付提交是否包含在运行提交里：

```
git merge-base --is-ancestor <交付提交> <运行提交>
```

- 退出码 0（在运行版本里）：不动。
- 退出码 1（不在），或需求没有 `deliveredCommit`：`agent-canvas-ctl unmark-requirement-released <需求节点id>`。已退役的需求也要清，这条不看 `disposition`。
- 其他退出码（例如仓库里找不到这个提交）：无法判定，不清理，在汇总里报告。

### 3. 标记发布版本

对第 1 步的待验收清单里的**每条需求**：

```
agent-canvas-ctl mark-requirement-released <需求节点id> --version <初始消息里的版本>
```

`--version` 与初始消息里的 `版本` 逐字一致。这一步只认当前运行的稳定版；开发版、未稳定版、版本不符、交付提交不在运行提交里，命令都会拒绝且不写入。被拒绝的需求**不写任何结论**，把拒绝原因报在汇总里。`releasedIn` 已经等于该版本的不用再标。

### 4. 读验收标准正文

在项目仓库里读交付提交时的 spec，看「验收标准」一节。spec 的位置沿这条需求的 `specified-by` 边找：

```
agent-canvas-ctl node-relations <需求节点id> --direction out --type specified-by   → 对端是 spec 文档节点
agent-canvas-ctl --result-format=action-v1 get-node <文档节点id>                  → value.node.filePath
git show <交付提交>:<仓库相对路径>
```

`filePath` 是绝对路径，要换算成仓库相对路径再给 `git show`：去掉仓库根前缀。仓库根用 `git -C <filePath 所在目录> rev-parse --show-toplevel`；路径若落在某个 worktree 里（含 `/.worktrees/<名>/` 或 `/.claude/worktrees/<名>/`），去掉到该 worktree 目录为止的前缀。没有 `specified-by` 边，或 `git show` 失败：不要猜，在汇总里报告"找不到验收依据"，这条需求不写结论。

按条目编号（`V1`、`V2`…）把正文里每条的验证方式、操作步骤和通过判据对上第 1 步取到的条目。对不上（编号缺失）的条目不要猜，在汇总里报告"无法对上正文"，不写结论。

### 5. 按验证方式逐条处理

| 验证方式 | 做法 |
|---|---|
| 机器可查（`machine`） | 按正文的步骤在真实环境取证（真实运行的版本，不是单测），然后写结论 |
| 观察期（`observation`） | 到期日 = `稳定于` 的时间 + 条目的 `observationDays` 天。**未到期**：只报告"观察中，剩 N 天"，不写结论；**已到期**：按正文取证，然后写结论 |
| 人工裁决（`human`） | **不写结论**（写了也会被拒）。整理成清单：条目编号、一句话说明、正文里的判据，请用户到该需求的面板上自己判 |

写结论：

```
agent-canvas-ctl record-requirement-verdict <需求节点id> --item <条目编号> --result <pass|fail> --evidence <证据> --commit <运行提交>
```

- `--item` 与条目编号完全一致，区分大小写。
- `--evidence` 写你实际看到的东西：命令、路径、数据；不要只写"已验证"。
- `--commit` 一律传初始消息里的**运行提交**，不是交付提交。
- 证据明确显示不满足判据时写 `fail`；证据不足、环境取不到证时**不写**，在汇总里报告"证据不足"及原因。
- 条目已有人写的结论（`by` 为 `human`）时不要覆盖。

### 6. 判断需求是否可以通过

再取一次现状（同样带 `--result-format=action-v1`，看每条的 `verdict`）：

```
agent-canvas-ctl --result-format=action-v1 get-node <需求节点id>
```

- 每条条目都有「通过」结论 → `agent-canvas-ctl pass-requirement <需求节点id>`。
- 还有条目没结论（观察中、等人裁决、证据不足）→ 不调 `pass-requirement`，留在汇总里。
- 有「不通过」的条目 → 报告条目编号与证据，**由人决定打回还是改标准**，你不替人选。

### 7. 下一条

回到第 4 步处理清单里的下一条需求。

### 8. 汇总

所有需求处理完后，一次说清：

- 每条需求：处理到哪一步、哪些条目已写结论（通过或不通过）、需求是否已通过。
- 发布记录：清理了哪几条（和为什么）、无法判定而没清的、标记了哪几条、标记被拒的及原因。
- 等用户判的条目：人工裁决清单，指到对应需求的面板。
- 观察中的条目：每条的到期日。
- 跳过的需求和条目：原因（含已退役 / 已搁置、进度不对、找不到验收依据）。

## 边界

- 不改条目：不增删、不改条目的内容或验证方式。
- 不把 `progress` 改到 `in_progress`。
- 发布记录只用 `unmark-requirement-released`（清理）和 `mark-requirement-released`（标记）两个命令写，不碰别的字段；不动 `disposition`。
- 不调 `fail-requirement`：不通过时由人决定打回还是改标准。
- 不做验收之外的事：不修代码、不改 spec，也不与这些需求建任何关系——验收节点不是实现方。

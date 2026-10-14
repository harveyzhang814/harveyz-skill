---
name: judge-release
description: Judge the requirements of a stable release against their acceptance criteria — read each requirement's acceptance items, gather evidence in the real environment, record per-item verdicts and pass the requirement when every item passes; launched by the pending-acceptance banner; only usable inside an Agent Canvas node.
disable-model-invocation: true
user_invocable: true
version: "1.0.1"
---

# 对照验收标准逐条下结论（judge-release）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

**人工触发**，不自动触发。Codex 通过 `agents/openai.yaml` 禁止隐式调用。一般由项目窗口顶部「待验收」提示条的「开始验收」拉起：验收节点建好后，会收到一条初始消息。

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

对初始消息里的**每条需求**依次做第 1–4 步，最后做第 5 步。

### 1. 读需求现状

```
agent-canvas-ctl --result-format=action-v1 get-node <需求节点id>
```

**必须带 `--result-format=action-v1`，且写在 `get-node` 之前**：不带时输出是旧格式，只有标题、状态等通用字段，读不到下面这些需求字段。

从 `value.node.requirement` 取需求的 `status`、交付提交（`deliveredCommit`）、验收依据（`acceptanceSpec`）、验收条目（`acceptanceItems`，每条有编号、类别、验证方式、一句话说明，已有结论在每条的 `verdict` 里）。`value.node.requirement` 不存在，说明这不是需求节点或节点编号不对，跳过并在汇总里报告。

`status` 已经不是 `in_acceptance` 的，跳过这条需求并在汇总里报告"状态已是 X，未处理"。

### 2. 读验收标准正文

在项目仓库里读交付提交时的 spec，看「验收标准」一节：

```
git show <交付提交>:<验收依据>
```

按条目编号（`V1`、`V2`…）把正文里每条的验证方式、操作步骤和通过判据对上第 1 步取到的条目。对不上（编号缺失、`git show` 失败）的条目不要猜，在汇总里报告"无法对上正文"，不写结论。

### 3. 按验证方式逐条处理

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

### 4. 判断需求是否可以通过

再取一次现状（同样带 `--result-format=action-v1`，看每条的 `verdict`）：

```
agent-canvas-ctl --result-format=action-v1 get-node <需求节点id>
```

- 每条条目都有「通过」结论 → `agent-canvas-ctl pass-requirement <需求节点id>`。
- 还有条目没结论（观察中、等人裁决、证据不足）→ 不调 `pass-requirement`，留在汇总里。
- 有「不通过」的条目 → 报告条目编号与证据，**由人决定打回还是改标准**，你不替人选。

### 5. 汇总

所有需求处理完后，一次说清：

- 每条需求：处理到哪一步、哪些条目已写结论（通过或不通过）、需求是否已通过。
- 等用户判的条目：人工裁决清单，指到对应需求的面板。
- 观察中的条目：每条的到期日。
- 跳过的需求和条目：原因。

## 边界

- 不改条目：不增删、不改条目的内容或验证方式。
- 不改状态到 `in_progress`。
- 不调 `fail-requirement`：不通过时由人决定打回还是改标准。
- 不给人工裁决条目写结论。
- 不在非稳定版本上写结论：初始消息没给运行提交时停下报告。
- 不做验收之外的事：不修代码、不改 spec，也不与这些需求建任何关系——验收节点不是实现方。

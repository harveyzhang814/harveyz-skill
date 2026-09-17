---
name: relation-review
description: Global-Pilot-only relation-type governance loop — scans the pending queue and runs proposed types through four gates before promotion; invoked on a cron schedule, must not be manually called from a project canvas node.
user_invocable: false
version: "1.0.1"
---

# Relation 类型治理循环（relation-review）

如果当前不是全局 Pilot 身份（`agent-canvas-ctl` 命令不存在，或明显运行在某个项目画布节点
的上下文里），这个 skill 不适用，直接跳过。

## 第一步：数待议区，决定要不要唤起完整审议

调 `agent-canvas-ctl relation-review-queue`，拿到全部画布里
`type='unspecified' && provenance='agent' && reading != null` 的关系列表，每条带
`{relationId, cwd, fromNodeId, toNodeId, fromKind, toKind, reading, why, createdAt}`。

**`WAKE_N = 5`**：本次列表长度**相比上次记录的基线**新增条目数 < 5 时，只记下这次的数量
（可以简单回复"待议区当前 N 条，未达唤起阈值，不审议"），**不要往下做任何关卡判断**——
空转成本压到这一次计数（spec §5.1）。达到阈值才继续。

## 第二步：按语义聚类

把待议区列表按"读法在说同一件事"聚类（不是按 `reading` 字面量分组——不同措辞可能是
同一个模式）。每一簇是一个候选 type 提案。

## 第三步：对每个候选簇过四道关卡

**审议时不要看任何"这条提案本来该不该过"的暗示**——你只应该看到 `relation-review-queue`
返回的原始数据，不要预设结论。每道关卡的产出必须引用真实 `relationId`，不能虚构案例；
写不满结构化字段就是没过这道关，不能用"综合考虑认为合理"糊过去。

### 关卡一 · 谓语关

判据：**把 `to` 端换成另一种 kind 的节点，这个 type 还成立吗？** 成立才是谓语，不成立
说明它描述的是宾语的种类（比如"这份文档是设计稿"这种，该由文档节点子类型承载，不是
新 relation type——这条岔路必须堵死，见 spec §1.3）。

打回时必须**明说是关卡一**，否则同一提案会反复被提上来。

### 关卡二 · 聚类关（用例门槛）

判据：同一语义在待议区累计 **≥ `PROMOTE_N`（3）条**，且 **来自 ≥2 个不同节点**
（`fromNodeId` 不同，不是同一个节点连记了好几遍——那是一个案例复述多遍，不是一个模式）。

不满足就打回，附上当前累计数量和涉及的节点数，方便下次审议时快速核对是否已经攒够。

### 关卡三 · 可辨别性关

判据：对该端点对上现有的**每一个** type（用 `agent-canvas-ctl relation-guide` 查该端点对
当前合法的 type 列表），举出一个真实 `relationId`，说明在那条具体的关系上，新 type 与
这个现有 type 会给出不同答案。写进最终提案的 `distinguishedFrom` 字段。

**有一个现有 type 举不出区分案例，就不是新 type，是那个已有 type 的实例**——打回，
并建议把这批关系改用 `agent-canvas-ctl update-relation <relationId> --type <已有type>`
归到它名下（不要自己批量执行，写进审议报告让下一步的人工事后核查时看到）。

每条候选自带的 `why` 字段（agent 走 `link-nodes` 逃逸阀建这条关系时就已经写明"为什么
现有 type 装不下"）是关卡三最直接的原料，优先核对这些——**不是 `despite`**：`despite`
只在写入那一刻用于校验"逐个点名已排除的现有 type"，校验完就丢弃，不落在 Relation 记录上、
`relation-review-queue` 也不会把它吐出来，审议阶段读不到。

### 关卡四 · 消费关（软）

判据：写出至少一个"谁会读它"——一句具体的提问（例如"这个需求被哪个取代了"），
允许答案是"agent 通过 `get_node_relations`/`relation-guide` 读回"（现有 7 个 type 里
已有 4 个只有这个消费点，不是更高标准）。一句都写不出就打回。

## 第四步：对通过全部四关的提案执行升格

```
agent-canvas-ctl relation-promote \
  --name <新type名> \
  --reading "<谓语读法>" \
  --endpoints "<fromKind>:<toKind>,<fromKind>:<toKind>" \
  --evidence "<cwd>::<relationId>,<cwd>::<relationId>,..." \
  --gate-reasoning "<四道关卡论证全文，含每一关的判断依据>"
```

`--endpoints` 里的 `<fromKind>`/`<toKind>` 是节点 **kind**（比如 `pty`/
`requirement`），不是节点 id——跟 `--evidence` 里的 `relationId` 是两种不同的标识符，
不要混用。`--evidence` 列出的应该是这一簇里全部符合条件的 `relationId`（不止 3 条门槛
数量，攒了多少条证据就列多少条——升格后这些关系的 `type` 会被原样改写成新 type 名）。

对没通过的提案，**不调用任何写操作**，只在报告里说明打回在哪一关、原因是什么。

## 第四步之后：审议中顺带发现的其他治理动作

四道关卡只回答"这个候选该不该升格成新 type"。审议过程中如果顺带发现**已经是正式 type**
的词条有下面三类问题，同一轮一并处理（不需要单独等下一轮）——这三个动作**不改任何存量
relation 数据**，只改注册表条目的 `status`/`supersededBy`（spec §5.4）：

- **发现两个现存 type 其实是同一件事**（例如关卡三的可辨别性检查显示不出真实差异）：
  `agent-canvas-ctl relation-merge --from <旧type> --into <目标type> --gate-reasoning "<为什么判定等价>" [--evidence <relationId>,...]`
  `from` 会被标记为 `deprecated`、`supersededBy` 指向 `into`；`into` 必须是当前存在的 type，
  不存在会被拒绝。
- **发现一个现存 type 已经没有意义**（比如从未被真实使用、或语义已被更好的 type 完全覆盖）：
  `agent-canvas-ctl relation-deprecate --name <type> --gate-reasoning "<为什么判定过时>" [--evidence <relationId>,...]`
  有代码消费点（`codePinned`，如 `spawns`/`implements`/`unspecified`）的 type 会被硬拒绝，
  不要尝试废弃它们。
- **发现一个现存 type 的名字本身有误导性**：
  `agent-canvas-ctl relation-rename --from <旧名字> --to <新名字> --gate-reasoning "<为什么需要改名>" [--evidence <relationId>,...]`
  等价于"新建 `to` + 合并 `from`→`to`"，`to` 必须已经存在（先用 `relation-promote`
  建出新名字，再用这个命令把旧名字标记废弃）。

这三个动作不是每轮都会用到——待议区常年空转、四道关卡常年不通过是预期状态（spec §9.1），
这三个动作同样可能常年不触发。**不要为了"这次总得做点什么"而勉强套用它们**。

## 第五步：简短报告

列出：本轮待议区总数、本次新增数（是否达到唤起阈值）、审议的候选簇数、每簇的关卡结论
（通过/打回及原因）、执行了哪些升格（附 changelogId）、顺带执行了哪些废弃/合并/改名
（附 changelogId，没有就说明本轮没有）。

## 什么时候不要往下走

- 待议区新增 < `WAKE_N`：只报数量，不审议（见第一步）。
- 候选簇 < `PROMOTE_N` 或 < 2 个不同节点：打回在关卡二，不进关卡三。
- `agent-canvas-ctl` 命令不存在，或明显不是全局身份：整个 skill 不适用，跳过。

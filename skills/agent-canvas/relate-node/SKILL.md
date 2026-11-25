---
name: relate-node
description: Work out the current node's semantic relations to other Agent Canvas nodes (hands-off-to/implements/produces or references docs) — use after Gate 2 is finalized and before the closing report, when deciding whether to link an existing node; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.1.0"
---

# 梳理节点关系（relate-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么做

1. 调 `agent-canvas-ctl relation-guide`（不需要传 nodeId，按祖先进程链反查自己），
   拿到 `{ matrix, criterion, rules, tiers, selection, phase, context }`（带 `--from <id> --to <id>` 时多一个 `pair`，见第 3 步）：
   - `matrix`：`(fromKind, toKind)` 端点对允许的 type 全集，每项带 `reading`（怎么读，
     type 名是谓语、from 是主语、to 是宾语）与 `agentAllowed`（false 的项只由系统写入，不要尝试建）。
     **`created-from` 由建节点机制自动写，任何时候都不手动连；`spawns`、`originates-from` 已退役。**
   - `criterion`：判据原文，「不记它，将来某个具体动作会做错或做不了；写不出消费点就不记」。
   - `rules`：E1–E8 事件规则（事件 → 关系 → 写入方），说明哪些关系由谁在什么时候写。
   - `tiers`：关系类型的分层。
   - `selection`：选型四步与各类型的判据。
   - `phase.start` / `phase.finish`：当前所处阶段该核对哪些 type（见下方「两次调用」）。
   - `context.node`：自己这个节点的 id/title/kind/cwd。
   - `context.existingRelations`：自己已有的关系（含对端摘要）——**先看这个，避免重复主张**。
   - `context.lineage`：来历链（沿 `created-from`）。
   - `context.waitingOn`：本会话还在等待的会话（`waits-for` 的 active 出边目标）。
   - `context.requirementNodes`：画布上的需求节点候选。
   - `context.candidateDocs`：同 cwd 下的 markdown/html/text 节点候选。
2. **按 `phase` 对应的 type 列表逐个比对**（不是自由联想）：对每个候选 type，问「`context`
   里有没有一个具体的候选对象（需求节点/文档节点/来历链上的节点），配得上这个 type 的读法」。
   配不上就跳过，不要为了凑数硬建。
3. **选型**：候选类型拿不准时（会话→文档要在 `references` / `produces` 之间选，会话↔会话要在
   `waits-for` / `hands-off-to` 之间选），调 `agent-canvas-ctl relation-guide --from <自己> --to <候选>`，
   按返回的 `pair` 候选与判据选；返回 `pair.determined: true`（已确定）时直接用。
   `waits-for` 由发起等待的一方（fork-topic、派活方）当场写，本 skill 不写 `waits-for`；会话↔会话只核对 `hands-off-to`。
4. 对通过判据的每一条，调 `agent-canvas-ctl link-nodes --from <id> --to <id> --type <t> [--label <s>]`。
   传矩阵外的组合会报错并回传该端点对的合法 type 列表。**如果连报错列出的合法 type 都没有
   一个装得下**（不是"选一个将就"，是确实没有语义相符的），改用
   `agent-canvas-ctl link-nodes --from <id> --to <id> --reading "<谓语读法>" --why "<原因>" --despite <报错列出的全部合法 type，逗号分隔>`
   逃逸阀记下来，不要放弃这条主张也不要硬套一个不准确的现有 type。`--despite` 必须逐个列全，漏一个即拒。
5. 简短报告建了哪些关系、跳过了哪些候选及原因。
6. **等待提醒**：`context.waitingOn` 非空时，在报告里列出这些会话，并提示「结论已交回的，可经用户同意后用
   `agent-canvas-ctl resolve-wait <relationId>` 解除」（relationId 用
   `agent-canvas-ctl node-relations <自己> --direction out --type waits-for` 查）。本 skill 不自行解除。

## 两次调用（对齐 describe-node 的两个时机，可紧挨着调）

- **第一次（闸门 2 通过后、开工实现前）**：核对 `phase.start` 列出的 type——
  `implements`（需求此刻最显眼，收尾时早被压缩出上下文）、
  `hands-off-to`（**只核对，不在这里新建**——接手方要补走 `/handoff` verify，见下方归属规则）。
  **不核对 `explores`**：即使 `phase.start` 列了它，也由会话 agent 按画布约定当场写，不归本 skill。
- **第二次（收尾、汇报验收前）**：核对 `phase.finish` 列出的 type——
  `produces`/`references`（文档要等到这时才成立）、
  `hands-off-to`（这次要交出去、且已经能指认接手节点时才新建）。

## hands-off-to 的归属

**谁先能同时指认两端谁建**，另一方只核对、不重复主张（两边都建会出重复关系）：

- 交出方在 `/handoff` author 阶段**已经能指认接手节点**（比如接手用的节点是它亲手创建的）
  → 当场建，并在交接文档里注明已建。
- 指认不到接手节点（常态：接手方是还不存在的下一个 session）→ 交出方只把自己的节点 id 写进
  交接文档 frontmatter 的 `source_node`，由**接手方在 `/handoff` verify 阶段**读到它之后
  建、并把自己的 id 回填 `target_node`。
- 建之前先看 `context.existingRelations` / `node-relations`，已有就跳过。

接手方补的只有这一条边：**不建 `implements`、不调 `capture-requirement`**——需求挂在交接源
节点上，接手节点该不该关联需求是另一个问题。

## 什么时候不要调

- 想连会话之间的 `depends-on`：App 会拒绝；需求之间的 `depends-on` 按 E4 由发现问题的会话当场写，不归本 skill。
- 会话刚开始、还没有任何候选对象（需求/文档/上游节点）时。
- 矩阵里没有对应格子的端点对（比如两个 group 节点之间）——这是显式的空格子，不是遗漏。

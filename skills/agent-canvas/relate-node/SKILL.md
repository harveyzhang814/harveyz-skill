---
name: relate-node
description: Work out the current node's semantic relations to other Agent Canvas nodes (depends-on/hands-off-to/implements/produces or references docs) — use after Gate 2 is finalized and before the closing report, when deciding whether to link an existing node; only usable inside an Agent Canvas node.
user_invocable: true
version: "1.0.1"
---

# 梳理节点关系（relate-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

## 怎么做

1. 调 `agent-canvas-ctl relation-guide`（不需要传 nodeId，按祖先进程链反查自己），
   拿到 `{ matrix, criterion, phase, context }`：
   - `matrix`：`(fromKind, toKind)` 端点对允许的 type 全集，每项带 `reading`（怎么读，
     type 名是谓语、from 是主语、to 是宾语）与 `agentAllowed`（false 的项——目前只有
     `spawns`——是系统专属，不要尝试建）。
   - `criterion`：判据原文，「不记它，将来某个具体动作会做错或做不了；写不出消费点就不记」。
   - `phase.start` / `phase.finish`：当前所处阶段该核对哪些 type（见下方「两次调用」）。
   - `context.node`：自己这个节点的 id/title/kind/cwd。
   - `context.existingRelations`：自己已有的关系（含对端摘要）——**先看这个，避免重复主张**。
   - `context.lineage`：spawns/hands-off-to 血缘链。
   - `context.requirementNodes`：画布上的需求节点候选。
   - `context.candidateDocs`：同 cwd 下的 markdown/html/text 节点候选。
2. **按 `phase` 对应的 type 列表逐个比对**（不是自由联想）：对每个候选 type，问「`context`
   里有没有一个具体的候选对象（需求节点/文档节点/血缘链上的节点），配得上这个 type 的读法」。
   配不上就跳过，不要为了凑数硬建。
3. 对通过判据的每一条，调 `agent-canvas-ctl link-nodes --from <id> --to <id> --type <t> [--label <s>]`。
   传矩阵外的组合会报错并回传该端点对的合法 type 列表。**如果连报错列出的合法 type 都没有
   一个装得下**（不是"选一个将就"，是确实没有语义相符的），改用
   `agent-canvas-ctl link-nodes --from <id> --to <id> --reading "<谓语读法>" --why "<原因>" [--despite <已排除的type>,...]`
   逃逸阀记下来，不要放弃这条主张也不要硬套一个不准确的现有 type。
4. 简短报告建了哪些关系、跳过了哪些候选及原因。

## 两次调用（对齐 describe-node 的两个时机，可紧挨着调）

- **第一次（闸门 2 定稿后、建分支前）**：核对 `phase.start` 列出的 type——
  `implements`（需求此刻最显眼，收尾时早被压缩出上下文）、`depends-on`（已知的阻塞）、
  `hands-off-to`（**只核对，不在这里新建**——接手方要补走 `/handoff` verify，见下方归属规则）。
- **第二次（收尾、汇报验收前）**：核对 `phase.finish` 列出的 type——
  `produces`/`references`（文档要等到这时才成立）、`depends-on`（补漏）、
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

- 会话刚开始、还没有任何候选对象（需求/文档/上游节点）时。
- `context.existingRelations` 里已经有语义相同的关系时——不要重复主张。
- 矩阵里没有对应格子的端点对（比如两个 group 节点之间）——这是显式的空格子，不是遗漏。

---
name: capture-intent
description: "Capture a need the user mentions for later as an Agent Canvas requirement node. Triggers on casual phrasing like 'we should do X later', 'note this requirement', 'add this to the backlog', 'remember to build X'. Writes to the current canvas by default, or to another project's running canvas when the user names it. Not for the requirement the current session is implementing (use capture-requirement)."
user_invocable: true
version: "1.0.0"
---

# 记录意图（capture-intent）

如果 `agent-canvas-ctl` 命令不存在，这个 skill 不适用，直接跳过。

把用户随口提出、以后要做的需求立成一个需求节点。顺序：澄清 → 定画布 → 查 schema → 查重 → 确认 → 写入。完整的需求描述是查重和起标题的依据，顺序不能反。

与 `capture-requirement` 的分界：那个记的是本会话**正在实现**、已经有 spec 的需求，并连 `implements`；本 skill 记以后要做的需求，**不连任何关系边，也不放上画布**。

## 1. 澄清需求（2-3 轮）

只问需求、不问方案；上下文里已经明确的直接跳过。每次只问一个问题，优先给选项。

1. **需求**——要解决什么问题、实现什么功能？用户已说清楚就复述确认。
2. **紧急程度**——默认不问；用户暗示紧急或不重要时据此定档。
3. **背景**——为什么现在提出来（可选）。

不主动问验收。用户描述里已经带了完成标准（"做完应该能……"），拆出来留作验收文字。

## 2. 确定目标画布

- 用户没点名别的项目 → 当前画布，后面的命令不带 `--canvas`。
- 用户点名了别的项目：
  1. 跑 `agent-canvas-ctl --canvas /nonexistent resolve-canvas`。它必然以退出码 1 失败，stderr 逐行列出当前可用画布的绑定路径。
  2. 按项目名匹配其中一条路径；有多条候选就让用户选。
  3. 跑 `agent-canvas-ctl --canvas <路径> resolve-canvas`，退出码为 0 才算定下来。之后每条命令都在子命令**之前**带同一个 `--canvas <路径>`。
- 清单里没有该项目 → 报告「<项目> 的画布没开，记不进去」，然后停止。不改写到别的画布，也不直接改 `~/.agent-canvas/` 下的文件。

## 3. 查 schema

每次都查，不凭记忆：

```bash
agent-canvas-ctl describe-action create_requirement_node
```

从 `inputSchema` 取字段、类型、枚举和必填项；从 `bindings` 里 `surface` 为 `cli` 的那条取 `usage` 和 `args.flags`。本 skill 不写字段名和取值，只在下一节写各字段的语义；按 schema 里的字段名和 `description` 把语义对到字段上。

- 某条语义对不上任何字段 → 跳过它，在最终报告里说明。
- schema 有必填字段，而下一节没有对应的语义 → 停止，报告这个字段，不去猜。
- 枚举档数和下一节描述的不一样 → 按相对位置映射，在确认摘要里标出来。

## 4. 各字段的写法

- **标题**：`<对象> <类型> <描述>`，与画布上已有的需求标题一致，例如「feed feat 实现 Creator/Channel 名册架构」「publish-skill fix 命名检查由阻断改为建议」。
  - 对象：受影响的 skill、模块或子系统名。
  - 类型：feat / fix / refactor / docs / chore。
  - 描述：写出关键区分点，不用「优化」「修复」这类泛词，也不堆细节。
- **需求正文**：写做什么、为什么。**不写怎么做**。篇幅以说清楚为准。
- **优先级**：默认取中间档；用户表示紧急取最高档，表示不重要取最低档。
- **验收文字**：只在第 1 步拆出了完成标准时才填，照用户原意写，不替用户补全。
- **状态**：不传，取缺省值。
- **验收依据文件**：不传（没有 spec）。

## 5. 查重

```bash
agent-canvas-ctl [--canvas <路径>] search-nodes <需求关键词> --limit 5
```

只看结果里 `kind` 为 requirement 的节点。有语义重叠时问：

> 发现可能重叠的需求 **[标题]（[编号]）**，跳过还是仍然新建？

用户选跳过就到此结束。

## 6. 确认摘要

> 记录为：**[项目/画布]** — [标题]，[优先级]。确认吗？

有枚举映射或被跳过的字段，一并列出。用户确认后才写入。

## 7. 写入与报告

按第 3 步取到的 `usage` 拼出 `create-requirement-node` 命令，只传第 4 步对得上的字段；点名了别的项目时，`--canvas <路径>` 放在子命令之前。

- 成功：报告需求编号（返回里的 `requirementId`，形如 YYMMDD-XX）和标题。
- 失败：把 stderr 原样报出，不重试，也不改参数重跑。

---
name: capture-intent
description: "Capture a need the user mentions for later as an Agent Canvas requirement node. Triggers on casual phrasing like 'we should do X later', 'note this requirement', 'add this to the backlog', 'remember to build X'. Writes to the current canvas by default, or to another project's running canvas when the user names it. Not for the requirement the current session is implementing (use capture-requirement)."
user_invocable: true
version: "1.3.1"
---

# 记录意图（capture-intent）

如果 `agent-canvas-ctl` 命令不存在，这个 skill 不适用，直接跳过。

把用户随口提出、以后要做的需求立成一个需求节点。顺序：澄清 → 定画布 → 取字段映射 → 查重 → 确认 → 写入。完整的需求描述是查重和起标题的依据，顺序不能反。

与 `capture-requirement` 的分界：那个记的是本会话**正在实现**、已经有 spec 的需求，并连 `implements`；本 skill 记以后要做的需求，**不连任何关系边，也不放上画布**。

## 1. 澄清需求（2-3 轮）

只问需求、不问方案；上下文里已经明确的直接跳过。每次只问一个问题，优先给选项。

1. **需求**——要解决什么问题、实现什么功能？用户已说清楚就复述确认。
2. **紧急程度**——默认不问；用户暗示紧急或不重要时据此定档。
3. **背景**——为什么现在提出来（可选）。

不主动问验收。用户描述里已经带了完成标准（"做完应该能……"），逐条拆出来，第 7 步写成验收条目；不并入需求正文。

## 2. 确定目标画布

- 用户没点名别的项目 → 当前画布，命令不带 `--canvas`。
- 点名了别的项目 → 按 agent-canvas-control「寻址」一节定位：`--canvas <路径> resolve-canvas` 退出码为 0 才算定下，有多条候选就让用户选；之后每条命令都在子命令之前带同一个 `--canvas`。
- 可用画布清单里没有该项目 → 报告「<项目> 的画布没开，记不进去」并停止。不改写到别的画布，不碰 `~/.agent-canvas/`，也不回退到 TODO.md 或 capture-todo。

## 3. 取字段映射

本 skill 不写字段名和取值，只在下一节写语义。语义对到哪个 flag、取哪个值，缓存在本机 `~/.hskill/capture-intent/`：`schema.json` 是上次写入成功时的 schema 快照，`mapping.md` 是映射表。先比对：

```bash
d="$HOME/.hskill/capture-intent"; mkdir -p "$d"
agent-canvas-ctl describe-action create_requirement_node \
  | jq -S '{schema: .action.inputSchema, cli: [.action.bindings[] | select(.surface == "cli") | {usage, flags: .args.flags}]}' \
  > "$d/schema.new.json"
cmp -s "$d/schema.json" "$d/schema.new.json" && echo "schema: same" || echo "schema: diff"
grep -qxF "$(grep -m1 '^version:' <本 SKILL.md 路径>)" "$d/mapping.md" 2>/dev/null && echo "version: same" || echo "version: diff"
```

- **两项都 same** → 只读 `mapping.md`，照表用，不读 schema。
- **version: diff**（含首次运行）→ 下一节可能变了：读 `schema.new.json`，整张重做映射。
- **只有 schema: diff** → 看变了什么，每行带字段路径：

  ```bash
  f='paths(scalars) as $p | [$p, getpath($p)]'
  diff <(jq -c "$f" "$d/schema.json") <(jq -c "$f" "$d/schema.new.json")
  ```

  只改了说明文字，或改动没碰到映射表里的 flag 和取值 → 映射不变；否则只重做受影响的行。

重做映射时：

- 语义对不上任何字段 → 跳过，记进映射表。
- 有必填字段而下一节没有对应语义 → 停止，报告该字段，不去猜。
- 枚举档数与下一节不一致 → 按相对位置映射，在映射表里注明。

`mapping.md` 的格式：

```
version: "<本 skill 的版本号>"

| 语义 | flag | 取值 |
|---|---|---|
| 标题 | … | 文本 |
| 优先级 | … | 最低档 / 中间档 / 最高档 → <枚举值> |
| … | | |

不传：<flag>（原因），…
跳过的语义：<语义>（原因）；没有写「无」
```

映射新建或改过，都要在第 6 步交用户审；`schema.json` 与 `mapping.md` 等第 7 步写入成功后才落盘。

`jq` 不存在时不用缓存：读 `agent-canvas-ctl help create-requirement-node` 当场映射，照样在第 6 步交用户审，并在报告里说明缓存没生效。

## 4. 各字段的写法

- **标题**：`<对象> <类型> <描述>`，与画布上已有的需求标题一致，例如「feed feat 实现 Creator/Channel 名册架构」「publish-skill fix 命名检查由阻断改为建议」。
  - 对象：受影响的 skill、模块或子系统名。
  - 类型：feat / fix / refactor / docs / chore。
  - 描述：写出关键区分点，不用「优化」「修复」这类泛词，也不堆细节。
- **需求正文**：写做什么、为什么。**不写怎么做**，也不写完成标准。篇幅以说清楚为准。
- **优先级**：默认取中间档；用户表示紧急取最高档，表示不重要取最低档。
- **状态**：传「新建、未开始」那一档，不依赖缺省值。
- **验收条目**：创建命令不收条目。第 1 步拆出了完成标准时，第 7 步在创建成功后另写；没有就不写，不替用户补全。每条一句话（不超过 60 字），照用户原意；类别和验证方式按 `agent-canvas-ctl describe-action set_requirement_acceptance` 里 items 的取值选最贴近的一档，拿不准时验证方式取人工裁决；编号从 V1 起顺排。
- **spec**：不传（没有 spec）。

## 5. 查重

```bash
agent-canvas-ctl [--canvas <路径>] search-nodes <需求关键词> --limit 20 \
  | jq '(if type=="array" then . else .results end) | map(select(.kind == "requirement"))'
```

结果有两种形态：旧版 App 返回顶层数组，直接用；新版 App 返回 `{results, truncated, totalMatches}`，读
`.results`。上面的 jq 两种都认，只留 `kind` 为 requirement 的节点。没有 `jq` 时照同样规则读原始输出。有语义重叠时问：

> 发现可能重叠的需求 **[标题]**，跳过还是仍然新建？

用户选跳过就到此结束。

## 6. 确认摘要

> 记录为：**[项目/画布]** — [标题]，[优先级]。确认吗？

第 3 步新建或改动了映射时，摘要后附上整张映射表、标出改动的行，请用户一并审；用户对映射有异议就当场改，改完再给用户看一遍。映射没变不附。用户确认后才写入。

## 7. 写入与报告

按映射表拼出 `create-requirement-node` 命令，只传表里有 flag 的语义。

- 成功：报告需求编号（返回里的 `requirementId`，形如 YYMMDD-XX）和标题。第 3 步不是两项都 same 时把缓存落盘：`mv "$d/schema.new.json" "$d/schema.json"`；映射新建或改过，把用户审过的表写进 `mapping.md`。
- 有完成标准时，接着写条目：`agent-canvas-ctl [--canvas <路径>] set-requirement-acceptance <返回的 nodeId> --items '<条目 JSON 数组>'`。失败时把 stderr 原样报出，说明「需求已建、条目未写」并给出 nodeId，不重试；用户可以在需求面板的验收区补写。
- 失败：把 stderr 原样报出，不重试，也不改参数重跑；缓存不落盘。

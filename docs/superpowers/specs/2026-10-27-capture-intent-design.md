# capture-intent 设计

## 定位

用户随口提出一个「以后要做」的需求时，capture-intent 把它立成 Agent Canvas 上的一个**需求节点**（状态 open）。它取代 capture-todo 在画布项目里的角色：需求和意图不再存成 TODO.md 里的条目，而是作为画布上的需求节点存在，后续可以从节点派生会话、走验收。

没有它，画布项目里的需求只能二选一：要么继续写 TODO.md，和画布上的需求节点割裂成两处；要么手敲 `agent-canvas-ctl create-requirement-node`，没有澄清、查重和标题约定。

与 `capture-requirement` 的分界：

| | capture-requirement | capture-intent |
|---|---|---|
| 记的是什么 | 本会话**正在实现**的需求 | 随口提出、**以后**要做的需求 |
| 何时调 | 闸门 2 定稿后，一次 | 用户提出需求时，随时 |
| 依据 | spec（`draft-requirement` 读不到 spec 就报错） | 对话中 2-3 轮澄清 |
| 关系边 | 连 `implements` | 不连 |

两者共用 `create-requirement-node` 这一个写入口，流程不共用。

## 边界

- **触发**：允许模型隐式触发，接管 capture-todo 原有的随口触发词（"以后要做 X""记一下这个需求""加到 backlog"）。
- **写到哪**：默认写当前画布；用户点名别的项目时，写到那个项目**已经打开**的画布。
- **不做**：
  - 不连关系边。agent 可用的关系里，pty→requirement 只有 `implements`，没有「会话提出了需求」这种来源关系；当前会话并没有在实现这条需求，连 `implements` 是错的。
  - 不放上画布，只建实体，和 capture-requirement 一致。
  - 不写 TODO.md，也不回退到 capture-todo。
  - 不写入未打开的画布，也不直接改 `~/.agent-canvas/*.json`（会绕过 App 生成需求编号的逻辑，还会和 App 的读写冲突）。
  - 不主动问验收标准。

代价：
- 需求只存在画布数据里，没有 git 历史，也没有能离线阅读的文件。
- 目标画布没开就记不进去，而现在的 TODO.md 随时都能写。
- 优先级从 P0–P3 四档压成 low/medium/high 三档。

## 流程

1. **判断是否适用**：`agent-canvas-ctl` 命令不存在就直接跳过。
2. **澄清需求（2-3 轮）**：沿用 capture-todo 阶段一，只问需求、不问方案，上下文里已经说清楚的直接跳过，每次只问一个问题，能给选项就给选项。
   - 需求：要解决什么问题、实现什么功能。
   - 紧急程度：默认不问，用户暗示紧急或不重要时才调整。
   - 背景：可选。
   - 验收：**不主动问**。用户描述里已经带了完成标准（"做完应该能……"），就拆出来作为 `acceptanceCriteria`。
3. **确定目标画布**：
   - 用户没点名别的项目 → 用当前画布，命令不带 `--canvas`。
   - 用户点名了别的项目 → 先拿到可用画布清单：用一个肯定不存在的路径跑 `agent-canvas-ctl --canvas <该路径> resolve-canvas`，失败时 stderr 会列出可用画布，从中按绑定路径匹配；再对匹配到的路径跑 `agent-canvas-ctl --canvas <路径> resolve-canvas`，退出码为 0 才算定下来。后续所有命令都带上同一个 `--canvas`。
   - 清单里没有这个项目 → 如实报告「该项目画布未打开」，然后停止，不改写到别的画布。
4. **查 schema**：每次都跑 `agent-canvas-ctl describe-action create_requirement_node`，从 `inputSchema` 取字段、类型、枚举和必填项，从 CLI 那条 binding 的 `usage` 与 `args.flags` 取命令写法。skill 里**不写死任何字段名、参数名和枚举值**，只写下节各字段的语义；把语义对到字段上靠的是 schema 里的字段名与 `description`。
   - 语义对不上任何字段（比如 schema 里已经没有「优先级」这一项）→ 跳过这项，并在报告里说明。
   - schema 有必填字段、下节没有对应的语义 → 停下来报告，不去猜怎么填。
   - 枚举的档数和下节写的不一样（比如优先级从三档变成五档）→ 照下节的相对位置映射过去，并在确认摘要里标出来，让用户看一眼。
5. **查重**：在目标画布上用需求的关键词跑 `search-nodes <关键词> --limit 20`，只看需求节点。有语义重叠时问用户：「发现可能重叠的需求 **[标题]**，跳过还是仍然新建？」
6. **确认摘要**：「记录为：**[画布/项目]** — [标题]，[优先级]。确认吗？」，用户确认后才写入。
7. **写入**：按第 4 步取到的 `usage` 拼出 `create-requirement-node` 命令，用户点名了别的项目时在子命令前加 `--canvas <路径>`。只传下节语义对得上的字段；状态字段不传，取缺省值；验收依据文件不传（没有 spec）。
8. **报告**：给出节点的 `requirementId`（YYMMDD-XX）和标题。写入失败时把 stderr 原样报出，不重试。

## 写法规范（写在 skill 里）

本节只写各字段的语义，不写字段名和取值；括号里是 2026-10-27 schema 中对应的字段，仅供写 skill 时参照，**不进 SKILL.md**。

- **标题**（`title`）：`<对象> <类型> <描述>`，与画布上已有的需求标题一致，例如「feed feat 实现 Creator/Channel 名册架构」「publish-skill fix 命名检查由阻断改为建议」。
  - 对象：受影响的 skill、模块或子系统名。
  - 类型：`feat` / `fix` / `refactor` / `docs` / `chore`。
  - 描述：写出关键区分点，不用「优化」「修复」这类泛词，也不堆细节。
- **需求正文**（`description`）：写做什么、为什么。**不写怎么做**。篇幅以说清楚为准。
- **优先级**（`priority`）：默认取中间档；用户表示紧急取最高档，表示不重要取最低档。
- **验收文字**（`acceptanceCriteria`）：只在第 2 步拆出了完成标准时才填，内容照用户原意写，不替用户补全。

## capture-todo 收窄为人工调用

capture-todo 会逐步退役，退役前和 capture-intent 的触发词重叠。过渡期把它收窄成只能人工调用，避免两个 skill 抢触发：

- `SKILL.md` frontmatter 加 `disable-model-invocation: true`（Claude Code 侧）。
- 新增 `agents/openai.yaml`，内容为 `policy: allow_implicit_invocation: false`（Codex 侧），写法与 `close-node`、`explain-design` 相同。
- description 去掉随口触发词，改成「Manual invocation only: `/capture-todo`」，并注明画布项目改用 capture-intent。
- 正文不改。版本号 4.5.3 → 4.6.0（触发行为改变，算 minor）。

真正的归档另走 `archive-skill`，不在本次范围内。

## 命名与登记

- 名称 `capture-intent`，对应「需求和意图」；和 `capture-requirement`（已定稿、正在实现的需求）在词义上分开。
- 路径 `skills/agent-canvas/capture-intent/`，`skills-index.json` 登记 `bundle: "agent-canvas"`、`installScope: "project"`（与同组的 skill 一致），并在 `bundleMeta.agent-canvas` 的描述里补上它。
- frontmatter：`user_invocable: true`，版本 `1.0.0`。

## 测试

- `npm test`：两个 SKILL.md 都通过格式校验，skills-index 登记正确。
- 在画布节点里实跑：用一条虚构需求走完整个流程 → 用 `get-node` 核对 title/description/priority/status 与确认摘要一致 → `purge-node --yes` 删掉测试节点。
- 查重：建测试节点前先手动建一条相似节点，确认第 5 步能发现并提问；跑完两条都 purge 掉。
- 未打开画布：点名一个画布没开的项目，确认第 3 步报告后停止，没有建出任何节点。
- capture-todo：确认 frontmatter 带 `disable-model-invocation: true`，`agents/openai.yaml` 存在。
- 不写死 schema：`grep -nE -- '--(title|description|priority|status|acceptance-criteria)|\b(low|medium|high|open|in_progress)\b' skills/agent-canvas/capture-intent/SKILL.md` 没有命中。

## 验收标准

### V1｜真实环境生效｜机器可查
标签：在画布节点里随口提一条需求，生成一个字段正确的 open 需求节点
正文：在画布节点里按流程走一次。`get-node` 返回的节点 kind 是 requirement、status 是 open，标题符合 `<对象> <类型> <描述>`，priority 与确认摘要一致，节点上没有任何关系边。

### V2｜原始问题消失｜人工裁决
标签：随口说的需求触发 capture-intent，不再触发 capture-todo
正文：用户在画布节点里用随口语气（"以后要做 X"）提一条需求，被触发的是 capture-intent；capture-todo 只有输入 `/capture-todo` 时才会运行。

### V3｜没有引出新问题｜机器可查
标签：未打开的画布不会被写入，也不会写到错误的画布上
正文：点名一个画布未打开的项目时，流程在第 3 步报告后停止，当前画布和目标项目的数据里都没有新增节点（前后各跑一次 `list-nodes` 比较）。

## 未决与风险

- **App 内置清单**：Agent Canvas 按 `builtinSkillsManifest.ts` 把同组 skill 装进画布项目，目前清单里没有 capture-intent。要在 agent-canvas 项目另立需求把它登记进去；那边发版之前，capture-todo 的收窄不能单独发布，否则画布项目里随口记需求会两头落空。
- **离线写入**：「写入未打开的画布」要在 agent-canvas 那边加能力（`ctl` 离线写入，或先排进队列、App 启动时再处理），作为一条独立需求记到 agent-canvas 项目里。那边交付后，本 skill 只需要删掉第 3 步里「未打开就停止」这条分支。
- **来源关系**：需求节点没法反查是哪个会话提出的。要补就得在 agent-canvas 的关系表里新增一个类型，第一版不做。
- **写法规范有两份**：capture-requirement 的写法来自 `draft-requirement` 的提示词，本 skill 的写法写在 SKILL.md 里，两者可能慢慢写得不一致。（推测：目前标题约定是一致的，因为都参照了画布上已有的标题；尚未对照 `draft-requirement` 的提示词核实。）
- **用户点名别的项目时的清单获取**：用不存在的路径触发 stderr 清单是借用了报错行为（2026-10-27 已实测：退出码 1，stderr 逐行列出可用画布的绑定路径）。如果 `resolve-canvas` 以后提供「列出画布」的正式命令，应该换成正式命令。

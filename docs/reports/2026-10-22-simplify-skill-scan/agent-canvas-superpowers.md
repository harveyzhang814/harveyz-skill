---
title: simplify-skill 扫描 — agent-canvas 与 superpowers-rewrite
date: 2026-10-22
standard: .claude/skills/simplify-skill/SKILL.md v0.1.2「拟定建议」7 条
scope: 只拟定建议，未执行「审批与执行」；未改仓库任何文件
---

# simplify-skill 扫描：agent-canvas 与 superpowers-rewrite

**主线：** 这两个 bundle 里最大的一块冗余在 `init-spec` 目录：约 1,490 行可视化辅助文件，`SKILL.md` 一处都没引用，却随 npm 包一起发出去。agent-canvas 七个 skill 本身已经写得紧，可删的主要有三类：`agent-canvas-control` 抄了一遍本机 `help` 已有的内容，同一条「不重试」规则在多处重复，还有几处只给维护者看、执行时用不上的说明。

**把握度标记：** 【读到】= 亲眼读到原文或命令输出；【推出】= 根据读到的内容推断；【未查】= 没核实。

**标准编号**（对应 simplify-skill「拟定建议」）：S1 识别保留项｜S2 删重复、空泛、通用教程｜S3 压成术语｜S4 渐进式披露｜S5 含糊改明确｜S6 指令与解释分开｜S7 核对保留项、标记存疑。

**行数口径：** `wc -l`。agent-canvas 的 SKILL.md 一行约 30–40 字；init-spec/SKILL.md 一段就是一行，130 行约 4,950 字，按行数比较会低估它的体量。

---

## 第一部分：agent-canvas

### 1. 总览

| skill | 当前规模（行，含引用文件） | 优化潜力 | 预估可减 | 主要问题（一句话） |
|---|---|---|---|---|
| agent-canvas-control | 261（只有 SKILL.md） | 中 | 20–30%（选做渐进式披露可再减约 25%） | `wait-reply` 一节与本机 `help wait-reply` 逐条重复；7 个示例里 3 个只是把正文规则再演示一遍；「不重试」在 4 处各写一遍 |
| describe-node | 85 | 低 | ~10% | — |
| relate-node | 64 | 低 | ~10% | — |
| capture-requirement | 60 | 中 | ~15% | 第 30 行 `--spec` 一句有歧义；两段说明加起来比规则本身还长 |
| relation-review | 139 | 中 | 20–25% | 引用了不随 skill 安装的 spec 小节号；「什么时候不要往下走」整节重复；「基线」存在哪里没写 |
| close-node | 158（+ agents/openai.yaml 2） | 中 | ~15% | 第 4 步接手方三条写得很绕；同一句告诫出现两次；「按 CLAUDE.md」指向一个在 agent-canvas 仓库里不存在的文件 |
| judge-release | 105（+ agents/openai.yaml 2） | 低 | ~5% | — |

### 2. agent-canvas 几个 skill 之间重复的共同规则

这几个 skill 分别安装，**都不能改成「见另一个 skill」**。下面几条只建议在各自文件里写短、写成一致的措辞，不建议合并。

| 共同规则 | 出现位置 | 建议 |
|---|---|---|
| 「不在画布节点里就跳过」开头段（两行，措辞完全相同） | describe-node:10-11、relate-node:10-11、capture-requirement:10-11、close-node:11-12、judge-release:11-12；agent-canvas-control:10 是另一种写法 | 保留每一份。如果要压短，五份要同步压成同一句，方便以后全局替换【读到】 |
| 「人工触发 + Codex 通过 `agents/openai.yaml` 禁止隐式调用」 | close-node:14、judge-release:14 | 执行者只需要知道「只在用户显式调用时执行」和「什么时候调」；openai.yaml 那半句是维护说明，可删。`agents/openai.yaml` 文件本身和 frontmatter 里的 `disable-model-invocation: true` 是接口，不能动【读到】 |
| handoff 接手方不调 `capture-requirement`、不建 `implements` | relate-node:57-58、capture-requirement:53-55、close-node:154 | 三处结论一致。capture-requirement 那段可以压短（见下文）【读到】 |
| `describe-node`/`relate-node` 各调两次的时机 | relate-node:37-44、describe-node:62-67、close-node:152-153；权威定义在 agent-canvas 仓库的 `AGENTS.md:245-255, 333-351` | 时机定义在**项目**的 AGENTS.md 里，不在 skill 里。close-node:152 写的是「按 CLAUDE.md」，但 agent-canvas 仓库根目录下没有 CLAUDE.md，只有 AGENTS.md【读到】 |
| `--spec` 必须传绝对路径 | describe-node:21-29（要求一律显式传）、capture-requirement:30（写法有歧义，也没要求显式传） | 两处的严格程度不一样。要不要让 capture-requirement 也改成「一律显式传」属于改行为，不在精简范围内，单列出来请用户决定【读到】 |
| 「某个节点此刻能不能调某个动作」读哪个字段 | agent-canvas-control:23, 197, 244 写 `get-node` 返回 `actions[]`（含 `available`/`reason`/`bindings`）；close-node:44 写 `availableActions / unavailableActions`；本机 `agent-canvas-ctl help get-node` 写 `availableActions` | **未确认**：可能是 `--result-format=action-v1` 和旧格式的字段名不同。离线拿不到 `get-node` 的真实输出，**两处都别改**，先去实测【读到差异，原因未查】 |

---

### 3. agent-canvas-control（中）

#### 问题归类

- **S2 与二进制 help 重复**
  - `wait-reply` 的用法、两种适用场景、前台阻塞、100 秒默认值、codex 轮询、退出码 0/1/2 和返回结构，都写在 agent-canvas-control/SKILL.md:144-155。本机 `agent-canvas-ctl help wait-reply` 里几乎逐句都有【读到】。这和 skill 自己第 14 行定的原则「不列命令清单，以二进制自己的回答为准」相矛盾。
  - 第 65-66 行列了「每次都审批」的五个命令，第 83 行紧接着又说「名单以 help 为准」。这个清单在派活前就能让 agent 预判会不会弹卡片，有决策作用，**建议保留**。
- **S2 内部重复**
  - 「不重发、不重试」写了 4 次：`failed`/`interrupted` 在 :111，`held` 在 :113，`closed-without-reply` 在 :160，往返 20 条触发 held 在 :167-168。
- **S2/S4 示例重复正文**
  - 示例 2（:188-198）重复「先查再调」一节（:17-28）。
  - 示例 4（:211-221）重复「寻址」一节（:56-59），只有 :220-221「画布外没有节点可反查」是新信息。
  - 示例 6（:236-245）重复审批规则，只有 :244「`send_message` 仅 claude-code/codex 且进程在跑才可用」是新信息。
- **S4 渐进式披露（选做）**
  - 「给其他 agent 发消息」「要对方回复」两节加示例 5–7，共约 85 行（:98-168、:223-256），只在发消息时才用得上。挪到 `references/messaging.md` 后，建节点、摆放、分组这类任务每次少加载约三分之一。
  - 代价：凡是发消息的任务都要多读一个文件，而发消息是 description 里写明的两大用途之一【推出】。是否值得由用户定。
- **S5** :25-28 一句话里同时讲了「本地作答」「零副作用」和「`list-actions` 与 `get-node` 的分工」，建议拆成两句。

#### 代表性修改

**① wait-reply 一节（:144-155）**

修改前（节选）：
> `wait-reply <messageId>[,<messageId>…] [--all | --any] [--timeout <秒>]`：
> - 只能等你自己发出、带了 `--expect-reply` 的消息；默认 `--all` 等全部，`--any` 任一到达即返回。
> - 只能**前台阻塞**调用：不要包 sleep、不要放后台。……
> - 默认最多等 100 秒，……codex 的命令工具会在命令结束前先返回 session id：继续轮询**同一个会话**直到出现退出码，不要重新发起命令。
> - 退出码 0：stdout 是 `{timedOut: false, results: [...]}`。……
> - 退出码 2：超时，还没等到。agent 调用方**不要接着再等一次**……退出码 1：失败。
> - 被等的消息被拒、失败、中断、撤回或无回复关闭时，立即返回该状态……

修改后：
> 参数、返回结构、退出码见 `agent-canvas-ctl help wait-reply`。必须遵守：只能前台阻塞调用（不包 sleep、不放后台；codex 继续轮询同一会话直到出现退出码，不重新发起）；退出码 2（超时）时，agent 调用方结束本轮、不再接着等，shell 调用方稍后再领取。

理由：符合 S2 和 skill 自己第 14 行的原则。需要决策的两条（前台阻塞、超时后结束本轮）留在正文里。可减约 8 行。
**未确认**：老版本 App 的 help 是否也有这些内容。我只核对了本机二进制。

**② 「不重试」四处合成一条（放在「给其他 agent 发消息」一节，删掉 :111、:113、:160 末句、:167-168 末句里的重复部分）**

修改后：
> **都不自动重发，也不要自行重试：**`held`（往返过密，或同一条链里要求回复的消息累计 20 条）等用户在卡片上放行或终止，agent 解不了；`failed` 时文字可能已经写进去了，先看对方节点；`interrupted`、`closed-without-reply`（`user-takeover`/`turn-aborted`/`terminated`）告诉用户，要不要再发由用户决定。

理由：S2。原来的四种状态名、20 条上限、三种关闭原因全部保留，只去掉重复的「不要重试」。

**③ 删示例 2 和示例 6，示例 4 只留命令块**

把 :220-221「画布外的进程不是任何画布节点，`whoami` 这类命令在这里没有节点可反查」挪进「寻址」一节末尾；把 :244「`send_message` 只有 claude-code/codex 且进程在跑才 `available: true`」挪进「给其他 agent 发消息」开头。理由：S2，其余内容正文里已经讲过。可减约 22 行。

#### 必须保留、不能动的语义

- 第 10 行的跳过条件；`--canvas` 必须写在子命令前；探测时要带同样的 `--canvas`；探不到就如实告诉用户，不要改去操作别的画布。
- 每次都审批的五个命令；`delete-node`/`purge-node` 必须带 `--yes`；最多等 90 秒；两条报错原文；被拒绝不重试、等待期间不重发。
- 安全一节全部保留：没有 dry-run；不为探测去跑写操作；不发测试消息；测试子进程不要继承 `AGENT_CANVAS_MCP_URL` 和 token。
- 信封头格式字符串 `[agent-canvas 消息 …]`、`[agent-canvas 回复 …]`，以及正文里转义的 `\[agent-canvas`；30 条/分钟、50 条待投、32KB 上限，以及用 `--file`/`--file -` 传长正文（本机 `help send` 里**没有**这三个上限，必须留在 skill 里）【读到】。
- 默认做法是「发完就结束本轮，回复会推回来」；收件方用 `reply`、写最后一条回复的规则。
- 批量命令退出码 2 表示部分生效；`create-pty-node` 退出码 2 表示节点可能已经建出来了，先核对，别再建一个；分组要先 `put` 才能 `group-add`；新建的节点默认不在画布上；`put --position` 只接受单个 id。
- 「相关 skill」一节点名 describe-node、relate-node、capture-requirement、close-node，这是跨 skill 接口。

#### 拿不准的地方

- **未确认**：`get-node` 的 `actions[]` 和 `availableActions` 是什么关系（见第 2 节表格）。
- **未确认**：「相关 skill」一节没提 judge-release 和 relation-review。我推测是有意的：前者由横幅拉起，后者只给 Pilot 用。但没核实。

---

### 4. capture-requirement（中）

#### 问题归类

- **S5 歧义**：capture-requirement:30「`--spec` 不传时按本会话记录自动发现，必须是绝对路径」。这句话读起来像是「自动发现的路径必须是绝对路径」，实际意思应该是「传 `--spec` 时必须是绝对路径」【读到原文；本意是推断】。
- **S6 解释比规则长**：
  - :49-51 解释为什么只在闸门 2 调，写了 3 行。
  - :53-55 解释 handoff 接手方为什么不调，写了 3 行，其中「不调纯粹是约定，不是系统会替你挡住」这层意思表达了两遍。
- **S6 维护者注释**：:13 标题后缀「（三步，每步一个既有/新增的单一能力命令）」对执行没有作用。
- **S7 外部引用**：:39「按 AGENTS.md 4.2」指的是 agent-canvas 仓库 `AGENTS.md:224`。skill 装到别的项目以后，这个引用就落空了【读到】。

#### 代表性修改

**① :30**

修改前：
> 第 1 步**只撰写、不落盘**——`--spec` 不传时按本会话记录自动发现，必须是绝对路径。

修改后：
> 第 1 步**只撰写、不落盘**。传 `--spec` 时必须是绝对路径；不传时按本会话记录自动发现。

理由：S5，消除歧义，行为不变。

**② :49-55 合并**

修改后：
> **只在闸门 2 定稿后调一次**，收尾时不调：到收尾时上下文已经被实现细节占满，重写出来的需求会偏向实现叙述。本节点已 implements 某个需求节点时，第 1 步会直接拒绝。
>
> handoff：交出方在闸门 2 调；接手方**不调**。第 1 步只检查本节点自己的 implements 边，拦不住接手方重复调用，只能靠这条约定。

理由：S6，保留了两条规则和「系统拦不住」这个关键事实。可减约 3 行。

**③ :39「按 AGENTS.md 4.2，spec 里本应有这一节」→「spec 本应有 `## 验收标准` 一节」**

理由：S7，去掉项目外的引用，规则本身不变。**未确认**：用户是否希望保留这个出处，方便维护。

#### 必须保留

- 三步的顺序和全部旗标：`draft-requirement [--spec]` → `create-requirement-node --title/--description/--priority/--status/[--acceptance-criteria]/--acceptance-spec` → `link-nodes --type implements`，以及每一步返回的字段名。
- 第 1 步报错时不重试、不跳过；第 2 步因 `--acceptance-spec` 报错时**不准去掉旗标重试**；stderr 出现两类警告时要如实报告。
- 第 3 步失败就立刻 `purge-node <nodeId> --yes`。
- 与 describe-node 划清边界那一段。

#### 拿不准的地方

- **未确认**：要不要把「有 spec 一律显式传 `--spec`」（describe-node 的做法）也加到这里。`draft-requirement` 的自动发现很可能有和 summarize-self 一样的落空风险，但这是行为变更，超出精简范围。

---

### 5. relation-review（中）

#### 问题归类

- **S6/S7 外部引用**：:23「spec §5.1」、:40「§1.3」、:105「§5.4」、:126「§9.1」。执行者手里没有这份 spec。根据关键词 `WAKE_N` 推断，它是 agent-canvas 仓库的 `docs/superpowers/specs/2026-09-08-relation-self-governance-design.md`【推出；小节号没核对】。
- **S2 整节重复**：「什么时候不要往下走」（:135-139）三条分别重复 :21-23、:46-49、:10-11。唯一的新信息是 :138「不进关卡三」。
- **S6 解释过长**：:61-64 用 4 行解释为什么读不到 `despite`，执行时只需要一句「别找它」。
- **S6 会过期的数字**：:70「现有 7 个 type 里已有 4 个只有这个消费点」，type 数量会随升格变化【推出】。
- **S5 含糊**：:21「相比上次记录的基线」「只记下这次的数量」，没写记在哪里。cron 每次运行如果是新会话，就读不到上次的基线【推出】。
- **S4（选做）**：「第四步之后」的合并、废弃、改名、回滚（:101-127，约 27 行）只在顺带发现问题时才用，可以挪到 `references/governance-actions.md`。这个 skill 只由 cron 触发，省下的加载有限，收益偏低【推出】。

#### 代表性修改

**① :61-64**

修改前：
> 每条候选自带的 `why` 字段（agent 走 `link-nodes` 逃逸阀建这条关系时就已经写明"为什么现有 type 装不下"）是关卡三最直接的原料，优先核对这些——**不是 `despite`**：`despite` 只在写入那一刻用于校验"逐个点名已排除的现有 type"，校验完就丢弃，不落在 Relation 记录上、`relation_review_queue` 也不会把它吐出来，审议阶段读不到。

修改后：
> 优先核对每条候选自带的 `why`（建关系时写明的「为什么现有 type 装不下」）。`despite` 只在写入时校验，不进 `relation_review_queue` 的返回，审议时读不到，不要找它。

理由：S6。可减约 2 行。

**② 删除 :135-139，把「不进关卡三」并进 :49**

修改后（:49）：
> 不满足就打回，不进关卡三；附上当前累计数量和涉及的节点数……

理由：S2。

**③ spec 小节号**

把「（spec §5.1）」这类括注删掉，或者换成完整路径加小节号。两种做法都不影响执行，取决于维护者需不需要出处。**未确认**，请用户选。

#### 必须保留

- 第 10 行的适用条件；`WAKE_N = 5`、`PROMOTE_N = 3`、来自 ≥2 个不同 `fromNodeId`。
- 四道关卡的判据，以及「打回时必须写明是哪一关」「必须引用真实 `relationId`」「字段写不满就是没过」。
- Pilot 工具名和参数结构：`relation_review_queue`（返回裸数组或 `{items, skipped}`）、`relation_promote{name, reading, endpoints, evidence, gateReasoning}`，以及 `relation_merge`、`relation_deprecate`、`relation_rename`、`relation_revert` 的参数和返回值。
- CLI 接口：`agent-canvas-ctl relation-guide`、`update-relation <relationId> --type`（只写进报告，不自己批量执行）。
- 升格整次拒绝的四种情形，以及被拒后要重新取队列、重新筛、重新核关卡二。
- `codePinned` 的 type 会被硬拒绝；`rename` 要求 `to` 已经存在；`revert` 只在有人明确要求时用；「不要为了做点什么而勉强套用」。
- 第五步报告要列的字段。

#### 拿不准的地方

- **未确认**：基线计数到底存在哪里。可能由 cron 任务自己的记忆承载，也可能有 Pilot 侧的存储。skill 没写，不应该替它编一个位置，只建议把这一点标成待补。
- **未确认**：Pilot 工具 `relation_review_queue` 和 CLI 命令 `relation-review-queue` 是不是同一能力的两个入口。skill 只用 Pilot 工具，保持现状。

---

### 6. close-node（中）

#### 问题归类

- **S5/S6 写得绕**：第 4 步接手方的三条（:71-73）混写了宿主适配、Claude Code 示例和失败分支，读三遍才能理清「停在哪」。
- **S2 重复**：
  - 「把没合并的分支连同节点一起关掉，等于把工作弄丢了」出现了两次（:81-82、:116-117）。
  - 「如实报告：需求状态维持 X，因为 Y」也出现了两次（:58-59、:60）。
- **S6 维护者注释**：:14 的 openai.yaml 那半句。
- **S7 失效引用**：:152「按 CLAUDE.md」。agent-canvas 仓库根目录下没有 CLAUDE.md，两次调用的时机写在 `AGENTS.md:333-351`【读到】。harveyz-skill 的 CLAUDE.md 里也没有这条规则【读到】。

#### 代表性修改

**① :71-73**

修改前：
> - **不合并、不 `git worktree remove`。** 先检查当前宿主是否提供且可核对为"保留 worktree 并离开/解除当前会话绑定"的可靠能力。
> - Claude Code 适配示例：使用 `ExitWorktree(action: "keep")`；它必须保留 worktree，不是合并或清理动作。其他宿主只使用实际提供且已核对语义的能力，不杜撰 API。
> - 若无安全解除绑定能力，报告 `nodeId`、分支、worktree 绝对路径与需人工解除绑定的事实，停在第 4 步。单次 shell `cd` 不能解除会话绑定；不得继续执行 `hide` 或 `stop-node`，也不得进入第 6/7 步。

修改后：
> - **不合并、不 `git worktree remove`。**
> - 用宿主提供的「保留 worktree 并离开」能力解除会话绑定：Claude Code 用 `ExitWorktree(action: "keep")`；其他宿主只用实际提供、而且已经核对过语义的能力，不杜撰 API。
> - 没有这种能力时（单次 shell `cd` 不算）：报告 `nodeId`、分支、worktree 绝对路径，并说明需要人工解除绑定；停在第 4 步，不执行 `hide`/`stop-node`，不进第 6/7 步。

理由：S5。条件、动作、停点三者分开。可减约 1 行，主要收益是好读。

**② :58-60 合并**

修改后：
> - 想要的命令不在 `availableActions` 里，或者拿不准该推到哪一步：不改，如实报告「需求状态维持 X，因为 Y」（Y 取 `unavailableActions` 给的原因，或者你的疑点）。改错比不改更难发现。

理由：S2。

**③ :152「那两个的第二次调用仍按 CLAUDE.md 由你自己在收尾前调」→「那两个的第二次调用由你自己在收尾前调」**

理由：S7，去掉失效引用，规则本身就在这句里。**未确认**：作者是否把 AGENTS.md 和 CLAUDE.md 当成同一个东西（有的宿主会把 AGENTS.md 软链成 CLAUDE.md）。

#### 必须保留

- 角色判定表；frontmatter 字段 `source_node`/`target_node`/`status`，取值 `待验收`/`已验收`；交接文档目录 `docs/commute/`。
- `submit-requirement --commit <40 位 sha>`；实现方不推到 `done`；`defer-requirement`；没有 `implements` 边就跳过，不顺手立项。
- 交出方：没到 `已验收` 就停；没合并就停；合并由 `/handoff` accept 阶段跑 `scripts/merge-to-staging.sh`，本 skill 不代跑。
- 第 5 步的分支判定：没有 `staging`、detached HEAD、在 `main` 上 → 停；在 `staging` 上 → 跳过；`git merge-base --is-ancestor HEAD staging`；脚本不存在就停，不换别的合并手法；判断是否 linked worktree 的 `git_dir`/`git_common_dir` 比较；不加 `--force`。
- 第 6 步必须把话说完；第 7 步检查子代理；先 `hide` 再 `stop-node`，顺序不能反。
- 「只有交出方能合并、能 `git worktree remove`」；不代跑 describe-node/relate-node；不调 capture-requirement；不动 `implements` 边。
- `availableActions`/`unavailableActions` 这两个字段名（见第 2 节，未确认，先不动）。

#### 拿不准的地方

- **未确认**：:14「用户必须以 `$close-node` 显式调用」，`$` 是 Codex 的写法，Claude Code 里是 `/close-node`。改不改写法属于触发方式的表述，不在精简范围内，只标出来。

---

### 7. 潜力低的 skill

- **describe-node（低，~10%）**：唯一值得动的是 `--spec` 一段（:21-28）。既然规则已经是「一律显式传」，自动发现的机制（Write > Edit > Read 的优先顺序、主进程 cwd、实测落空）对决策没有作用，可以压成两句：「有 spec 一律传绝对路径；返回 `specUsed` 为 null 就补传重跑」。其余内容都是返回状态的处理规则，要保留。
- **relate-node（低，~10%）**：「什么时候不要调」（:60-64）与第 2 步（:29「配不上就跳过」）、:55（已有就跳过）重复。另有一处 S5：:33 把 `--despite` 写在方括号里，看起来是可选的，但本机 `help link-nodes` 写明「端点对已有合法 type 时必须传，漏一个即拒」【读到】，而 :31-32 说的正是这种情况，建议去掉方括号并注明必填。这是澄清写法，不改行为。
- **judge-release（低，~5%）**：结构紧凑。「边界」一节的 :102-104 三条重复了 :87、:63、:29，可删；:14 的 openai.yaml 半句同 close-node。其余都是必要的接口：`--result-format=action-v1` 必须写在 `get-node` 前、`record-requirement-verdict` 的旗标、运行提交和交付提交的区别。

---

## 第二部分：superpowers-rewrite

### 1. 总览

| skill | 当前规模（行，含引用文件） | 优化潜力 | 预估可减 | 主要问题（一句话） |
|---|---|---|---|---|
| init-spec | 1,859（SKILL.md 130 ≈ 4,950 字；builder-check-prompt.md 15；visual-companion.md 293；scripts/ 1,400；LICENSE 21） | 高 | 按包算约 80%；SKILL.md 本身 10–15% | `visual-companion.md` 和 `scripts/` 没被 SKILL.md 引用，执行时根本读不到，却随 npm 包发布；SKILL.md 里「人工复核」写了两遍，「可视化辅助」夹着通用作图建议 |
| develop-plan | 187（SKILL.md 166；LICENSE 21） | 中 | 10–15% | 「用签名和测试代替函数体」写了 4 遍；两个保存位置可以合并；:155 写「无」写在哪里不清楚；:54 一段塞了 5 条规则 |

### 2. init-spec（高）

#### 问题归类

- **S4/S2 孤立文件（最大一项）**：
  - init-spec/SKILL.md 全文没提到 `visual-companion.md`，也没提到 `scripts/`【读到，grep 仓库只命中这些文件自己互相引用】。
  - 历史：原版 brainstorming 的 SKILL.md 有「If they accept, read `visual-companion.md`」（commit b68d257 导入的原文第 224 行附近）。改名为 init-spec 的 commit 61a9e74 把这一步换成了 `sync-design`（现在的 :87）【读到】。
  - 后果：这约 1,490 行（visual-companion 293 + scripts 1,400，约 56KB）在当前流程里永远不会被加载，但 package.json:77 把整个目录打进了 npm 包【读到】。
  - 这些脚本还会往 `.superpowers/brainstorm/` 写文件，这是原版 superpowers 的路径，与本 skill 的 `.hskill/spec/` 约定不一致【读到】。
- **S2 重复**：
  - :102「写作前确认决定记录已通过上述人工复核」重复 :89「写前复核」。
  - :104 末句「标明版本、审查状态、已批准范围及未决事项」与 :122「批准后同步」有部分重叠。
- **S2/S3 通用内容**：:110「可视化辅助」列了一串图的种类（架构、组件、数据流、时序、状态、关键流程），属于通用作图常识。
- **S5/S6 一句多规则**：
  - :32「对话方式」一句话里放了 6 条规则：何时切换、共用标准、只问什么、沿用用户词汇、末尾只问一个、不用流程术语。
  - :85「方案形成标准」同样。
  - simplify-skill 第 5 条只反对「一句话能说清却拆成几句」，没要求把多条规则塞进一句。这里建议改成列表：字数基本不变，但每条规则可以单独核对。
- 其余部分基本是本 skill 特有的条件和边界，S1 判定为保留。

#### 代表性修改

**① 孤立文件**

修改前：`init-spec/` 下有 `visual-companion.md` 和 `scripts/{server.cjs, helper.js, frame-template.html, start-server.sh, stop-server.sh}`，SKILL.md 不引用它们。

修改后（两条路，请用户选）：
- A. 删除 `visual-companion.md` 和 `scripts/`。
- B. 如果还打算用浏览器辅助，在 :87「前端设计稿审查」里补一句加载条件，例如「用户同意用浏览器展示选项时读 `visual-companion.md`」，并把脚本的输出目录改成符合本仓库的约定。

理由：S4/S2。按当前 SKILL.md，A 不改变任何行为（文件本来就到不了）【推出】，还能让 npm 包少 56KB。B 是加功能，超出精简范围。
**未确认**：当初是有意留作备用，还是改写时漏删了。`docs/reports/2026-10-17-brainstorming-rewrite-analysis.md:15, :47` 还把它列为保留文件【读到】，说明至少分析阶段打算保留。

**② :102**

修改前：
> 写作前确认决定记录已通过上述人工复核，核实方案依赖的现状，缺乏依据时补查；若结果改变获批决定，更新决定记录并重新送审。

修改后：
> 写作前核实方案依赖的现状，缺乏依据时补查；结果改变获批决定时，更新决定记录并重新送审。

理由：S2。:89 已经规定「明确批准后……再写 Spec」，这里不必再确认一次。

**③ :110**

修改前：
> 图示有助于人或 Agent 理解、审查 Spec 时，在相关内容旁嵌入 UML 或其他技术图示，呈现架构、组件、数据流、时序、状态或关键流程；文字足够清楚时无需绘制。图示须标明关键元素、关系、条件和异常路径，与正文一致，优先使用 Mermaid 等可随 Spec 维护的文本图示；图示不代替关键决定的文字说明。

修改后：
> 图示有助于审查时，在相关内容旁嵌入可随 Spec 维护的文本图示（如 Mermaid），标明关键元素、关系、条件和异常路径，并与正文一致；图示不代替关键决定的文字说明。

理由：S2/S3，去掉通用的图种类清单，保留本 skill 特有的约束。

#### 必须保留

- 两份文档的分工；决定记录「按决定组织、不是审计日志」。
- 第一条消息先判定是探索性还是定义性、不问用户归类、问完就停；六项共同澄清；结束条件里「用户说够了也不能代替确认」；查看项目外个人文件前要征得同意；200–300 词的阶段性复述。
- 决定条目的字段；三种来源的定义，以及「用户批准不改变来源」；五种状态名「已提出、待审、已批准、已否定、已失效」；否定与修订单独成一部分、保留原编号、新决定另建编号。
- 路径约定（跨 skill 接口，develop-plan 依赖它）：`.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-record.md`、同目录的 `-spec.md`；日期取首次建档日；同名时加序号。
- 两道人工闸门；方案至少两种、只有一种时说明其他路径为什么被排除；调用 `sync-design` 设计模式（跨 skill 接口），设计稿不等于获批。
- `builder-check-prompt.md` 的引用和三类缺口；无子代理工具时自查。
- `<HARD-GATE>` 全文，包括两个例外、调用 `develop-plan` 时传 Spec 路径/版本/范围、计划文件名 `YYYY-MM-DD-<topic>-plan.md`、「此处不得调用其他技能」。

#### 拿不准的地方

- **未确认**：孤立文件的去留（见①）。
- **跨 bundle 观察【推出】**：init-spec 把 Spec 存在 `.hskill/spec/…`，而 describe-node 的自动发现只认 `docs/superpowers/specs/`（describe-node:25；agent-canvas `AGENTS.md:232`）。在画布节点里用 init-spec 时必须显式传 `--spec`。describe-node 已经要求一律显式传，所以现在不出问题，不需要改，只是记一笔。

---

### 3. develop-plan（中）

#### 问题归类

- **S2 重复**：「用签名和测试代替函数体」出现了 4 次：:137「仅当……才写实现片段」、:141 后半句、:149「删除……不必要的函数体」、:157「用签名、测试名称和断言替代实现代码」。
- **S2 两个保存位置写重了**：:49 和 :50 两条都写了一遍同一个路径模板和「修订沿用原路径」。
- **S5 含糊**：:155「没有遗漏时明确写『无』」，没说「无」写在哪里，可能是 `## Review Focus` 一节，也可能是自查结论【读到原文；指向是推断】。
- **S5/S6 一段多规则**：:54 一段里放了 5 条规则：开头字段怎么取舍、全局约束按确切取值逐项写、Review Focus 最多五项、对应测试归哪个任务、越过决定边界怎么办。
- 「作用」和「开始时声明」都很短，按 S1 保留。

#### 代表性修改

**① :49-50 合并**

修改前：
> - 接续 `init-spec`：与 Spec 同目录；默认路径为 `.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-plan.md`，日期、topic 及同名序号沿用 Spec，修订沿用原路径。用户另有命名约定时遵循其约定。
> - 独立调用：直接保存到项目根目录下的 `.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-plan.md`；日期取首次建档日，topic 根据任务命名，独立任务同名时加序号，修订沿用原路径。

修改后：
> 默认 `.hskill/spec/YYYY-MM-DD-<topic>/YYYY-MM-DD-<topic>-plan.md`（项目根目录下），修订沿用原路径。
> - 接续 `init-spec`：与 Spec 同目录，日期、topic 和同名序号沿用 Spec；用户另有命名约定时遵循其约定。
> - 独立调用：日期取首次建档日，topic 按任务命名，同名时加序号。

理由：S2。路径模板只写一次。**未确认**：「用户另有命名约定时遵循」原文只出现在接续分支里，我保持了这个不对称，没有扩到独立调用，以免改变行为。

**② :141、:149 删掉重复的半句**

- :141「删除未作决定的占位语，如『TBD』『处理边界情况』；用签名和测试代替可由实施者写出的函数体。」→「删除未作决定的占位语，如『TBD』『处理边界情况』。」
- :149「删除空话及不必要的函数体。」→「删除空话。」

理由：S2。函数体规则保留在 :137（写法）和 :157（自查），两处足够。

**③ :155**

修改前：
> 所列风险是否各有归属任务和测试？没有遗漏时明确写"无"，并检查新增行为是否越过决定边界。

修改后（按我的推断，请确认）：
> 所列风险是否各有归属任务和测试？`## Review Focus` 没有可列项时，该节写「无」；新增的预期行为越过决定边界时，按第 1 步处理。

理由：S5。**未确认**：「无」到底写在哪里。

#### 必须保留

- 开始时的声明原句。
- 两种输入的分支；越过决定边界时，接续 init-spec 就返回它的审查阶段，独立调用就请用户澄清。
- 工作区规则和 `superpowers:using-git-worktrees`（跨 skill 接口）。
- 文档开头的英文字段名（`Goal`、`Architecture`、`Tech Stack`、`Spec`、`Spec Version and Scope`、`Requirements`、`## Global Constraints`、`## Review Focus`），以及两种调用下各删哪些字段；Review Focus 最多五项。
- 模板里的 `> **For agentic workers:** REQUIRED SUB-SKILL: …` 一行；任务标题保留 `Task N`（执行类 skill 靠它提取任务）；用 `- [ ]` 跟踪；每个任务最后的 `Run` 覆盖本任务全部测试。
- 自查 6 项；执行交接时请用户确认、两种执行方式各自的代价；`superpowers:subagent-driven-development` / `superpowers:executing-plans`（跨 skill 接口）。
- 保存路径与 init-spec 的 HARD-GATE（init-spec:129）保持一致。

#### 拿不准的地方

- **未确认**：:54 改成列表后行数会增加约 4 行，抵消一部分删减。要不要拆，取决于用户看重好读还是篇幅。
- **顺带（不属于精简）**：frontmatter `version: 0.1.11` 没加引号，仓库 CLAUDE.md 的格式示例是 `version: "x.x.x"`。`npm test` 是否校验这一点【未查】。

---

## 附：本次扫描读过的材料

- 标准：`.claude/skills/simplify-skill/SKILL.md`
- 扫描目标：`skills/agent-canvas/*/SKILL.md`、`skills/agent-canvas/{close-node,judge-release}/agents/openai.yaml`、`skills/superpowers-rewrite/init-spec/{SKILL.md, builder-check-prompt.md, visual-companion.md}`、`skills/superpowers-rewrite/develop-plan/SKILL.md`；`init-spec/scripts/` 只核对了引用关系和输出路径，没有逐行审代码。
- 旁证：本机 `agent-canvas-ctl help`、`help send|wait-reply|summarize-self|get-node|draft-requirement|relation-guide|link-nodes`、`describe-action get_node`（都在本地作答，零副作用）；`~/Projects/agent-canvas/AGENTS.md:224-255`；harveyz-skill 的 git 历史（61a9e74、b68d257）和 `package.json:69-78`。

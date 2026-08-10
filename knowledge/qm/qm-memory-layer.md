# QM 记忆层深入分析

> 关联文档：
> - [[qm-overview]]（QM 项目整体调研：产品目标、哲学与功能模块分解）
> - [[qm-execution-layer]]（执行环境层深入分析——记忆之外，agent 状态的另一个家）
> - [[qm-skills-layer]]（技能层深入分析——同样遵循「索引进 prompt，正文按需读」的成本模型）
> - [[qm-resolution-layer]]（解析层深入分析——本篇依赖的 `resolution.layers` 由它算出）
>
> 调研对象：`yc-software/qm` 的 `src/memory/`
> 本地路径：`~/Repositories/qm`
> 调研时间：2026-08-09
> 仓库版本：`main` @ `0f0e0ad`
>
> 阅读范围：`src/memory/` 六个文件 + 三个策略（共 1247 行），以及它在 `core/orchestrator.ts`、
> `tools/primitives.ts`、`harness/pi-tools.ts`、`api/routes/surface.ts`、`api/routes/admin/memory.ts`、
> `skills-seed/memory/SKILL.md`、`config.ts` 的全部接入点

**总体印象：这是整个 qm 里判断密度最高的一块——很小的代码量，很多的判断。**

---

## 一、数据模型：记忆就是一个 Markdown 文件

```markdown
# Memory

- (2026-07-14) Prefers terse replies
- (2026-07-20) Owns the billing service
- (2026-08-01) Working on the Q3 launch (said in #project-atlas)

<!-- consolidated: 2026-08-05 -->
```

路径 `memory/MEMORY.md`（`memory-service.ts:6`），**每个 scope 一份**。没有向量库，没有 embedding，没有图谱。

两个硬上限定义了整个系统的赌注：

| 常量 | 值 | 位置 | 含义 |
|---|---|---|---|
| `MAX_FACTS` | 300 | `memory-service.ts:8` | 一个笔记本最多 300 条 bullet，超了从**最老的**砍 |
| `RECALL_MAX_CHARS` | 6000 | `notebook.ts:1` | 每轮注入 prompt 的上限，取**尾部**（`capTail`） |

赌注是：**一个人或一个房间真正耐用的事实，几百条 bullet 装得下**。这个假设成立，整套设计就成立；不成立，就得换检索架构。

检索也同样朴素——`queryBullets`（`memory-service.ts:94`）是**大小写不敏感的全词子串 AND 匹配**。`skills-seed/memory/SKILL.md` 诚实地把这个限制告诉了 agent：

> Matching is substring-based (all terms must match), so prefer distinctive terms (a name, a project) over sentences.

`notebook.ts` 37 行就是全部的行语法：`isBullet` / `bulletText` / `captureDate` / `bullets` / `normalize` / `dateStr` / `capTail`。AGENTS.md 把它列为「helper 的家庭住址」之一（memory line grammar），意思是所有涉及记忆行格式的代码都必须走这里。

---

## 二、存储层：两个实现，一个接口

`MemoryService`（`memory-service.ts:28`）有 5 个必需方法 + 6 个可选方法。可选的那半边是**能力探测点**——不同后端支持程度不同。

```ts
// 必需
recall / capture / query / read / replace
// 可选
readHead / replaceIfRevision / history / restore / updatedAt / metadata
```

### 2.1 文件版 `createMemoryService`

落在 `WorkspaceStore` 上。revision = `sha256(content)`，乐观并发靠内容哈希比对。没有 history / restore。

### 2.2 Postgres 版 `createPostgresMemoryService`

生产形态，三个关键决策：

**（1）Append-only 修订链，不是可变行**

```sql
CREATE TABLE memory_revisions(
  id BIGSERIAL PRIMARY KEY,
  scope_id TEXT, seq BIGINT, op TEXT,
  body TEXT,          -- 每次存【整篇】笔记本
  author TEXT, at BIGINT,
  UNIQUE (scope_id, seq)
)
```

body 是**全量快照**而非 diff。用存储空间换「简单 + 天然可回滚」。所以 `history()` 和 `restore()` 是白送的。

**（2）Per-scope 咨询锁串行化**

```sql
SELECT pg_advisory_xact_lock(hashtext('memory'), hashtext($1))
```

（`postgres-memory-service.ts:45,80`）不锁表，按 scope 粒度在事务内排队。多实例并发写同一个人的记忆是安全的。

**（3）乐观并发 = seq 比对**

`replaceIfRevision(scope, content, expectedSeq)` 在锁内校验 head seq，不匹配就 `ROLLBACK` 返回 false。Web 端两个标签页同时编辑记忆，后提交的会被拒绝而不是静默覆盖。

> **不对称之处**：文件版的 `replaceIfRevision`（`memory-service.ts:143`）是**读-比-写，无锁**，两个并发调用可能都通过哈希校验。生产走 Postgres 所以无实害，但本地 / 内存形态存在 TOCTOU 窗口。

---

## 三、一条事实的完整生命周期

```
用户说话
   |
   v
[turn 执行]  <-- recall: 把 notebook 注入 "## What you remember"
   |
   v
turn 结束（异步，不阻塞回复）
   |
   v
[BurstBuffer]  攒 180s 静默期 或 10 轮，凑成一个 burst
   |
   v
[extractFacts]  一次 LLM oneShot，输出 `- fact` 列表 或 NONE
   |
   +--> capture 到 conversation 自己的 notebook
   |
   +--> ccCaptureToPersonal：如果是频道/群，抄送一份到发言人的个人 notebook
   |                        并打上 `(said in #channel)` 标签
   v
[foldCapture]  净化 -> 去重 -> 追加 -> 超 300 条砍最老的
   |
   v
累计 10 条后触发 [consolidation]  <-- LLM 输出 UPDATE/DELETE/ADD 动作脚本
```

### 3.1 Recall —— 注入哪些笔记本

`policy.ts` 定义三档：

| `MEMORY_RECALL` | 行为 |
|---|---|
| `off` | 不注入 |
| `writable` | 只注入自己能写的那一份 |
| `visible`（默认） | 注入 writable + **所有 workspace layer 的 scope**（个人 / 频道 / org），去重 |

> **补正**（来自 [[qm-resolution-layer]]）：这里的「所有 workspace layer 的 scope」是一个恒定结构——`[org, 当前会话 scope]`，**DM 时**再加上说话人的每个 team。频道会话里不挂 team 层，所以**频道里读不到团队记忆**。

多份时每份加 `### <scopeId>` 标题（`orchestrator.ts:769`）。然后在 `orchestrator.ts:874` 拼成 prompt block：

> ## What you remember
> You're in **#project-atlas**. A memory tagged `(said in …)` was stated in another context — apply it only if that tag matches here; untagged memories are general.

注意这块被插在 `stableSystemBytes` 记录**之后**——有意放在 prompt cache 稳定区的**外面**，因为记忆每轮都可能变。

### 3.2 Capture —— 异步、串行、失败不影响回复

`orchestrator.ts:2591` 起：

- `pausing`（等待人工审批）时**不**捕获
- 用 `pendingCaptures` Map 按 `memoryScopeId` 串成链：新的 capture 先 `await` 前一个
- 异常进 error sink（`category: "memory", code: "capture_failed"`），耗时进 metrics（`status: "capture", captureMs`）
- 整体是 fire-and-forget，回复早就发出去了

### 3.3 BurstBuffer —— 为什么不是每轮抽一次

`per-turn.ts:85`。默认静默期 **180 秒**（`DEFAULT_CAPTURE_QUIET_MS`），上限 **10 轮**（`DEFAULT_CAPTURE_MAX_TURNS`）。key 是 `scopeId + conversationScopeId + actorId + autonomous` 四元组。

动机是双重的：**省一大笔 oneShot 调用**，同时**抽取质量更高**——把连续几轮当一段完整交流看，模型才分得清什么是「这次任务的临时状态」、什么是「这个人一贯如此」。

细节：`timer.unref?.()`（`per-turn.ts:120`）——不阻止进程退出。

---

## 四、两段 Prompt 才是这层的真正核心

代码是骨架，`MEMORY_EXTRACTION_PROMPT` 和 `MEMORY_CONSOLIDATION_PROMPT` 是肌肉。它们绝大部分篇幅在讲**不要记什么**。

### 4.1 抽取 prompt 里的三条硬约束

**（a）PROVENANCE：偏好只能来自本人的原话**（`per-turn.ts:16-20`）

> 一个偏好、意图或指令，只有当**用户自己的消息**在这些交流中陈述了它，才是有效事实。**永远不要从 assistant 的回复中推导** —— assistant 说「按 X 的偏好」或描述自己的策略（「静默排队以避免刷屏」）**不是**任何人持有该偏好的证据。同样排除关于未发言者的二手转述。

这条防的是**自指污染闭环**：模型编了一句「我按你的偏好静默处理了」→ 被抽取成「用户偏好静默处理」→ 下一轮 recall 读回来 → 模型更加确信。没有这条约束，agent 会在几十轮内给自己造出一整套虚构人格档案。

**（b）自主轮不许产出关于人的事实**（`per-turn.ts:30`，`AUTONOMOUS_EXTRACTION_ADDENDUM`）

> 这些是 AUTONOMOUS 轮：没有人说话。"User said" 的内容是系统或 bot 触发，回复是 assistant 独自工作。只记录操作性事实（状态、阻塞、队列、结果）。不要输出任何关于任何人的偏好 / 意图 / 指令事实；如果只有这类，输出 NONE。

同一逻辑的延伸：cron 半夜跑一轮，房间里没有人类，那么任何「偏好」都只可能是模型自己编的。

**（c）机制不记，约定要记**（`per-turn.ts:22-26`）

> 排除你需要时可以查到的系统机制：API endpoint / header、凭证与 broker 管道、状态文件路径、工具调用细节、schema。对于用户依赖的常驻系统（一个 cron、一个 watcher、一个集成），把它的**存在和用途**记成一条事实——不要记它的内部。用户陈述的约定（「永远走 broker，不要裸 token」）是偏好，属于记忆；broker 怎么工作则不属于。

这条划的界很准：**可查的 = 不记，不可查的 = 记**。人的意图无处可查，所以必须记；API 文档随时能看，记了只是白烧 context。

### 4.2 Consolidation：让模型输出动作脚本，而不是重写全文

`consolidation.ts:26`。触发条件是 `<!-- consolidated: DATE -->` 标记行**以下**的 bullet 数 ≥ 10（`bulletsBelowMarker`）。

给模型一个编号列表，要求它只输出三种动作：

```
UPDATE <n>: <revised fact>
DELETE <n>
ADD: <new fact>
```

**这是整层最聪明的一个决定。** 让 LLM 整篇重写记忆，它会顺手改掉你没让它改的行、丢掉它不理解的行、把风格统一成它喜欢的样子。动作脚本把它逼进一个窄接口：可解析、可审计、可部分失败。规则里还明说——

> 不要改写已经没问题的事实。**拿不准就别动它。**

三条保护性规则：

- **永远不要删除或弱化用户明确要求记住的事实**
- `(said in …)` 后缀必须**逐字保留**，UPDATE 时也要带着
- **绝不合并两条来源不同的事实**

### 4.3 运行时能力降级探测

`consolidation.ts:151-155`：

```js
await deps.memory.replace(scopeId, next, "system");
const after = await deps.memory.read(scopeId);
if (after !== next) {
  degraded.add(scopeId);
  log(`[memory] store for ${scopeId} does not support rewrite; consolidation disabled (capture-only)`);
}
```

写完回读校验。如果某个后端实际上只支持追加，就把该 scope 标记 degraded、**永久关闭 consolidation**、降级成 capture-only 并打日志。不靠接口声明，靠实测。

---

## 五、跨 scope 抄送：整层最有产品洞察的 30 行

`memory-service.ts:158-185`。

**问题**：Bob 在 `#project-atlas` 里说了一件关于他自己的事。这条记忆该记在哪？

- 只记频道 → Bob 在 DM 里问，agent 一无所知
- 只记个人 → 频道里别人问起，agent 一无所知
- 都记 → agent 会在错误的场合，把 Bob 在项目频道说的话讲给不相干的人听

QM 的答案是第四种：**两边都记，但个人那份带来源标签**。

```js
const tagged = facts.map((f) => `${f} (said in ${source})`);
return memory.capture(target, tagged, at, `cc:${origin}`);
```

触发条件很克制（`ccTargetFor`）：origin 必须是 channel / group，actor 不能是 system，target ≠ origin。

### 5.1 而这个标签是不可伪造的

看 `foldCapture` 的净化逻辑（`memory-service.ts:59-63`）：

```js
if (!trustedProvenance) {
  text = text
    .replace(/^\((\d{4}-\d\d-\d\d)\)\s*/, "on $1: ")                  // 伪造的日期戳 -> 降级成普通文本
    .replace(/\s+\(said in ([^)]+)\)\s*$/i, " [claimed source: $1]");  // 伪造的来源戳 -> 降级成"声称的来源"
}
```

只有 `author` 以 `cc:` 开头（系统自己发起的抄送）才 `trustedProvenance = true`。

**任何来自模型或用户的文本，只要试图自己带上 `(2026-01-01)` 或 `(said in X)` 这两个系统语义标记，就会被改写掉。** `(said in X)` 变成 `[claimed source: X]` —— 保留信息，剥夺权威。

这是把 provenance 做成了**系统专属命名空间**，一个非常干净的防注入设计。

### 5.2 标签在下游被一路尊重

- recall 的 prompt 里解释它怎么用（`orchestrator.ts:875`）
- consolidation prompt 要求逐字保留、禁止跨来源合并
- scratch-promote 的 promotion prompt 同样要求保留

**绝大多数 agent 记忆系统只有「记住 / 不记住」两态。QM 有第三态：记住，并且记住是在哪儿说的。**

---

## 六、三种策略：三种对记忆本质的不同假设

`MEMORY_STRATEGY` 三选一，默认 `per-turn`（`strategy.ts:28-34`）。

| | **per-turn**（默认） | **scratch-promote** | **agent-only** |
|---|---|---|---|
| 自动捕获 | 有，直接进 notebook | 有，进当日 scratch log | 无，完全不自动 |
| 结构 | 单层 notebook | 双层：notebook + `memory/log/YYYY-MM-DD.md`（留 14 天） | 单层 |
| 整理方式 | 动作脚本 consolidation | LLM 重写完整 notebook（promotion） | 仅 consolidation |
| Recall 内容 | notebook 尾部 6000 字符 | notebook + **最近 2 天** scratch（各截尾 3000 字符） | notebook |
| Search 范围 | notebook | notebook + **14 天**全部 log | notebook |
| 代码量 | 159 行 | 210 行 | **15 行** |

三者的哲学分歧：

- **per-turn**：自动抽取基本可信，脏了再整理。
- **scratch-promote**：赌**大多数自动抽取的事实活不过两周**，所以先隔离在草稿区，只有经得起时间的才「毕业」进正式笔记本。它甚至通过 `promptLines()` 主动告诉 agent 自己有两层，并教它怎么绕过草稿层直接钉一条长期事实（`read` 然后 `rewrite`）。
- **agent-only**：不信任自动抽取，全部交给模型自己策展。15 行代码里 9 行是 prompt：

  > 没有任何东西会自动保存——你是它唯一的策展人。如果你不保存一个事实，这次对话结束它就没了。

值得注意的分化：scratch-promote 的 `maintain` 用的是**完整重写**（`PROMOTION_PROMPT`）而非动作脚本——因为任务性质不同：不是「微调一个已经不错的笔记本」，而是「从一堆噪音里挑出该毕业的」。同一个代码库里，两种整理任务用了两种截然不同的 LLM 接口形态，这是想清楚了才会有的分化。

---

## 七、权限模型

记忆的授权走 capability token claim（`orchestrator.ts:1035-1040`）：

```js
memoryAccess = { write: memoryScopeId, read: recallScopes }
// admin 才额外获得：
if (actorIsOrgAdmin && capture !== "off" && orgScope !== memoryScope)
  memoryClaim.orgWrite = resolution.orgScopeId;
```

落到工具面（`primitives.ts:748-783`）：

| 操作 | 作用范围 |
|---|---|
| `memorySearch` | 遍历 **read scopes 全部**；多个时每条结果打 `[scope]` 前缀 |
| `memoryRead` / `memoryRemember` / `memoryRewrite` | **只有 write scope** |

外加几层收口：

- **只读 wake**（heartbeat 探视）下 `remember` / `rewrite` 直接被拒，返回明确文案
- 写操作包在 `once()` 里做幂等，防重试重复写
- 工具描述里那句是产品级承诺：*"this conversation can only ever touch its OWN memory, no one else's, **by design**."*

### 7.1 跨房间写：能力开在 self-API，不开在工具

想把一条事实写进**另一个房间**的笔记本，工具面没有这个动作，得走 self-API `POST /v1/memory/facts`。core 会先检查这个人本身**有没有资格在那儿说话**：公开频道任何内部同事可写，私有频道 / 群 DM 要求是成员，否则 403。

而且只能**追加**——不能读、不能整体重写别人房间的笔记本。这跟 SECURITY.md 那条「授权未来行为的决定必须来自 agent 之外」是同一思路的延伸：跨边界的写入是有限动词。

org 级笔记本只有 org admin 能写（capability 里单独的 `orgWrite` claim，在确认 admin 状态后才发放）。

### 7.2 审计

每条路径都落审计事件：

```
memory.self.read / memory.self.update / memory.self.restore
memory.agent.search / memory.agent.capture / memory.agent.read
```

admin 面另有 `/v1/admin/memory/scopes` 和 `/v1/admin/memory` 可读可写——SECURITY.md 对此坦白：「admin 是特权内容读者，读取被审计但不需要额外的用户同意。」

---

## 八、质量保障：把记忆质量变成可回归的指标

`bench.ts` 是一个完整的策略基准框架——回放 bench conversation → 得到 notebook → LLM judge 三轴打分：

| 轴 | 测的是什么失效模式 |
|---|---|
| `signalToNoise` | **存了太多垃圾**：一次性琐事、填充、重复、不该存的密钥 |
| `staleness` | **存了过时的**：对话中事实变了，笔记本反映最新状态了吗 |
| `inferenceVsObservation` | **存了编的**：条目是真被说过的，还是模型推测装成的事实 |

Judge prompt 里还有一条防作弊：

> 空笔记本不自动算差：只有当对话中确实包含值得保留的耐用事实时，才给 signalToNoise 低分。

CI 门槛（`bench.ts:142`）：

```js
DEFAULT_STRATEGY_FLOORS = { signalToNoise: 5, staleness: 4, inferenceVsObservation: 5 }
```

`floorFailures()` 返回破线项，`formatTable()` 输出策略横向对比表。

**这三个轴恰好对应记忆系统的三种死法。** 把主观的「记忆质量好不好」拆成三个可打分、可设地板、可回归的维度——这是把 LLM 行为纳入工程控制的正经做法，不是事后凭感觉调 prompt。

---

## 九、配置面

| 环境变量 | 取值 | 默认 |
|---|---|---|
| `MEMORY_RECALL` | `off` / `writable` / `visible` | `visible` |
| `MEMORY_CAPTURE` | `off` / `writable` | `writable` |
| `MEMORY_STRATEGY` | `per-turn` / `scratch-promote` / `agent-only` | `per-turn` |
| `MEMORY_CONSOLIDATE_AFTER` | N 条后整理（0 = 关闭） | 10 |
| `MEMORY_CAPTURE_QUIET_MS` | burst 静默期 | 180000 |
| `MEMORY_CAPTURE_MAX_TURNS` | burst 上限轮数 | 10 |

（定义见 `config.ts:112-117, 802-811`）

---

## 十、设计哲学提炼

1. **记忆是索引，不是数据库。** 工具描述把成本直接摊给模型看：

   > 每一行都会在未来**每一轮**加载进你的上下文，所以记忆是你**最贵的存储**：它是索引，不是数据仓。存指针，永远不要存数据本身——工作状态（队列、backlog、水位线、ID 列表、日志、逐项状态）属于你电脑上的文件，最多在记忆里留一行说明那个文件叫什么、装了什么。**如果一个事实是一个会增长的列表，那它是个文件。**

   这句话里的「你电脑上的文件」指向另一整套存储体系——三层文件模型、双写持久化、以及「盘比记忆更不持久」这个不对称的来源，见 [[qm-execution-layer]] 第四节。

2. **写路径必须唯一，并且反复强调。** 工具描述第一句、SKILL.md 第一段都在说同一件事：「它不是文件」。因为 agent 看到 `memory/MEMORY.md` 这个路径，本能就会想去 `cat` 它。这是针对已知失效模式的重复施压。

3. **Prompt 是这一层的主要实现语言。** 1247 行代码里，四段 prompt 常量承担了绝大部分产品语义。代码只负责触发时机、并发、持久化和净化。

4. **系统元数据必须不可伪造。** `(date)` 和 `(said in …)` 是系统命名空间，任何非可信来源的同形文本一律降级改写。

5. **防止模型给自己造记忆。** 两条独立的约束（不从 assistant 回复推导、自主轮不产出人的事实）指向同一个风险。

6. **让 LLM 走窄接口。** 整理笔记本用动作脚本而不是自由重写。

7. **能力靠实测，不靠声明。** consolidation 写完回读校验，不支持就自动降级。

8. **质量要能回归。** 三轴 judge + CI 地板。

---

## 十一、张力与风险

调研中发现的、值得注意的几处：

**1. FIFO 淘汰与「重要性」不相关。**
`foldCapture` 溢出 300 条时从**最老的** bullet 砍（`memory-service.ts:87-90`）。但一个人最核心的事实——他是谁、他负责什么——往往是最早被记住的。consolidation 会做语义化的合并删除，但它的口径和 FIFO 完全不同，两者没有协调。高频用户长期使用后，基础事实可能被悄悄挤掉。

**2. Recall 与 query 的可见性不对称。**
`recallBody` 用 `capTail` 取尾部 6000 字符，同样偏新。所以当 notebook 变长时会出现：**自动回忆看不到、主动搜索却搜得到**的老事实。这个不对称没有在 prompt 里向 agent 说明——SKILL.md 只说了「你记得的比自动注入的多」，但没说「多出来的那部分系统性地偏老」。

**3. 检索没有语义层。**
子串 AND 匹配对「上个季度那个客户叫什么来着」这类模糊回忆无能为力。SKILL.md 把限制诚实地暴露给了 agent，但这是解释限制，不是解决限制。考虑到 300 条的规模上限这是合理取舍——但也意味着规模假设一旦被打破，需要换的不只是一个函数。

**4. BurstBuffer 是进程内 Map。**
`per-turn.ts:91` 的 `bursts` 存在 RAM 里。按 AGENTS.md 自己那条「Durable by default」的标准，这处于灰色地带——默认 180 秒静默窗口内如果实例被 blue-green 换掉，这批待抽取的事实就丢了。不严重（用户下次还会说），属于文档里说的「真正可丢弃、可重建的状态」，但它确实是 RAM-only 且写在一个反复强调不要 RAM-only 的代码库里。`degraded` Set 同理（重启后会对已知不支持的 store 重试一次，无害）。

---

## 十二、可迁移到自己项目的做法

这一层里几条与 qm 无关、可以直接搬走的设计：

- **系统元数据独占命名空间 + 非可信输入一律降级改写**（`(said in X)` → `[claimed source: X]`）——比「过滤掉」更好，因为保留了信息但剥夺了权威。
- **让 LLM 输出动作脚本而非重写全文**——凡是「让模型维护一份长期文档」的场景都适用。
- **写完回读校验以探测后端能力，失败即永久降级**——比在接口上声明 capability 更可靠。
- **把主观质量拆成 3 个可打分轴 + CI 地板**——signal/noise、staleness、inference-vs-observation 这三个轴对任何 LLM 抽取系统都通用。
- **抽取 prompt 的主体写「不要记什么」而非「要记什么」**。
- **禁止从模型自己的输出中提取用户偏好**——防自指污染闭环，这个坑很隐蔽。

---

> 回到 [[qm-overview]] 看整体架构与其余模块。

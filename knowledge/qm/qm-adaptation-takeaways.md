# 从 QM 适配机制提炼的可借鉴清单

> 关联文档：
> - [[qm-skill-adaptation]]（**姊妹篇：本篇的全部依据。纯 QM 机制描述，不含可借鉴性判断**）
> - [[qm-harness-layer]] · [[qm-skills-layer]] · [[qm-execution-layer]] · [[qm-overview]]
> - 仓内参照：[`docs/explanation/skill-creator-testing-system.md`](../../docs/explanation/skill-creator-testing-system.md)（评估方法论）
>
> 整理时间：2026-08-14
> 依据版本：`yc-software/qm` @ `0f0e0ad`
>
> **本篇按「问题」组织，不按模块组织。** 每一条先说我们面对的问题，再说 QM 的做法，
> 最后给判断：直接抄 / 改造后抄 / 不抄，以及理由。
>
> 本篇只做判断与理由，不设计具体方案。

---

## 零、先说结论

QM 是目前唯一一个在生产里让**一份 skill 跑在四个异构 agent 循环上**的开源系统。它值得抄的地方比预想的多，但**抄的位置和预想的不一样**：

| | 预想 | 实际 |
|---|---|---|
| 最值钱的 | 能力协商接口 `HarnessAdapterProfile` | **jail 模式**（第二节）与 **末端补偿**（第一节） |
| 中等价值 | tape / 冷启动重放 | **三层确定性测试**（第五节）、**纯函数解析器**（第四节） |
| 高估了的 | `capabilities` 能力表 | 0 个生产消费点，只是文档 + 护栏（第六节） |
| 完全没有的 | —— | **真 LLM 跨平台行为评估**（第八节） |

一句话：**QM 给的是「怎么可靠地驱动一个异构平台」，不是「怎么评估一个 skill 在异构平台上的表现」。前者可以大段抄，后者它一行都没有。**

---

## 一、问题：skill 写在一个平台上，用了那个平台的特性

这是我们的原始问题。

### QM 的做法

**skill 正文对四个 harness 完全无感，一行都不改。**（[[qm-skill-adaptation]] 第二节）

平台差异全部在适配器的最后一步用**追加文字**消化：opencode 把工具改名后，在 systemPrompt 尾部注入一段别名翻译表；claude 用原生 subagent 时追加一段额外约束；pi 冷启动时追加历史重放前言。

一般形式：

> 平台 P 与 skill 假设不一致时，**不重写 skill，不禁用 skill，在 P 的适配器里注入一段声明差异的文字**。

### 判断：直接抄，这是整套架构的地基

理由有三：

1. **维护成本是决定性的。** 我们有 50+ 个 skill × 7 个目标平台。为每个平台维护变体是 7 倍维护成本，一次都做不下去。一份 skill + 每平台一段差异声明，是 `50 + 7` 而不是 `50 × 7`。
2. **差异声明是数据不是代码。** 一段字符串可以被测试断言、可以被人 review、可以直接展示给用户。分支逻辑做不到这三点。
3. **那段声明文字本身就是产出。** 「这个 skill 要在 cursor 上跑需要补什么」——这个问题的答案，正好就是适配器要注入的那段文字。**适配手段和诊断结论是同一个东西。** 这一点在设计框架输出形态时会很关键。

### 但有一个必须正视的落差

**QM 有一个中间工具面，我们没有。**

QM 的 core 自己定义了十来个固定工具（`execute` / `read` / `write` / `publish` / `memory` / `history` / `background` / `cron` / …），四个 harness 都被迫适配到这套工具面上。所以 skill 正文只要针对这一套写就够了，末端补偿要补的差异很小——opencode 那边只有三个工具改名。

**我们的 skill 直接针对 Claude Code 的工具名写。**（实测：`~/.claude` 硬编码 6 个文件、`allowed-tools` frontmatter 4 个、`AskUserQuestion` 2 个、`WebSearch` 3 个、MCP 4 个。）没有中间层意味着末端补偿要补的不是「三个工具改名」，而是**整套工具面语义映射**。

这个落差有两种走法，都不该在框架设计里顺手做掉：

- **A：先定义最小公共工具面词汇表**（读文件 / 写文件 / 跑命令 / 搜网 / 问用户），让 skill 正文向它对齐。收益是末端补偿退化成 QM 那种小规模；代价是波及全部现存 skill，是一次大迁移。
- **B：不定义中间层，让每个适配器持有一张较大的映射表。** 收益是零迁移成本；代价是映射表的维护量随「平台数 × 工具数」增长，而 QM 的经验（三行硬编码 if，见风险 5）说明这条路会失控。

这是整个项目最大的一个未决架构问题，**应该作为独立议题讨论，而不是框架设计的副产品**。

### 顺带：skill 正文里可移植的措辞

`skillsIndex()` 的一句 `run its steps with your tools` 是刻意去平台化的——索引层不承诺任何工具名。skill 正文引用文件用 `read skills/<name>/SKILL.md`（沙箱文件路径，四个平台都能读），而不是任何平台的 skill 加载机制。

**这是一条零成本、可立即执行的写作规范**：skill 正文里凡是能用「读这个文件」「跑这条命令」表达的，就不要写具体工具名。这一条不依赖任何框架，今天就能用在新 skill 上。

---

## 二、问题：怎么起一个平台，还保证跑出来的结果是干净的

如果框架要真跑六个平台，第一个问题就是：**用户机器上 `~/.claude/skills/` 里装的 50 个 skill、`~/.pi/` 里的 extension、`~/.config/opencode/` 里的配置，会不会污染测试结果？**

会。而且是致命的——一次「cursor 上这个 skill 失败了」的结论，可能实际上是用户某个全局配置造成的。

### QM 的做法：jail 模式，四次应用

（[[qm-skill-adaptation]] 第四节）

| | jail | 重定向的配置根 | 环境变量策略 |
|---|---|---|---|
| claude | `mkdtempSync` | `HOME=jail`, `CLAUDE_CONFIG_DIR=jail/.claude` | 白名单 15 项 |
| codex | `mkdtempSync("qm-codex-")` | `HOME=jail`, `CODEX_HOME=jail/codex-home` | 白名单 15 项 |
| opencode | `mkdtempSync("qm-opencode-")` | `HOME`/`TMPDIR`=jail, `XDG_CONFIG/DATA/CACHE_HOME`=jail/* | `cleanEnv` 从零构造 8 键，PATH 硬编码 |
| pi | 临时 cwd + agentDir | 构造器参数 | `noExtensions/noSkills/noPromptTemplates/noThemes/noContextFiles` |

白名单的四类内容非常整齐：**PATH 与本地化 / TLS 证书 / 代理 / 该平台自己的凭证**。别的一律不传。

### 判断：直接抄，而且这是六条里最紧急的一条

三个理由：

1. **不做 jail，整个框架的结论都不可信。** 这不是「锦上添花的隔离」，是结果有效性的前提。跨平台对比的全部价值建立在「除了平台，其他都一样」上。
2. **白名单模式必须照抄，不能改成黑名单。** 新出现的环境变量默认不通过。我们跑六个平台，六份白名单，每份 15 行左右——成本极低，收益是「用户机器上任何新东西都不会悄悄泄进来」。
3. **`noSkills: true` 那一行是灵魂。** QM 驱动 pi 时**主动关闭 pi 原生的 skill 加载**。对我们含义直接：框架跑一个 skill 时，必须确保平台不会同时加载用户已安装的同名/其他 skill。否则测的是「这个 skill + 用户全部 skill」的混合体。

### 具体到六个平台，可用的开关（实测 CLI）

| 平台 | 配置根重定向 | 关闭原生 skill 发现 |
|---|---|---|
| claude | `HOME` + `CLAUDE_CONFIG_DIR` | `--bare`（跳过 hooks/LSP/plugin sync/CLAUDE.md 自动发现），skill 仍走 `/skill-name` |
| codex | `HOME` + `CODEX_HOME` | 待验 |
| opencode | `HOME` + `XDG_CONFIG_HOME`/`XDG_DATA_HOME`/`XDG_CACHE_HOME` + `OPENCODE_CONFIG_CONTENT` 内联配置 | 通过内联配置控制 |
| pi | 临时 `--session-dir` | `--no-skills` / `-ns`、`--no-extensions` / `-ne`、`--no-prompt-templates` / `-np` |
| hermes | 待验 | `--ignore-user-config`、`--ignore-rules`、`--skills SKILLS` |
| cursor-agent | `--workspace <path>` | 待验 |

**pi 和 hermes 的开关最齐全**（`--no-skills` / `--ignore-user-config` 都是现成的），claude 的 `--bare` 也正对这个需求。这三个平台的 jail 可以做得很扎实。**codex 与 cursor-agent 的隔离手段需要实测确认**，这应该是任何真跑框架的第一批验证项。

**`OPENCODE_CONFIG_CONTENT` 这个手法值得单独记一笔**：整份配置以 JSON 字符串塞进环境变量，不落盘。没有清理问题，没有并发问题，没有「测试跑一半被另一个测试改了配置文件」的风险。凡是平台支持这种内联配置的，优先用它。

---

## 三、问题：注入通道用哪条

### QM 的做法

四条通道抽象层级完全不同（in-process / 第三方 SDK / 自研 JSON-RPC / HTTP+插件注入），QM **没有强行统一实现形态，只统一了接口**。

### 判断：抄「统一接口不统一实现」这个态度，不抄具体通道

理由：QM 是运行时，需要流式、需要中断、需要工具回调，所以它必须用 SDK / RPC / 插件这些重通道。**我们是测试框架，一次性跑完抓输出即可**——六个平台的 `-p` / `--print` / `run` headless 模式就够了，不需要 opencode 那种「起服务 + 塞插件 + 回调桥」的复杂度。

但要抄两个具体做法：

**① 从 QM 各适配器抽象层级的巨大差异学到的**：不要为了让六个适配器"长得一样"而抽象。适配器接口应该窄（起进程 / 注入 / 抽输出 / 差异声明），实现各自长成它该长的样子。QM 的 opencode 适配器是 1163 行 + 286 行插件，pi 是进程内直接调用——同一个接口下差 20 倍体量，这是正常的。

**② codex 的 `writeTail` / `eventTail` 两条 Promise 串行链。**（[[qm-skill-adaptation]] 3.2 节）行分隔的流协议下，两个并发写会交错出半行 JSON。任何解析 stream-json 的地方都要保证读写各自串行。这是**协议正确性的必要条件，不是性能优化**——很容易在写适配器时漏掉，然后在高负载下偶发地拿到损坏的 JSON。

### 顺带：codex 那 169 行 RPC 客户端里，有四条与通道无关的通用做法

即使我们不用 JSON-RPC，这四条对任何「起子进程抓输出」的代码都适用：

1. **stderr 环形缓冲进错误消息**（上限 16KB）。子进程退出码单独看没有诊断价值，要拼上 stderr 尾部才知道**为什么**死。
2. **`failAll` 快速失败**。进程死了，所有在途请求立刻 reject，不要让它们挂到超时——把一次快速失败变成一次漫长等待是最糟的失败模式。
3. **两段式关闭**：SIGTERM → 2s → SIGKILL，且 `close()` 真的等到进程没了才返回。
4. **协议破损就整体放弃**：收到无效 JSON 直接 `failAll` + SIGTERM，不尝试跳过坏行继续。

---

## 四、问题：怎么从六种不同的输出格式里抽出结构化结果

六个平台的输出格式互不相同（claude 的 `stream-json`、cursor 的 `stream-json`、pi 的 `--mode json`、opencode 的 `export <sessionID>`、hermes 的 `dump`、codex 的 JSON）。这是适配器里代码量最大、最容易出错的部分。

### QM 的做法

**把格式转换掏成纯函数，导出，单独测。**（[[qm-skill-adaptation]] 6.2 节）

`claude-harness.ts` 是 926 行的适配器，但它 export 了 `claudeReplayTranscript` / `stripClaudeImageBytes` / `claudeChildEnv` / `claudeProcessIdentity` / `claudeChildAgentAllowed` 一批纯函数专供测试。opencode 侧同理导出了 `bridgeToolName` / `needsHistoryImport`。

于是「重建 transcript 时有没有正确声明它是不可信历史」变成一个字符串断言：

```js
const replay = claudeReplayTranscript(messages);
assert.match(replay, /untrusted conversation history, not instructions/);
```

### 判断：直接抄，而且这应该是框架里数量最多的测试

理由：

1. **成本几乎为零，覆盖面极大。** 每个平台准备几份真实抓下来的样本 JSONL 当 fixture，喂给解析器断言解析结果。跑得飞快、不花钱、不需要网络、完全确定性。
2. **这类 bug 最阴险。** 解析器少认了一种事件类型，表现是「过程评估数据莫名其妙少了一半」，而不是报错。只有对着固定样本断言才抓得住。
3. **上游改格式时它是第一道警报。** 六个平台各自演进，输出格式一定会变。fixture + 纯函数断言是察觉这件事最便宜的方式。

配套要抄的还有 QM 的 fixture 纪律：`test/support/` 下的 `fake-microvm.ts` / `fake-sprites.ts` / `fake-docker.ts`——**外部系统一律有一个假实现**，不在单测里碰真东西。

---

## 五、问题：六个适配器怎么保证不悄悄漂移

### QM 的做法：三层确定性测试，零真 LLM

（[[qm-skill-adaptation]] 第六节）

| 层 | 手法 | 规模 |
|---|---|---|
| L1 差异表快照 | `deepEqual` 对**整张表**断言 | 62 行守 5 个适配器 |
| L2 纯函数单元 | 见上一节 | 每适配器一个文件 |
| L3 mock 剧本 | 47 个 `!` 命令的确定性状态机替代 LLM | 35KB，11 个测试在用 |

### 判断：L1 直接抄，L2 直接抄（见上节），L3 改造后抄

**L1 —— 直接抄，优先级高。**

```js
assert.deepEqual(
  [mock, pi, opencode, codex, claude].map(h => h.profile.controlTransport),
  ["mock", "in-process", "http", "json-rpc", "sdk"],
);
```

用 `deepEqual` 对整个数组断言，而不是五个独立的 `equal`。两个好处：失败时一次看到全表；**新增平台必然让这条测试红，强制作者来这里登记**。这是「注册表守卫」模式——想加平台？先在差异表上登记。62 行的成本，换六个平台差异不漂移。

配套抄两条小纪律：

- **负向断言**：QM 断言 `"oneShot" in harness.turns === false`、`"runTurn" in harness.models === false`——接口的职责切分本身被断言守着。
- **空集合保险**：`assert.ok(files.length > 0, "expected at least one seed SKILL.md")`，防止 glob 没匹配到文件造成的假绿。**我们的矩阵测试同理：跑了 0 个平台组合不能算通过。** 这是最容易忘、后果最隐蔽的一条。

**L3 —— 不抄那 47 个命令，抄它背后的分工。**

mock-harness 测的是 QM 自己的编排内核（压缩、记忆、审批、持久进程），我们没有这个内核，我们的"编排"薄得多。但**分工原则要抄**：

> **用确定性假模型测框架本身，用真模型测 skill 内容。**

这条线划在哪里，决定了 CI 能跑什么、什么必须手动触发花钱跑。

**具体可抄的是「回吐」手法。** QM 的 mock harness 收到 `!sysprompt` 就把它拿到的 systemPrompt 原样吐回，于是「prompt 装配对不对」变成字符串断言。对应过来：框架应该有一个 **dry-run / echo 模式**，把「将要注入各平台的完整 prompt」原样输出而不真跑。

这一条的价值被低估了——它把两件事彻底解耦：

- **注入内容对不对** → 零成本、确定性、可进 CI
- **模型表现好不好** → 花钱、有方差、按需触发

没有这条分割线，每次想验证「我给 cursor 注入的东西对不对」都要花钱跑一次真模型。

---

## 六、问题：能力差异要不要驱动运行时降级

直觉上应该建一个机制：测试用例声明「需要能力 X」，平台没有就自动 skip 而不是 fail。

### QM 的做法：声明了，测了，但生产从不读它

```
capabilities 声明点：5 处
capabilities 断言点：3 处（全在 harness-adapter.test.ts）
capabilities 生产消费点：0 处
```

`controlTransport` / `toolTransport` / `transcriptFormat` 同样——除测试外无人读。（[[qm-skill-adaptation]] 第五节）

### 判断：抄「声明 + 断言」，**不要**抄「分派机制」——因为它不存在

这是本次调研最有实践价值的一条负面发现。

QM 是一个 76,648 行、跑在生产里、支撑四个 harness 的系统，**跑到 v1 都还没长出一个能力分派的消费点**。这强烈提示：先建一个没有消费者的能力分派框架是典型的过度设计。

能力表先做成两件事就够了：

1. **可执行的文档** —— 差异写在代码里而不是 README 里，不会腐烂成过期文字
2. **回归护栏** —— 配合 L1 整表快照

真实的降级需求会自己浮现。到时候让消费点长出来，比一开始就猜要准得多。

### 但要吸取 QM 在这一条上的教训

**能力表没有消费者，长期会腐烂成谎言。**（[[qm-skill-adaptation]] 风险 1）

这张表靠一条测试守着，而这条测试断言的正是声明本身——**自己证明自己**。改了适配器同时改了测试（很自然的操作），表就和现实脱节而无人察觉，因为没有任何生产路径会因为它错了而出错。

缓解办法：**让至少一个真实消费点存在**。最轻的做法是让报告渲染时读它（「本次 cursor 上跳过了 3 项，因为它不支持工具轨迹输出」）。这样表错了会体现在给人看的输出里，谎言就有了代价。

### 顺带修正一处：真正落地的是 `tools.name`，不是 `capabilities`

[[qm-harness-layer]] 第 88 行原写「`tools.name` 四个适配器没有一个覆盖它，接缝存在但未使用」——**这是错的**。opencode 覆盖了它，有测试守着，并配套注入了别名声明，构成跨平台工具面适配的完整闭环。

原文把整个 profile 机制里唯一有真实消费者的那条判成了「未使用」，而把 0 消费点的 `capabilities` 讲成了核心手法——**两处评价正好接反**。已在两处文档标注勘误。

这个教训本身值得记：**判断一个机制重不重要，要看有没有消费者，不能只看接口定义得漂不漂亮。**

---

## 七、问题：过程评估怎么落地

「质量评估」有现成参照（仓内 `docs/explanation/skill-creator-testing-system.md` 那套断言 + grader + benchmark）。**「过程评估」没有现成参照**——这是 QM 唯一能提供线索的地方。

### QM 的做法一：`GapPhase` 22 相延迟归因

（[[qm-skill-adaptation]] 7.1 节）

```ts
export type GapPhase =
  | "provision" | "creds" | "dir_cleanup" | "proc_reconcile" | "auth_probe" | "skills_materialize"
  | "recall" | "memory_write" | "file_op" | "exec"
  | "model_dispatch" | "dispatch_glue" | "loop_reentry" | "context_assemble" | "glue_other"
  | "tool_body" | "pre_tool" | "in_tool_untagged" | "post_tool" | "tool_ledger"
  | "persist" | "stream_open";

export type GapPhases = Partial<Record<GapPhase, number>>
  & { residual?: number }
  & { [key: `tool_body.${string}`]: number | undefined };
```

### 判断：22 相不抄，三个设计点直接抄

**不抄 22 相**——那是 QM 自己编排管线的相，我们的管线里根本不存在 `provision` / `creds` / `proc_reconcile` 这些阶段。

**抄这三个：**

1. **`residual`：承认自己没归因完。** 各相加起来对不上总时长的部分单列，而不是把误差摊进某一相。任何时间/token 归因都该有这一格——**没有 residual 的归因表一定在撒谎**。
2. **模板字面量键 `tool_body.${string}`：按工具名再细分一层。** 对应我们：工具调用统计不只要「共调了 12 次工具」，要 `tool.Read: 5, tool.Bash: 4, tool.Edit: 3`。跨平台对比时，**工具调用分布的差异比总次数的差异信息量大得多**。
3. **可选字段 + `| null` 到处都是**，说明预期就是参差不齐。六个平台能给出的过程数据一定不一样，数据模型从一开始就该允许缺失，而不是假设都能拿到。

### QM 的做法二：`unreached` 负向断言

```js
const unreached = () => {
  throw new Error("fakeSandbox: a conversational !sysprompt turn must not touch the sandbox");
};
```

`fakeSandbox` 的每个方法都是 `unreached`。一次纯对话的 turn 如果碰了沙箱，测试就炸，**错误消息直接说明违反了什么约束**。

### 判断：直接抄，这是过程评估最容易落地的第一个形态

理由：**「不该做的事」比「做得好不好」容易判定一万倍。**

- 一个只读的 skill，在某平台上触发了写工具 → 客观、可判定、有价值
- 一个规定「先问用户再动手」的 skill，在某平台上直接动手了 → 客观、可判定、有价值
- 一个 skill 在 cursor 上「推理质量不如 claude」 → 主观、需要 grader、有方差

**先做前两类。** 它们不需要 LLM 判官，不需要多次采样消除方差，一次运行就能给出确定结论。而且它们恰好是跨平台最容易出问题的地方——skill 里的约束性指令（"不要"、"先…再…"）在不同模型上的遵守度差异，比生成质量的差异更大也更重要。

前提是能拿到工具调用轨迹。**这应该是平台差异表里最先要登记的一格**——任何平台给不出工具轨迹，过程评估在那个平台上就整个塌掉，只能退回质量评估。

---

## 八、QM 完全没有答案的部分

全仓确认（[[qm-skill-adaptation]] 6.5 节）：

- **没有 `evals/` / `benchmarks/` / `golden/` / `snapshot/` 目录**（唯一的 `test/memory-bench` 是记忆策略性能基准，不是行为评估）
- **没有任何跑真 LLM 做跨适配器行为对比的测试**
- **skill 层面唯一的自动化检查是 23 行的静态解析**（`skill-conformance.test.ts`，只验证 seed skill 能解析出 name/description/body）

也就是说：**QM 保证的是「四个适配器的管道对等」，不保证「四个模型对同一个 skill 的理解对等」。**

这个边界划得是合理的——QM 是运行时，不是 skill 作者工具，skill 质量由作者负责。但对我们来说：

```
QM 造的：    一份 skill → 四条管线 → 管线对等性，三层确定性测试守住
我们要造的：  一份 skill → N 个真平台 → 行为对等性，真跑 + 双重评估
```

**架构可以抄，测试策略只能抄一半，评估层不存在。**

评估层的现成参照不在 QM，在仓内已有的 [`docs/explanation/skill-creator-testing-system.md`](../../docs/explanation/skill-creator-testing-system.md)：对照实验（with_skill vs without_skill）、`evals.json`、断言、grader agent、`benchmark.json` + `benchmark.md`、人工 viewer。

**两者互补，且互补得很干净：**

| | 提供什么 | 不提供什么 |
|---|---|---|
| QM | 适配器架构、jail 隔离、解析器测试策略、过程数据模型 | 任何评估 |
| skill-creator | 评估方法论、断言体系、对照实验设计、人机协同 | 任何跨平台机制 |

而且 skill-creator 那套的「对照」轴是 `with_skill vs without_skill`（纵向：skill 有没有用），我们要的是 `platform_A vs platform_B`（横向：跨平台一不一致）。**方法论可以整套搬，只需要换对照轴**——这是一个很小的改动，说明这套方法论选得对。

---

## 九、明确不该抄的

| 机制 | 为什么不抄 |
|---|---|
| **`tape` 事件溯源与冷启动重放** | 长会话服务的需求。我们是一次性跑 + 抓输出，会话不需要跨进程重启存活。 |
| **mock-harness 的 47 个命令** | 测的是 QM 自己的编排内核（压缩/记忆/审批/持久进程），我们没有这个内核。**但它背后的分工原则要抄**（第五节）。 |
| **scope 所有权、签名、`draft→reviewed→published` 状态机** | 见 [[qm-skills-layer]] 第十节。单人仓库，多租户模型是纯负担。 |
| **上下文压缩两级阈值** | 我们的单次运行不会撞上下文上限；撞上了说明测试用例设计有问题，该修用例不该加压缩。 |
| **`jsonSchemaToZod` 那 150 行** | 那是因为 opencode 的插件 API 要 Zod。我们走 headless CLI，不注入工具，不需要 schema 翻译。 |
| **loopback HTTP 回调桥 + 插件注入** | 那是为了让 core 的工具在 opencode 进程里可用。我们不需要给平台注入工具，只需要读它的输出。 |
| **`capabilities` 的分派机制** | 它不存在（第六节）。 |

---

## 十、优先级建议

按「不做会让整个框架的结论不可信」排序：

| 级别 | 条目 | 依据 |
|---|---|---|
| **P0** | **jail 隔离**（配置根重定向 + 环境白名单 + 关闭原生 skill 发现） | 不做则所有跨平台结论都可能是用户配置造成的假象。第二节。 |
| **P0** | **一份 skill + 每平台差异声明** 的总架构 | 决定了维护成本是 `50+7` 还是 `50×7`。第一节。 |
| **P1** | **纯函数解析器 + fixture 单测** | 适配器代码量最大、最易错的部分；成本近零。第四节。 |
| **P1** | **差异表 `deepEqual` 整表快照** | 62 行换六平台不漂移；新增平台强制登记。第五节。 |
| **P1** | **dry-run / echo 模式** | 把「注入对不对」与「模型好不好」解耦，前者进 CI 后者按需花钱。第五节。 |
| **P2** | **`unreached` 式负向断言**（过程评估第一形态） | 「不该做的事」比「做得好不好」容易判定一万倍。第七节。 |
| **P2** | **空集合保险**、**负向断言**、**`residual` 归因格** | 单条成本极低，防的都是隐蔽假绿。第五、七节。 |
| **P3** | 能力表「声明 + 断言」（且至少一个真实消费点） | 先当文档和护栏，不建分派。第六节。 |
| **待定** | 中间工具面词汇表 | 独立架构议题，不该是框架设计的副产品。第一节。 |

---

## 附：本次调研发现的、与真跑相关的实测事实

这些不是从 QM 来的，是调研过程中为验证可行性顺带确认的，记在这里避免重复劳动。

**本机 CLI 可用性**（7 个安装目标）：

```
claude ✓   codex ✗(损坏)   opencode ✓   cursor-agent ✓   hermes ✓   pi ✓   openclaw ✗(未安装)
```

- **`codex` 本机已损坏**：`/opt/homebrew/lib/node_modules/@openai/codex/vendor/aarch64-apple-darwin/codex` ENOENT，`--help` 都跑不起来。任何真跑落地前必须先重装。
- **`openclaw` 无 CLI**，是七个目标里唯一无法真跑的。

**各平台的 headless 通道与隔离开关**（实测 `--help`）：

| 平台 | headless | 结构化输出 | 隔离开关 |
|---|---|---|---|
| claude | `-p/--print` | `--output-format stream-json` | `--bare`、`CLAUDE_CONFIG_DIR` |
| cursor-agent | `-p/--print` | `--output-format text\|json\|stream-json`、`--stream-partial-output` | `--workspace <path>` |
| pi | `--print/-p` | `--mode text\|json\|rpc` | `--no-skills/-ns`、`--no-extensions/-ne`、`--no-prompt-templates/-np`、`--session-dir`、`-t` 工具白名单 |
| opencode | `run [message..]`、`serve`、`acp` | `export <sessionID>` → JSON、`stats` → token/cost | `OPENCODE_CONFIG_CONTENT` 内联配置、XDG 三件套 |
| hermes | `-z PROMPT`、`--cli` | `dump`、`sessions` | `--ignore-user-config`、`--ignore-rules`、`--skills` |
| codex | `exec`、`app-server` | JSON / JSON-RPC | `CODEX_HOME` |

- **pi 和 hermes 的隔离开关最齐全**，claude 的 `--bare` 也正对这个需求。
- **codex 与 cursor-agent 的隔离手段待实测**，应是第一批验证项。
- **opencode 和 hermes 都提供 ACP**（Agent Client Protocol），claude 有社区的 `claude-code-acp` 适配器——存在一条控制通道收敛的可能路径，但按第三节的判断，测试框架未必需要它。

---

> 相关：[[qm-skill-adaptation]]（本篇的全部依据） · [[qm-harness-layer]] · [[qm-skills-layer]] · [[qm-overview]]

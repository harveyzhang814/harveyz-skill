# Skill 跨平台 Harness 适配测试框架 — design

**Date:** 2026-08-14
**调研依据:** [qm-skill-adaptation](../../../knowledge/qm/qm-skill-adaptation.md)（QM 机制）
· [qm-adaptation-takeaways](../../../knowledge/qm/qm-adaptation-takeaways.md)（可借鉴清单）

---

## Problem

本仓库的 skill 用 Claude Code 写成，正文里焊死了平台专属构造。实测全量 grep：

| 构造 | 命中文件数 |
|---|---|
| 硬编码 `~/.claude` 路径 | 6 |
| `allowed-tools` frontmatter | 4 |
| `WebSearch` | 3 |
| MCP / `mcp__` 引用 | 4 |
| `AskUserQuestion` | 2 |

`hskill` 已支持 7 个安装目标（claude / cursor / codex / openclaw / hermes / opencode / pi），
但**装完之后没有任何验证手段**。现有的 `skills/mint/runby-opencode/` 是一个手工的单平台原型：
把 skill 装进 opencode 的 skill 目录、手敲 `opencode run`、人眼比对。不可重复、不可回归、只覆盖一个平台。

要解决的是：**同一个 skill 在多个 agent 平台上跑，行为是否一致；不一致时，差异在哪、要补什么。**

---

## 决策：框架驱动平台运行时，native 为主、inject 为对照

框架自己起各平台的 headless CLI，抓输出，做质量与过程双重评估。
**不污染用户真实的 skill 目录** —— 但走的是各平台**原生的** skill 加载通道，
skill 装在 jail 内的 skill 目录里（`<jail>/.claude/skills/`、`<jail>/.hermes/skills/`），
或经平台的显式加载参数（pi `--skill <path>`）。jail 已经把「原生机制」与「污染用户环境」解耦了。

两种模式并存，它们不是二选一，是**诊断对**：

| | native 触发成功 | native 未触发 |
|---|---|---|
| **inject 执行正确** | 该平台通过 | description 触发词问题，正文没问题 |
| **inject 执行错误** | 正文有平台特有假设 | 两层都要改 |

单跑任何一种模式都拿不到这张表。native 是被测对象（端到端：发现 → 触发 → 执行），
inject 是拆解用的仪器（把触发环节短路，单独考察指令质量）。

### 依据：2026-08-14 实测（3 平台 × 2 模式）

完整记录与复现方法：[measurements/2026-08-14-native-vs-inject.md](measurements/2026-08-14-native-vs-inject.md)

探针 skill 正文含两个 token：一个写在 SKILL.md 里（`BODY`），一个写在同目录
`references/token.md` 里（`FILE`），要求模型两个都输出。`FILE` 直接测「路径锚点是否存在」。

| 平台 | 模式 | 通道 | BODY | FILE |
|---|---|---|---|---|
| pi | native | `-ns --skill <dir>` | ✓ | ✓ |
| pi | inject | `--append-system-prompt` | ✓ | **UNREACHABLE** |
| pi | inject + 路径补偿 | 追加一行绝对路径 | ✓ | ✓ |
| claude | native | jail `.claude/skills/` + `--setting-sources user` | ✓ | ✓ |
| claude | inject | `--append-system-prompt` | ✓ | **UNREACHABLE** |
| hermes | native | jail `.hermes/skills/` 自动发现 | ✓ | ✓ |
| hermes | inject | 拼进 `-z` prompt | ✓ | **UNREACHABLE** |

**三个平台无一例外：纯正文注入必然断锚。** 这不是概率问题——注入模式下模型压根没有
「skill 根目录」这个信息，行为是确定性失败。

本仓库 44 个 skill 中 **31 个（70%）在正文里引用了同目录的 `references/` `scripts/`
`assets/` 等资源**，另有 13 处正文明说「skill 目录」、4 处说「同目录」。
纯注入模式下这 31 个 skill 会在第一次读附属文件时断裂，且失败形态是模型编一个路径然后
读失败——会被误记成「该平台执行失败」，实际是测试装置的伪影。

**触发 gate 确实存在**：pi native 模式下换成不含触发词的 prompt（"what is 2+2"），
skill 未被调用，模型直接答 `4`。说明 native 模式真的在测 description 匹配，
inject 模式真的把这一环短路了。

**补偿能救 inject**：在注入正文后追加一行 `This skill directory is: <绝对路径>`，
pi 的 `FILE` 恢复正常。这正是 QM 末端补偿的形态，故 inject 模式统一带该补偿行。

### 依据：QM 的三条结论

调研 `yc-software/qm`（唯一在生产里让一份 skill 跑在四个异构 harness 上的开源系统）后确立：

1. **skill 内容平台无关，差异在适配器末端补偿。**
   QM 的 skill 正文对四个 harness 完全无感，一行不改；平台差异在适配器接到 systemPrompt
   之后、发给模型之前用**追加文字**消化（opencode 注入工具别名表、claude 注入子 agent 约束）。
   一般形式：不重写 skill，不禁用 skill，注入一段声明差异的文字。

2. **平台必须关进 jail。**
   QM 对三个子进程适配器 + pi 用同一个模式：配置发现根目录整个重定向到临时目录，
   环境变量白名单构造，并**主动关闭平台原生的 skill 加载**（`noSkills: true`）。
   不做 jail，跨平台结论都可能是用户全局配置造成的假象。

3. **能力表先当文档和护栏，不建分派机制。**
   QM 76,648 行、四个 harness、跑到 v1，`capabilities` 仍是 5 处声明、3 处断言、
   **0 处生产消费**。先建没有消费者的能力分派是过度设计。

---

## Non-goals

| 不做 | 理由 |
|---|---|
| 往用户真实 skill 目录写任何东西 | jail 内的 skill 目录已经能走原生通道，无需污染 |
| 把 skill 装进平台 skill 目录后测触发 | ~~见上，另一个问题~~ **已推翻**，见「决策」——这是主模式 |
| TUI / pty 自动化通道 | 六个平台无一缺 headless，pty 换不来新信息 |
| 能力分派机制（缺能力自动 skip） | QM 无消费点；真需求浮现再长 |
| 给平台注入工具（MCP / plugin bridge） | 只读输出，不需要 QM 那套 schema 翻译与回调桥 |
| tape 事件溯源 / 冷启动重放 | 一次性运行，会话不需跨进程存活 |
| 中间公共工具面词汇表迁移 | 独立架构议题，见「未决问题」 |
| 第一期纳入 cursor-agent / codex / openclaw / opencode | 见「分期」 |

---

## Architecture

```
                    ┌─────────────────────────────────────┐
   skill + task ───▶│  Runner                             │
                    │  组装矩阵 · 分发 · 并行 · 收集        │
                    │  矩阵 = skill × platform × mode × n  │
                    └──────────────┬──────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
        ┌──────────┐         ┌──────────┐         ┌──────────┐
        │ claude   │         │ pi       │         │ hermes   │
        │ adapter  │         │ adapter  │         │ adapter  │
        └────┬─────┘         └────┬─────┘         └────┬─────┘
             │ jail + install     │ jail + install     │ jail + install
             ▼                    ▼                    ▼
        [子进程]              [子进程]              [子进程]
      native | inject       native | inject       native | inject
             │                    │                    │
             │ stdout             │ stdout             │ stdout(仅回复)
             │                    │                    │ + collect(): sessions export
             ▼                    ▼                    ▼
        ┌─────────────────────────────────────────────────┐
        │  parse()  纯函数 · 规范格式 → RunRecord          │
        └────────────────────────┬────────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │  RunRecord[]            │
                    └────────────┬────────────┘
                                 ▼
              ┌──────────────────┴──────────────────┐
              ▼                                     ▼
      ┌───────────────┐                    ┌────────────────┐
      │ 过程评估       │                    │ 质量评估        │
      │ 负向断言/轨迹  │                    │ 断言 + grader   │
      └───────┬───────┘                    └────────┬───────┘
              └──────────────┬─────────────────────┘
                             ▼
                      对比报告 + 差异声明建议
```

---

## Components

### 1. PlatformAdapter

```
PlatformAdapter {
  profile:          PlatformProfile        // 差异表的一行
  jail(dir):        { env, args, cleanup } // 构造隔离环境
  install(dir, sk): string[]               // native 模式：把 skill 放进 jail，返回追加 args
  launch(input):    RawRun                 // 起进程，拿 stdout/stderr/exitCode/durationMs
  collect(ctx):     string | null          // 进程退出后的二次抽取；无需要则返回 null
  parse(raw):       RunRecord              // 纯函数
  compensation:     string                 // 该平台的差异声明
}
```

**`install` 只在 `mode: "native"` 下调用**，且只写 jail 内部。三平台形态不同：

| 平台 | install 做什么 | 返回的 args |
|---|---|---|
| claude | `cp -r <skill> <jail>/.claude/skills/` | `[]`（靠 `--setting-sources user` 发现） |
| pi | 不复制 | `["--skill", <skill 绝对路径>]` |
| hermes | `cp -r <skill> <jail>/.hermes/skills/` | `[]`（自动发现，实测无需 `-s`） |

pi 的 `--skill` 是三者里最干净的：不落地、不依赖 HOME 重定向，`-ns --skill <path>`
即可得到「恰好一个 skill」的环境。

**`parse` 必须是纯函数** —— 不碰进程、不碰文件系统、不读环境变量。输入字符串，输出 `RunRecord`。
这是本设计唯一的硬约束，理由是它让每个平台的解析逻辑都能用真实抓下来的样本做 fixture 单测：
跑得飞快、零成本、完全确定。适配器里代码量最大、最易错的就是格式转换，而格式转换是纯函数。

**`collect` 是独立阶段，不是为某平台开的后门。** hermes 的 `-z` 只往 stdout 打最终回复文本，
工具轨迹在 SQLite session store 里，必须跑完之后 `hermes sessions export` 才拿得到。
opencode 的 `export <sessionID>` 是同一形状。claude / pi 的 `collect` 返回 `null`。

### 2. PlatformProfile（差异表）

```
PlatformProfile {
  id                  // "claude" | "pi" | "hermes"
  skillChannel        // native 通道："skill-dir" | "explicit-flag"
  builtinSkillFloor   // jail 后仍存在的内置 skill 数（claude 12，pi 0，hermes 0）
  injection           // inject 模式的注入位："append-system-prompt" | "prompt-only"
  qualityChannel      // 质量输出来源："stdout-json" | "stdout-text"
  processChannel      // 过程数据来源："inline" | "collect" | "none"
  transcriptFormat    // "claude-code-jsonl" | "pi-json"
  isolation           // 该平台的隔离手段清单
  capabilities        // Set<"tool-trace" | "usage" | "cost-cap" | "tool-allowlist"
                      //     | "structured-output" | "system-prompt-append">
}
```

**`capabilities` 不驱动运行时分派。** 它是两件事：写在代码里不会腐烂的可执行文档，
以及配合整表快照测试的回归护栏。见「Testing · L1」。

唯一例外见「风险 1」：报告渲染读它，让表错了有代价。

### 3. Runner

组装 prompt、按矩阵分发、并行执行、收集 `RunRecord`。
矩阵维度：`skill × platform × mode × repeat`。`mode` 是 `native` / `inject`（见「两种模式」），
`repeat` 用于方差标定（见「分期 · 第二期」）。默认两种模式都跑；
`--mode native` 可只跑主模式，用于日常回归。

### 4. Evaluator

两条独立路径，第二期只做过程，第三期加质量。

---

## Jail：三平台具体构造

统一形状：`mkdtemp` 一个 jail 目录 → 重定向该平台的全部配置发现根 → 环境变量**白名单**构造
→ 传入该平台关闭原生资源发现的开关 → 运行结束 `rm -rf`。

**白名单，不是黑名单。** 新出现的环境变量默认不通过。四类内容（抄 QM 的 `CLAUDE_ENV_PASSTHROUGH` 分组）：

```
PATH 与本地化   : PATH, TMPDIR, LANG, LC_ALL
TLS 与证书      : SSL_CERT_FILE, SSL_CERT_DIR, NODE_EXTRA_CA_CERTS
代理            : HTTP_PROXY, HTTPS_PROXY, NO_PROXY, ALL_PROXY
该平台自己的凭证 : （逐平台不同，见下）
```

### claude

```
env:
  HOME=<jail>
  CLAUDE_CONFIG_DIR=<jail>/.claude
  + 白名单四类
  + ANTHROPIC_API_KEY | ANTHROPIC_AUTH_TOKEN | ANTHROPIC_BASE_URL | CLAUDE_CODE_OAUTH_TOKEN

args:
  -p
  --setting-sources user           # native：让 jail 内 .claude/skills/ 可被发现
                                   # inject：同样传 user（jail 内无 skills 目录即可）
  --permission-mode bypassPermissions
  --output-format json             # 质量；stream-json 用于过程
  --max-budget-usd 0.50            # 单次运行成本硬上限，默认值，可按 eval 覆盖
  [--append-system-prompt <正文 + compensation>]   # 仅 inject 模式
  --session-id <uuid>              # 确定性会话 id，便于定位产物
```

**实测结论 1：`HOME` 重定向后认证必然失败。** jail 内即使复制了
`~/.claude/.credentials.json` 也报 `Not logged in · Please run /login`。
必须显式注入 `CLAUDE_CODE_OAUTH_TOKEN`（可从 keychain
`security find-generic-password -s "Claude Code-credentials"` 的
`claudeAiOauth.accessToken` 取），或提供 `ANTHROPIC_API_KEY`。
QM 白名单里同时列这两个变量，正是这个原因。

**实测结论 2：`--setting-sources user` + `CLAUDE_CONFIG_DIR=<jail>/.claude`
足以让 jail 内的 skill 被发现并按 description 触发。** 原方案里「传空值屏蔽全部设置源」
的写法作废——我们要的恰恰是加载 jail 的 user 源。

**实测结论 3：jail 挡不住内置 skill。** 上述配置下模型仍能列出 12 个 Claude Code
内置 skill（`dataviz` `update-config` `keybindings-help` `code-review` `simplify`
`fewer-permission-prompts` `loop` `schedule` `claude-api` `run` `init` `security-review`）。
**claude 上拿不到零 skill 基线**，`builtinSkillFloor = 12`。含义：claude 的触发测试
是「在 13 个候选中选中目标」，另两个平台是「在 1 个候选中选中目标」——
这是一个已知的不对称，报告里 claude 的触发失败必须先归因到这一格。

**`--bare` 不用。** 它的说明含「keychain reads」被跳过且认证严格走 `ANTHROPIC_API_KEY`，
与我们用 OAuth token 的路径冲突；且它跳过的东西（hooks/LSP/plugin sync/CLAUDE.md 发现）
在空 jail 里本来就不存在。留作备选，不进第一期。

### pi

```
env:
  HOME=<jail>
  + 白名单四类 + 该平台凭证

args:
  -p
  --no-skills            (-ns)   # 关闭 skill 发现——对应 QM 的 noSkills: true
  --no-extensions        (-ne)
  --no-prompt-templates  (-np)
  --no-themes
  --no-context-files     (-nc)   # 关闭 AGENTS.md / CLAUDE.md 发现
  --no-approve           (-na)   # 忽略 project-local 文件
  --offline                      # 禁用启动期网络操作
  --session-dir <jail>/sessions
  --mode json
  [--skill <skill 绝对路径>]      # native 模式
  [--append-system-prompt <正文 + compensation>]   # inject 模式
  [-t <工具白名单>]               # 可选，用于收窄工具面做对照
```

pi 的开关是三个平台里最齐全的，`-ns` 与 QM 关闭 pi 原生 skill 加载的做法逐字对应。

**实测结论：`-ns` 不影响显式 `--skill`。** 二者组合得到「恰好一个 skill」的环境，
`builtinSkillFloor = 0`，且**完全不需要 HOME 重定向**——pi 的 jail 因此是三者里最轻的。
`--append-system-prompt` 接受文件路径或字面文本两种形式，传路径可绕开长参数问题。

### hermes

```
env:
  HOME=<jail>
  + 白名单四类 + 该平台凭证

jail 内需按白名单复制三个文件：`.hermes/.env`、`.hermes/auth.json`、`.hermes/config.yaml`。

```
args (第一步 · 运行):
  -z "<任务>"                     # native；inject 模式为 "<正文 + compensation>\n---\n<任务>"
  --safe-mode                    # 隐含 --ignore-user-config + --ignore-rules
  --yolo                         # 免审批（headless 无 TTY）
  --usage-file <jail>/usage.json
  [-t <toolsets>]

args (第二步 · collect):
  hermes sessions export --format trace --session-id <id> -
```

**实测结论 1：hermes 的 jail 是三者里最干净的。** `HOME` 重定向 + 上述三个凭证文件后，
`hermes skills list` 输出 `0 hub-installed, 0 builtin, 1 local` —— 恰好只有探针 skill，
`builtinSkillFloor = 0`。

**实测结论 2：jail 内的 skill 自动被发现并按 description 触发，无需 `-s`。**
`--skills/-s` 是「preload」语义（按名字强制预载），native 模式不用它——用了就等于
绕过触发环节，那是 inject 模式的活。

**实测结论 3：`--safe-mode` 与 native 模式兼容，保留。** help 里 `--ignore-rules`
（被 `--safe-mode` 隐含）写着「skip ... and preloaded skills」，字面读像会关掉被测 skill；
实测 `--safe-mode` + jail 内 skill 仍正常发现、触发、执行。
即 "preloaded skills" 只指 `-s` 的强制预载通道，不含目录发现。
因此 `--safe-mode` 仍是三平台里最彻底的单一隔离开关。

`--usage-file` **在运行失败时也会写**，所以成本会计不会因失败丢数据。

**关键收敛点**：`sessions export --format trace` 的官方说明是
「emits Claude Code JSONL for the Hugging Face Agent Trace Viewer」——
**一个解析器同时服务 claude 和 hermes**。因此把 Claude Code JSONL 定为框架的内部规范转写格式。

---

## 两种模式

### mode: native（主）

skill 经平台原生通道加载（见 `install`），prompt 只含任务本身。
测的是端到端：**发现 → description 触发 → 执行 → 附属资源读取**。

compensation 仍然注入（走各平台的 system prompt 追加通道，hermes 拼进 `-z` 头部），
因为它声明的是工具名等平台差异，与 skill 加载通道无关。

```
prompt = <任务 prompt>
system += <compensation>        ← 可为空
```

### mode: inject（对照）

skill 正文当文本注入，短路触发环节。测的是**指令质量本身**。

```
<compensation>                  ← 该平台的差异声明，可为空
This skill directory is: <绝对路径>   ← 路径补偿，实测必需，见「决策」
<SKILL.md 正文>                  ← 去掉 YAML frontmatter
---
<任务 prompt>
```

**路径补偿行不是可选的。** 缺了它三个平台一律断锚（实测 3/3），
inject 组会因为测试装置的缺陷而全线失败，得到的差异全是伪影。

claude / pi 走 `--append-system-prompt`（前三段）+ 位置参数（任务 prompt）。
hermes 无 system prompt 追加通道，整体拼成一段走 `-z`。

**这构成一个已知的不对称**：claude/pi 的 skill 正文在 system 位，hermes 在 user 位。
`PlatformProfile.injection` 记录这个差异（`"append-system-prompt"` vs `"prompt-only"`），
报告中出现 hermes 与另两者的系统性差异时，这一格是首要怀疑对象。

不为了对称而把 claude/pi 也降级成 prompt-only —— 那会同时损失两个平台的真实性，
换来一个我们本来就能标注的变量。

### 两模式的判读

| native | inject | 结论 | 行动 |
|---|---|---|---|
| ✓ | ✓ | 该平台通过 | 无 |
| ✗ 未触发 | ✓ | description 触发词对该平台无效 | 改 frontmatter description |
| ✓ | ✗ | 正文有平台特有假设，但原生机制补上了 | 记录，低优先级 |
| ✗ | ✗ | 正文本身有问题 | 改正文 |
| ✗ 触发但执行错 | ✓ | 平台的 skill 加载机制有损耗（如截断、包装干扰） | 记录到差异表 |

第 5 行需要 `RunRecord.triggered` 区分「未触发」与「触发了但做错」，见下。

---

## RunRecord

```
RunRecord {
  // 标识
  platform, skill, task, repeat, sessionId
  mode: "native" | "inject"

  // 质量
  reply: string

  // 过程
  triggered: boolean | null   // native 模式下 skill 是否真被调用；inject 恒为 null
  toolCalls: Array<{ name, args?, ok, seq }> | null
  turns: number | null

  // 成本
  usage: {
    input, output, cacheRead, cacheWrite, totalTokens,
    costUsd: number | null
  } | null
  durationMs: number

  // 失败面
  exitCode: number
  stderr: string          // 尾部截断，上限 16KB

  // 归因
  unavailable: string[]   // 本平台拿不到的字段名，显式列出
}
```

两条设计取自 QM 的观测模型：

- **抓不到的字段显式标 `null` 并进 `unavailable`，不假装有。**
  QM 的 `HarnessLlmRequestRecord` 里 `ttftMs` / `stepGapMs` / `toolWallMs` 全是 `?` + `| null`，
  预期就是参差不齐。三平台能给的过程数据一定不一样，数据模型从一开始允许缺失。
- **`unavailable` 对应 QM 的 `residual` 思路**：承认归因不完整，单列，不摊进别的格。
  没有 residual 的归因表一定在撒谎。

`stderr` 上限 16KB 且保留**尾部** —— 抄 QM 的 codex RPC 客户端：
子进程退出码单独看没有诊断价值，要拼上 stderr 尾部才知道为什么死。

**`triggered` 的判定按平台不同，由 `parse` 从轨迹里读，不靠猜：**

| 平台 | 判据 |
|---|---|
| claude | stream-json 中出现 `Skill` 工具调用且参数含目标 skill 名 |
| pi | 轨迹中出现该 skill 的加载/调用事件 |
| hermes | `sessions export --format trace` 的 Claude Code JSONL 中同 claude |

若某平台的轨迹里根本没有可判定的信号，`triggered` 填 `null` 并把
`"triggered"` 计入 `unavailable` —— 不用「回复里有没有 skill 特征词」这类启发式凑数。
该平台因此拿不到「两模式判读」表的第 2、5 行，报告里必须显式说明这个缺口。

---

## 差异声明（compensation）

每个适配器持有一段字符串，运行时注入 prompt 头部。例：

```
pi:      ""   (暂无已知差异)
hermes:  "This platform has no AskUserQuestion tool. When the instructions call for
          asking the user a multiple-choice question, ask it as plain text instead."
```

三条约束：

1. **compensation 是数据不是代码。** 一段字符串可以被断言、被 review、被直接展示给用户。
2. **compensation 与实际映射必须有一致性测试。** QM 在这一点上有缺陷（风险 5）：
   `bridgeToolName` 的三行映射与那段人工维护的别名说明文字之间**没有任何一致性保证**，
   改了映射忘了改文字，模型会拿到过期的翻译表而无测试发现。本设计要求 compensation
   文本进整表快照断言（见 Testing · L1）。
3. **compensation 同时是产出。** 「这个 skill 要在这个平台上跑需要补什么」的答案，
   正好就是适配器注入的那段文字。适配手段与诊断结论是同一个东西——
   这是「未决问题 · 中间工具面」那条建议路线的技术基础。

---

## 过程评估

第二期只做两类**客观、一次运行即出确定结论、不需要 grader、不需要消除方差**的判定：

### 负向断言（primary）

抄 QM `system-prompt-order.test.ts` 的 `fakeSandbox.unreached` 模式 ——
**「不该被碰的东西」本身是断言，且错误消息说明违反了什么约束**。

```
声明形式（随 eval 用例给出）：
  forbid:  ["Write", "Edit"]              # 这些工具一次都不得出现
  require: ["Read"]                       # 这些工具至少出现一次
  order:   [{ before: "Read", after: "Write" }]   # Write 之前必须先有 Read
```

`order` 的判定：在 `toolCalls` 的 `seq` 序列上，每个 `after` 的出现位置之前
必须存在至少一个 `before`。首个 `after` 之前没有 `before` 即判失败。

判定依据是 `RunRecord.toolCalls`。理由：**「不该做的事」比「做得好不好」容易判定一万倍**，
且约束性指令（"不要"、"先…再…"）的跨平台遵守度差异，比生成质量的差异更大也更重要。

### 工具调用分布（secondary）

抄 QM 的 `tool_body.${string}` 思路：不只统计「共调了 12 次工具」，
按工具名细分 `Read: 5, Bash: 4, Edit: 3`。**跨平台对比时，分布差异比总次数差异信息量大得多。**

### 平台前置条件

`processChannel === "none"` 的平台，过程评估整体不适用，报告显式标注跳过原因。
这是 `capabilities` 表最先要登记的一格。

---

## 质量评估（第三期）

整套搬 `docs/explanation/skill-creator-testing-system.md` 已记录的方法论：
`evals.json` 用例定义、`eval_metadata.json` 断言、grader agent 产出 `grading.json`
（字段名 `text`/`passed`/`evidence`，viewer 依赖精确字段名）、`aggregate_benchmark.py`
聚合出 `benchmark.json` + `benchmark.md`、eval viewer 人工 review。

**只换对照轴**：`with_skill vs without_skill` → `platform_A vs platform_B`。
断言体系、grader、聚合、viewer 全部照搬。换轴改动这么小，本身是这套方法论选得对的证据。

采样次数由第二期的方差标定结果决定，不预先拍板。

---

## 目录布局

```
tools/skill-harness/
  adapters/
    claude.js         # profile + jail + launch + collect(null) + parse + compensation
    pi.js
    hermes.js
  jail.js             # 通用 jail 构造与清理
  runner.js           # 矩阵分发
  record.js           # RunRecord 规范化
  parse/
    claude-code-jsonl.js   # claude 与 hermes trace 共用
    pi-json.js
  evaluate/
    process.js        # 负向断言 + 工具分布
  report.js
  cli.js              # skill-harness run|dry-run|report
  probe/
    probe-anchor/     # 框架自身的冒烟 skill：正文 token + references/ token
      SKILL.md
      references/token.md

tests/harness/
  fixtures/
    claude/*.jsonl    # 真实抓取的样本
    pi/*.json
    hermes/*.jsonl
  parse.test.mjs      # 纯函数解析器单测（数量最多）
  profile.test.mjs    # L1 整表快照
  jail.test.mjs       # 隔离有效性负向断言
```

`probe/probe-anchor/` 是框架的自检装置，不是被测 skill。它验证「skill 的附属文件在
该平台该模式下读得到」——这个前提不成立时，任何跨平台结论都是伪影。

产物落 `$HOME/.hskill/skill-harness/<run-id>/`（遵循本仓「skill 运行时数据写 `$HOME/.hskill/<name>/`」的约定），
不写进项目目录。

---

## Testing

三层，全部确定性，零真 LLM。抄 QM 的分工：**用确定性假模型测框架本身，用真模型测 skill 内容。**

### L1 · 差异表整表快照

```js
assert.deepEqual(
  [claude, pi, hermes].map(a => a.profile.processChannel),
  ["inline", "inline", "collect"],
);
assert.deepEqual(
  [claude, pi, hermes].map(a => a.profile.skillChannel),
  ["skill-dir", "explicit-flag", "skill-dir"],
);
assert.deepEqual(
  [claude, pi, hermes].map(a => a.profile.builtinSkillFloor),
  [12, 0, 0],                      // 2026-08-14 实测；变了必须重新实测再改
);
assert.deepEqual(
  [claude, pi, hermes].map(a => a.compensation),
  [/* 三段字符串逐字 */],
);
```

**用 `deepEqual` 对整张表断言，而不是三个独立的 `equal`。** 失败时一次看到全表；
**新增平台必然让这条测试红，强制作者来这里登记**。这是注册表守卫模式。

compensation 文本进快照，解决 QM 风险 5 那个「映射与说明文字无一致性保证」的缺陷。

### L2 · 纯函数解析器单测（数量最多）

每个平台准备真实抓下来的样本，喂给 `parse()` 断言 `RunRecord`。
配套两条纪律：

- **空集合保险**：`assert.ok(fixtures.length > 0, "expected at least one fixture")`。
  抄 `skill-conformance.test.ts` 那条，防止 glob 没匹配到文件造成的假绿。
  **同理：矩阵跑了 0 个平台组合不能算通过。**
- **正向 + 负向成对**：既断言该解析出的解析出来了，也断言不该出现的没出现。

### L3 · jail 有效性负向断言

抄 `fakeSandbox.unreached`：**「不该被碰到的东西」本身就是断言。**

native 模式下 jail 内**有意**放了被测 skill，所以探针不能放在 jail 里。改为对**宿主**取证，
两条断言，都不需要往用户目录写任何东西：

1. **宿主 skill 不可见**：读一遍用户真实 `~/.claude/skills/`、`~/.hermes/skills/`、
   `~/.pi/agent/skills/` 的目录名清单，断言 `RunRecord.reply` 与 `toolCalls` 里
   一个都没出现（`builtinSkillFloor` 里那 12 个内置名除外，它们进白名单）。
2. **宿主配置不可见**：在 jail 的 `CLAUDE.md` / `AGENTS.md` 位置放一个唯一 token，
   同时断言宿主的对应文件内容特征串不出现。

错误消息直接说明违反了什么约束：

```
"jail breach: <platform> saw host skill '<name>'; the run's result is not attributable to the skill under test"
```

这条是第一期的核心验收项：jail 不成立，后面所有跨平台结论都可能是用户全局配置的假象。

### dry-run 模式

`skill-harness dry-run` 把**将要发给各平台的完整 prompt + 完整 argv + jail 内文件清单**
原样输出，不起任何进程。三平台 × 两模式 = 六份。凭证类环境变量打码。

native 模式下 prompt 里没有 skill 正文，所以 dry-run 还要打印 `install` 会往 jail 写什么，
否则这个模式在 dry-run 里近乎空白。

这条把两件事彻底解耦：**「注入内容对不对」零成本、确定性、可进 `npm test`；
「模型表现好不好」花钱、有方差、按需触发。** 没有这条分割线，
每次验证注入是否正确都要花钱跑一次真模型。抄自 QM mock harness 的 `!sysprompt` 回吐。

---

## 分期与验收

### 第一期 · 跑得起来

范围：jail + `install` + 三个适配器 × 两种模式 + dry-run + L1/L2/L3 测试。**不做任何评估。**

平台：**claude + pi + hermes**。选型理由是隔离能力，不是流行度 ——
2026-08-14 实测已确认三者都能在 jail 内走原生 skill 通道，且各自的隔离开关都够用
（`--setting-sources user` + `CLAUDE_CONFIG_DIR` / `-ns --skill` / `--safe-mode` + `HOME`）。

**第一期的 anchor probe 直接复用实测用的探针 skill**（正文一个 token、`references/` 里
一个 token），把它作为框架自身的冒烟用例固化下来：任何平台任何模式下 `FILE=UNREACHABLE`
都是框架 bug，不是被测 skill 的问题。

验收：

1. 同一个 skill + 任务，三平台 × 两模式各产出一份 `RunRecord`，`unavailable` 如实填写
2. anchor probe 在 **native 模式下三平台全部 `FILE` 通过**；inject 模式下带补偿行也全部通过
3. anchor probe 在 native 模式 + 非触发 prompt 下，三平台 `triggered` 均为 `false`
4. `dry-run` 输出六份完整 prompt（3 平台 × 2 模式），可人工核对
5. **jail 探针未被触碰**（L3 断言通过）；claude 的 `builtinSkillFloor = 12` 被 L1 快照钉住
6. `npm test` 全绿，且 L2 fixture 数 > 0

### 第二期 · 看得出差异

范围：过程评估（负向断言 + 工具分布）+ 方差标定 + 对比报告。

方差标定：固定 skill 与任务，每个平台**每种模式**重复跑 **5 次**（3 平台 × 2 模式 = 30 次），
在负向断言的通过率与工具调用分布两个维度上量出**同平台同模式的基线方差**，
再与**跨平台差异**、**跨模式差异**分别比较。

跨模式差异必须单独量：它是测试装置引入的，不是被测对象的属性。
若某平台的跨模式差异 ≥ 跨平台差异，说明该平台的两种模式在测两个不同的东西，
报告中不得把它们的结果并列。

**这个数决定第三期每个格子的采样预算。** 判据：

- 跨平台差异显著大于同平台方差 → 第三期按常规采样（每格 2-3 次）推进
- 两者同量级 → 质量评估需显著提高采样次数，或改用更稳健的指标
- 同平台方差 ≥ 跨平台差异 → 该指标不具区分度，换指标而非加样本

这是第二期要交付的判断，不预先拍板。

验收：能对一个真实 skill 给出「哪些平台违反了哪条约束性指令」的确定结论。

### 第三期 · 评得了质量

范围：搬 skill-creator 方法论换对照轴。

### 后续平台接入顺序

`codex`（本机 `vendor/aarch64-apple-darwin/codex` ENOENT 已损坏，需先重装）
→ `opencode`（`export <sessionID>` 走 collect 通道，与 hermes 同形状）
→ `cursor-agent`（`--output-format stream-json` 规范，但隔离手段只查到 `--workspace <path>`，
配置根重定向与关闭原生 skill 发现的开关待实测）
→ `openclaw`（本机无 CLI）

---

## 风险与缓解

**1. `capabilities` 表没有消费者会腐烂成谎言。**
QM 的教训：表靠一条测试守着，而这条测试断言的正是声明本身——自己证明自己。
改了适配器同时改了测试，表就脱节而无人察觉，因为没有生产路径会因它错而出错。
**缓解：报告渲染必须读它**（「本次 hermes 跳过 3 项过程断言，因该平台过程数据走 collect 通道且导出失败」），
让表错了体现在给人看的输出里。

**2. 就绪探测与输出格式依赖上游不改。**
QM 用正则匹配 opencode 的启动横幅，上游改一次措辞启动就永久超时。
我们的等价脆弱点是三个平台的 JSON 输出结构。
**缓解：L2 的 fixture 单测就是这件事的警报**；另外记录各平台版本号进 `RunRecord`，
出现批量解析失败时能立刻定位到是哪次升级。

**3. hermes 的 collect 通道有失败面。**
`sessions export` 依赖 SQLite session store 写入完成。进程退出与 store 落盘之间可能有窗口。
**缓解**：collect 失败不算整个 run 失败，`toolCalls` 置 `null` 并进 `unavailable`，质量评估照常进行。

**4. inject 模式的注入位不对称（hermes 在 user 位）。**
见「两种模式」。**缓解**：`profile.injection` 记录，报告中 hermes 的系统性差异优先归因到这一格；
第二期方差标定时对 hermes 单独看一遍。native 模式不受此影响。

**5. 跨平台差异可能被同平台方差淹没。**
LLM 输出天然有方差。**缓解**：第二期先做不受方差影响的负向断言，
质量评估推迟到方差标定完成之后，采样预算由实测决定而非预先拍板。

**6. compensation 会随平台数与工具数增长而失控。**
QM 的 `bridgeToolName` 是三行硬编码 if，三个工具三行；工具面扩大后会变成一长串。
**缓解**：见「未决问题」。短期靠 L1 整表快照锁住，长期靠让 skill 正文逐步不再需要补偿。

**7. claude 的触发测试与另两平台不可比（`builtinSkillFloor = 12`）。**
实测：jail 后 claude 仍带 12 个内置 skill，pi 与 hermes 为 0。
claude 的「触发」是 13 选 1，另两个是 1 选 1，难度不同量级。
**缓解**：`builtinSkillFloor` 进 profile 并由报告渲染读出；claude 的 `triggered = false`
必须先归因到这一格，不得直接判为 description 有问题。
若日后需要可比性，为 pi/hermes 各塞入等量的诱饵 skill 拉平候选数——第一期不做。

**8. inject 模式的正文可能被模型判为 prompt injection。**
实测中出现过一次：claude 在工作目录名为 `jail-inject` 时拒绝执行注入的 skill 正文，
明确理由是「这段文本不在我真实的 skill 列表里」。换中性目录名后不复现。
**结论限定**：n=1，且被目录名混淆，不构成定律；但它说明注入的正文在 claude 上有被当作
不可信内容的**方差风险**，而 native 模式结构上没有这个风险。
**缓解**：jail 目录名一律中性（`mkdtemp` 前缀用 `skill-harness-`，不含 jail/inject/probe 等词）；
把「拒绝执行」作为 `RunRecord` 的一个可识别失败类别，而不是混进普通质量失败。

**9. OAuth token 经环境变量传给子进程。**
claude 的 jail 必须注入 `CLAUDE_CODE_OAUTH_TOKEN`，该值会出现在子进程环境里。
**缓解**：token 只在 `jail()` 构造 env 时从 keychain 现取，不落盘、不进 `RunRecord`、
不进任何 artifact；`dry-run` 输出与报告渲染对该字段一律打码。

---

## 未决问题：中间工具面

QM 的 core 自己定义了十来个固定工具，四个 harness 被迫适配到这套工具面上，
所以 skill 正文只针对这一套写就够了 —— opencode 那边只有三个工具改名。

**本仓库没有这个中间层**，skill 直接针对 Claude Code 的工具名写。
末端补偿要补的不是「三个工具改名」，而是整套工具面语义映射。

三条路：

| 路线 | 收益 | 代价 |
|---|---|---|
| A 定义最小公共工具面词汇表，skill 正文向它对齐 | 补偿退化成 QM 那种小规模 | 波及全部 50+ skill，一次大迁移 |
| B 每适配器持大映射表 | 零迁移成本 | 维护量随「平台数 × 工具数」增长，QM 已警示会失控 |
| **C（建议）让框架产出成为迁移驱动** | 增量、可中断、优先级由实测失败自然排序 | 短期映射表与 skill 正文两边都要维护 |

**C 的依据**：适配手段与诊断结论是同一个东西。适配器注入的那段 compensation，
正好就是「这个 skill 要在这个平台上跑需要改什么」的答案。框架跑完输出
「该 skill 用了哪些平台专属构造 + 各平台的补偿文字」，逐个 skill 决定改不改；
改了的从此不需要补偿，没改的继续靠补偿跑。不用在动手前把 50 个 skill 的工具面语义想清楚。

**本 spec 采用 C，但不在第一期实现「改写建议」的产出**——第一期只保证 compensation
机制存在且被测试锁住。产出形态待第二期有真实失败样本后再定。

---

## 与现有资产的关系

- **`skills/mint/runby-opencode/`**：被本框架取代。opencode 接入后归档该 skill，
  不并存 —— 它是同一件事的手工版，保留会造成两套不一致的做法。
- **`lib/targets.js`**：不改。安装与测试是两件事，本框架不走安装路径。
- **`docs/explanation/skill-creator-testing-system.md`**：第三期的方法论来源，整套搬用换轴。
- **`knowledge/qm/`**：本设计的调研依据，两篇（机制 + 可借鉴清单）。

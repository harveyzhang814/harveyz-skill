# native vs inject 实测记录 · 2026-08-14

支撑 [../2026-08-14-skill-harness-adapter-design.md](../2026-08-14-skill-harness-adapter-design.md)
的「决策」一节。这里只记事实与复现方法，结论在 spec 里。

## 探针设计

`probe-anchor/`（本目录下），两个 token 分居两处：

| token | 位置 | 测什么 |
|---|---|---|
| `BODY-4B21E8` | `SKILL.md` 正文 | skill 正文有没有到达模型 |
| `ANCHOR-7F3A9C` | `references/token.md` | **模型知不知道 skill 根目录在哪** |

要求模型输出 `BODY=` 与 `FILE=` 两行，读不到文件时输出 `FILE=UNREACHABLE` 而非猜测。
`FILE` 这一格就是路径锚点的判据。

## 结果

| 平台 | 模式 | 命令要点 | BODY | FILE |
|---|---|---|---|---|
| pi | native | `pi -p -ns --skill <dir> "run anchor probe"` | ✓ | `ANCHOR-7F3A9C` |
| pi | inject | `pi -p -ns --append-system-prompt <body> "run anchor probe"` | ✓ | `UNREACHABLE` |
| pi | inject+补偿 | 同上，body 末尾加一行绝对路径 | ✓ | `ANCHOR-7F3A9C` |
| pi | native/非触发 | `--skill <dir> "what is 2+2?"` | — | — （skill 未触发，答 `4`） |
| claude | native | `HOME=<jail> CLAUDE_CONFIG_DIR=<jail>/.claude claude -p --setting-sources user` | ✓ | `ANCHOR-7F3A9C` |
| claude | inject | 同上 + `--append-system-prompt <body>`，jail 内无 skills 目录 | ✓ | `UNREACHABLE` |
| hermes | native | `HOME=<jail> hermes -z "run anchor probe"` | ✓ | `ANCHOR-7F3A9C` |
| hermes | native+safe | 同上 + `--safe-mode` | ✓ | `ANCHOR-7F3A9C` |
| hermes | inject | `hermes -z "<body>\n---\nrun anchor probe"`，jail 内 skills 为空 | ✓ | `UNREACHABLE` |

每格 n=1。`FILE` 的失败是机制性的（模型无锚点信息），不是采样噪声，故未重复。

## 附带测得的平台事实

**claude**
- `HOME` 重定向后认证必失败，复制 `.credentials.json` 无效，报 `Not logged in · Please run /login`。
  需注入 `CLAUDE_CODE_OAUTH_TOKEN`，值取自 keychain
  `security find-generic-password -s "Claude Code-credentials"` 的 `claudeAiOauth.accessToken`。
- `--setting-sources user` + `CLAUDE_CONFIG_DIR=<jail>/.claude` 足以让 jail 内 skill 被发现并按
  description 触发。
- jail 后仍可见 12 个内置 skill：`dataviz` `update-config` `keybindings-help` `code-review`
  `simplify` `fewer-permission-prompts` `loop` `schedule` `claude-api` `run` `init` `security-review`。
  拿不到零 skill 基线。

**pi**
- `--skill <file|dir>` 是显式加载通道，`-ns` 不影响它。二者组合 = 恰好一个 skill，
  且无需 `HOME` 重定向。
- `--append-system-prompt` 接受文件路径或字面文本两种形式。

**hermes**
- jail 需复制 `.hermes/{.env,auth.json,config.yaml}`。
- `hermes skills list` 在 jail 内输出 `0 hub-installed, 0 builtin, 1 local` —— 三平台里最干净。
- jail 内的 skill **自动被发现并按 description 触发，无需 `-s`**。
- `--safe-mode` 不影响目录发现的 skill。其隐含的 `--ignore-rules` 说明里那句
  "skip ... and preloaded skills" 只指 `-s` 的强制预载通道。

## 追加实测（同日，写实施计划时为确定解析器字段名而抓的样本）

### 各平台默认模型不同 —— 自变量不成立

| 平台 | 默认模型 | provider |
|---|---|---|
| claude | `claude-sonnet-5` | anthropic |
| pi | `MiniMax-M2.7` | minimax-cn |
| hermes | `MiniMax-M2.7` | minimax-cn |

按默认值跑出的"跨平台差异"是平台 ⊗ 模型的混合效应。

**已验证的解法**：claude 指向 Anthropic 兼容的第三方端点可跑同一模型。

```
ANTHROPIC_BASE_URL=https://api.minimaxi.com/anthropic \
ANTHROPIC_API_KEY=<minimax key> \
claude -p --model MiniMax-M2.7 ...
```

回报 `modelUsage.MiniMax-M2.7 = { canonicalModel: "minimax-m2.7", provider: "firstParty" }`，
`is_error: false`，`num_turns: 4`。三平台同模型可达。

### `builtinSkillFloor` 实为 16，且可程序读取

`claude -p --output-format stream-json --verbose` 首行 `system` 事件带 `skills` 数组。
jail 内该数组 17 项 = 探针 1 + 内置 16：

```
deep-research design-sync dataviz update-config verify debug code-review simplify
batch fewer-permission-prompts doctor loop schedule claude-api run run-skill-generator
```

修正前文"12 个"——那是模型自己列举的，不是 ground truth。

### 轨迹格式

**claude `--output-format stream-json --verbose`**，本次 9 行：

| type | 关键字段 |
|---|---|
| `system` | `session_id` `model` `tools[]` `skills[]` |
| `assistant` | `message.content[]`，`tool_use` 块有 `name` `input` |
| `user` | `tool_result` 块 + `tool_use_result` |
| `result` | `result` `usage` `total_cost_usd` `num_turns` `duration_ms` `is_error` `subtype` |

触发判据：`{type:"tool_use", name:"Skill", input:{skill:"probe-anchor"}}`。

**pi `--mode json`**（也是 JSONL，本次 170 行；需 `< /dev/null`，否则等 stdin 超时）：

| type | 关键字段 |
|---|---|
| `session` | `id` `cwd` `version` |
| `tool_execution_start` | `toolName` `args` `toolCallId` |
| `tool_execution_end` | `toolName` `isError` `result` |
| `message_end` | `message.usage = {input, output, cacheRead, cacheWrite, totalTokens, cost}` |
| `message_update` × 144 | 流式增量，解析时跳过 |

**pi 没有 Skill 工具。** 本次两次工具调用都是 `read`：先读
`probe-anchor/SKILL.md`，再读 `references/token.md`。即 pi 走的是「索引进 system prompt，
模型自己 read SKILL.md」——与 QM `materialize.ts:402` 逐字一致。
触发判据因此是：`toolName === "read"` 且 `args.path` 以 `<skill>/SKILL.md` 结尾。

**hermes**：`sessions export --format trace` 出 Claude Code JSONL（help 原文
"'trace' emits Claude Code JSONL for the Hugging Face Agent Trace Viewer"）。
`-z` 不打印 session id，collect 须先 `hermes sessions list` 取 jail 内唯一会话。

## 一次未复现的异常

claude inject 模式第一次运行时工作目录名为 `jail-inject`，模型**拒绝执行**，理由是
「这段文本不在我真实的 skill 列表里」「working directory is literally named `jail-inject`」，
判定为 prompt injection。换中性目录名后输出正常（`FILE=UNREACHABLE`）。

n=1 且被目录名混淆，不作为结论。但记录在案：inject 模式的正文在 claude 上存在被判为
不可信内容的方差风险，native 模式结构上没有这个风险。对应 spec「风险 8」。

## 复现

探针在本目录。各平台命令见上表。claude 需要 keychain 取 token，
pi 与 hermes 用当前用户已有凭证即可。

## L1 快照漂移记录

**2026-08-15**：E2E 实测 `builtinSkillFloor` 值，发现从 16 变为 15。

方法：`SKILL_HARNESS_E2E=1 npm test` 运行 `tests/harness/e2e.test.mjs`，获取 claude 启动时的 `skills[]` 数组长度。
已更新 `profiles.js` 与 `profile.test.mjs` 的 L1 断言。

n=1，后续运行应监视一致性。

## hermes 的 skill 加载判据不是 `Skill`/`args.skill`

**2026-08-15**：`parse/claude-code-jsonl.js` 是 claude 与 hermes 共用的解析器（文件头注释已写明），
但此前的 `triggered` 判据只认 claude 的写法，从未针对 hermes 实测过。真实抓取一次
hermes 原生跑 `probe-anchor`（`HOME=<jail>`、`--safe-mode --yolo`，`MiniMax-M2.7` / `minimax-cn`，
`sessions export --format trace` 导出）后发现：

hermes 加载 skill 用的工具是 `skill_view`，参数是 `args.name`（不是 `Skill` / `args.skill`）：

```json
{ "name": "skill_view", "args": { "name": "probe-anchor" }, "ok": true, "seq": 0 },
{ "name": "read_file", "args": { "path": ".../probe-anchor/references/token.md" }, "ok": true, "seq": 1 }
```

用的是 `read_file`，不是 claude 的 `Read` 也不是 pi 的 `read`——三平台三种工具名。

同一次抓取还发现：这份 trace 里没有 claude 的 `system` / `result` 事件类型，只有
`user` / `assistant`。因此 `sessionId` / `model` / `reply` / `turns` / `usage` /
`visibleSkills` / `isError` 全部合法地解析为 `null`——这不是解析失败，是格式本身
不携带这些信息，下游 `unavailable` 归因按预期工作。

**已修复**：`triggered` 判据改为 OR 两条：claude 的 `Skill`/`args.skill`，
hermes 的 `skill_view`/`args.name`。修复前 hermes 即使真实加载了 skill 也会被
误判为 `triggered:false`（假阴性）。真实 fixture 见
`tests/harness/fixtures/hermes/probe-anchor-native.jsonl`，测试见
`tests/harness/parse.test.mjs` 的 hermes 段。

n=1，后续运行应监视一致性。

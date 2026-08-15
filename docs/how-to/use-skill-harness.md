# 如何使用 skill-harness：跨平台 skill 测试框架

`tools/skill-harness/` 让同一个 skill 在 `claude` / `pi` / `hermes` 三个平台上，以 native（走平台原生 skill 通道）与 inject（正文注入系统提示，作对照）两种模式各跑一次，产出结构一致的运行记录，用来判断 skill 在不同平台上的加载/触发行为是否一致。

---

## 什么时候用

- 想知道某个 skill 在 pi / hermes 上是否也能被正确加载和触发
- 想预览一次跨平台测试实际会发送什么 argv、环境变量、prompt，但不想真的花钱跑
- 想知道哪些 skill 还没在某个平台上被真实测过、或测过的结论已经过期
- 想把某个 skill 声明为不参与这套矩阵测试（比如它本身就是驱动别的平台的 skill）

**第一期范围提醒**：本框架目前只验证"跨平台适配是否work"（触发、jail 隔离、字段解析），不做任何质量/正确性评估——那是后续阶段的工作。

---

## 前置要求

- 从仓库根目录运行所有命令（`node tools/skill-harness/cli.js ...`）。
- `--model` 必填，`run` / `dry-run` 缺了会直接报错退出——刻意不给平台默认值，避免"平台差异"其实是"模型差异"混进结果。
- 真的执行 `run`（不是 `dry-run`）需要真实凭证：
  - `claude`：从 macOS keychain 读取 OAuth token（`security find-generic-password -s "Claude Code-credentials"`），本机需已登录过 `claude`。
  - `hermes`：从 `~/.hermes/.env` 读取 `MINIMAX_CN_API_KEY`。
  - 若用 `--base-url` 让 `claude` 也走 minimax 端点（见下），则 claude 也读同一个 `MINIMAX_CN_API_KEY`，不需要 keychain。
- 真实运行会产生真实 API 调用与费用。

---

## 四个子命令

```bash
node tools/skill-harness/cli.js dry-run --model <model> [选项]
node tools/skill-harness/cli.js run     --model <model> [选项]
node tools/skill-harness/cli.js report  [--model <model>]
node tools/skill-harness/cli.js coverage
```

### 通用选项

| flag | 说明 |
|---|---|
| `--model <name>` | 必填（`run`/`dry-run`），如 `MiniMax-M2.7` |
| `--provider <name>` | 传给 `pi`/`hermes` 的 `--provider`，如 `minimax-cn` |
| `--base-url <url>` | 让 `claude` 改走第三方端点（如 `https://api.minimaxi.com/anthropic`），配合 `--model` 实现三平台跑同一个模型 |
| `--skill <path>` | 可重复；只影响矩阵里哪些格子标记为"本次要跑"，**不改变实际执行的 skill 内容**（见下方「重要限制」） |
| `--bundle <name>` | 可重复；按 `skills-index.json` 的 bundle 字段筛选，同样只影响矩阵标记 |
| `--platform <claude\|pi\|hermes>` | 可重复；只测指定平台 |
| `--mode <native\|inject\|both>` | 默认 `both` |
| `--task <text>` | 自定义任务文本，默认 `run anchor probe` |

---

## 常见任务

### 1. 预览一次跑会发生什么（不花钱）

```bash
node tools/skill-harness/cli.js dry-run --model MiniMax-M2.7 --provider minimax-cn --skill mint/learn-skill
```

输出 6 段（3 平台 × 2 模式），每段包含完整 argv、打码后的环境变量、`systemAppend`、positional prompt。native 模式的段会额外打印 `jail writes:`（会话隔离目录里将被写入的文件路径），因为 native 模式的 prompt 本身不含 skill 正文——不看这一行会觉得输出是空的。

### 2. 真实跑一次

```bash
node tools/skill-harness/cli.js run --model MiniMax-M2.7 --provider minimax-cn --skill mint/learn-skill
```

跑完直接打印三态报告（pass / fail / n/a / 空白）。产物落在 `$HOME/.hskill/skill-harness/<run-id>/`（`records.json` + `cells.json`），不写进项目目录。

### 3. 查看历史覆盖情况

```bash
node tools/skill-harness/cli.js coverage
```

对 `skills-index.json` 里全部 skill 输出完整三态矩阵：`never`（没跑过）/ `NdⓍ`（N 天前跑过，内容未变）/ `NdⓍ·陈`（跑过但 skill 内容已改，结论过期）。永远显示完整矩阵，未跑过的格子绝不会伪装成通过。

### 4. 查看最近一次真实运行的报告

```bash
node tools/skill-harness/cli.js report
```

读最近一次 `run` 落盘的记录重新渲染报告，不重新执行。

### 5. 把某个 skill 声明为不参与矩阵

编辑 `tools/skill-harness/matrix.json`：

```json
{
  "overrides": [
    {
      "skill": "mint/runby-opencode",
      "platforms": [],
      "reason": "这个 skill 的作用就是驱动 opencode 去跑别的 skill，被测对象是 opencode 而不是它自己"
    }
  ]
}
```

`reason` **必填**，缺失或空白会让 `npm test` 直接变红——一条没写理由的排除和"忘了测"必须能区分开。`platforms: []` 表示全平台排除；也可以只列出部分平台白名单。

---

## 重要限制：Phase 1 只实际执行 probe-anchor 探针 skill

`--skill` / `--bundle` **只决定矩阵里哪些格子被标记为"本次运行范围"**，用于 `coverage` 记账和 `report` 的行标签——`dry-run` / `run` 实际发送给平台的 skill 内容，第一期**永远是** `tools/skill-harness/probe/probe-anchor/`（框架自带的自检探针 skill），与 `--skill` 传的值无关。

也就是说，`dry-run --skill mint/learn-skill` 的输出标题会写 `mint/learn-skill`，但 argv/prompt 里实际的 skill 正文是探针 skill 的内容。这是刻意的第一期设计——"跑真实业务 skill 内容"是后续阶段的评估逻辑，第一期只验证框架本身（触发判据、jail 隔离、字段解析）能不能在三个平台上正确工作。

---

## 不在此 skill 范围内

- 质量/正确性评估、grader、负向断言判定——Phase 2/3 的工作
- `codex` / `opencode` / `cursor-agent` 等其他平台——第一期只覆盖 `claude` / `pi` / `hermes`
- 往 `~/.claude/skills/`、`~/.hermes/skills/`、`~/.pi/agent/skills/` 等真实用户目录写任何东西——所有运行都在隔离的临时 jail 目录里进行
- `--repeat` 目前只解析不生效（Phase 2 语义，传 `1` 以外的值会报错，不会被静默忽略）

---

## 相关文档

- [reference/testing-guide.md](../reference/testing-guide.md) — 测试文件分层、fixture 来源、L1 快照更新纪律（末尾 `tests/harness/` 一节）
- [../superpowers/specs/2026-08-14-skill-harness-adapter-design.md](../superpowers/specs/2026-08-14-skill-harness-adapter-design.md) — 设计依据与三平台差异分析
- [../superpowers/specs/measurements/2026-08-14-native-vs-inject.md](../superpowers/specs/measurements/2026-08-14-native-vs-inject.md) — 全部实测记录、fixture 复现命令

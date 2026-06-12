---
name: opencode-runner
description: "Use opencode as an independent AI agent to verify a Claude skill's instruction logic, or A/B compare Claude vs opencode following the same skill instructions. Trigger when user says: verify this skill with opencode, validate skill logic, use opencode to check this skill, compare Claude vs opencode on this skill, 用 opencode 验证 skill 指令, 让 opencode 独立验证这个 skill. Always use this skill when the user mentions opencode and skill validation together."
user_invocable: true
version: "1.0.0"
---

# opencode-runner

将 SKILL.md 的指令内容作为任务说明传给 opencode，让它作为**独立 AI agent** 执行——不依赖 Claude Code 的 skill 加载机制，而是验证 skill 的自然语言指令本身是否足够清晰、在不同 AI 下是否产出一致结果。

> **定位说明**：这不是"让 opencode 运行 Claude skill"，而是"把 skill 指令当成 prompt，用 opencode 做独立验证"。如果两个 AI 都能按指令产出正确结果，说明 skill 的逻辑表达是健壮的。

---

## 前置检查

```bash
which opencode   # 必须可用
which jq         # 用于解析 JSON 输出
```

若 opencode 未安装，路径通常在 `~/.opencode/bin/opencode`；可用 `npm i -g opencode` 安装。

---

## 参数收集

运行前确认：

| 参数 | 说明 | 获取方式 |
|------|------|---------|
| **skill 路径** | 包含 SKILL.md 的目录绝对路径 | 用户提供，或在 `~/.claude/skills/` / 仓库 `skills/` 下查找 |
| **task prompt** | 要测试的 prompt | 用户提供 |
| **模式** | `execute`（仅 opencode） 或 `compare`（Claude vs opencode） | 见下方模式说明 |

**查找已安装的 skill：**
```bash
ls ~/.claude/skills/<skill-name>/SKILL.md
# 或仓库内（用 find 搜索）
find ~/Projects/harveyz-skill/skills -name "SKILL.md" -path "*<skill-name>*"
```

---

## 模式 1：Verify — 用 opencode 独立验证 skill

将 SKILL.md 作为指令文本传给 opencode，让它按内容完成任务，验证指令逻辑是否清晰可执行。

### 执行步骤

**Step 1** — 收集任务相关上下文

opencode 是独立进程，不共享当前对话历史。只传与任务直接相关的内容：

| 传什么 | 怎么传 |
|--------|--------|
| Skill 指引 | `--file <skill-path>/SKILL.md` |
| 任务所需的参考文件（如转录稿、数据文件） | 额外的 `--file <file>` |
| 简短的行内上下文（<200字） | 直接写在 prompt 里 |

**不要传**：整段对话历史、无关的背景信息。

**Step 2** — 构造并运行：

```bash
opencode run --format json \
  --file "<skill-path>/SKILL.md" \
  [--file "<context-file-if-needed>"] \
  -- "The first attached file contains skill instructions. Follow them to complete this task: <user-task-prompt>" \
  2>&1 | tee /tmp/opencode-run-output.jsonl
```

> **为什么用 `--file` + `--`：** 直接在命令行展开多行 shell 变量容易被 shell 截断或转义出错；`--file` 让 opencode 直接读文件内容；`--` 明确告诉参数解析器后面的是 positional message 而非 flag 值。

**Step 2** — 提取响应文本：

```bash
cat /tmp/opencode-run-output.jsonl | \
  jq -r 'select(.type == "text") | .part.text' | \
  paste -sd '' -
```

**Step 3** — 提取 token 用量：

```bash
cat /tmp/opencode-run-output.jsonl | \
  jq 'select(.type == "step_finish") | .part.tokens'
```

**Step 4** — 向用户展示结果：
- opencode 的完整输出文本
- token 用量（input / output / total）
- 询问：「opencode 是否正确理解并执行了 skill 的指令？如果没有，是哪部分指令不够清晰？」

---

## 模式 2：Compare — Claude vs opencode 独立性验证

同一份 skill 指令 + 相同 prompt，分别交给 Claude subagent 和 opencode 独立执行，对比输出一致性。两者都产出正确结果 = skill 指令健壮；只有一方正确 = 指令存在歧义需要改进。

### 执行步骤

**Step 1** — 在同一轮内并行启动两个任务：

**Claude subagent**（使用 Agent 工具，同一 turn 内发起）：
```
读取 <skill-path>/SKILL.md，严格按照其中的指引完成以下任务：
<task-prompt>

将你的最终输出保存到 /tmp/opencode-ab/claude-output.md
```

**opencode**（使用 Bash 工具，同一 turn 内并行）：
```bash
mkdir -p /tmp/opencode-ab
opencode run --format json \
  --file "<skill-path>/SKILL.md" \
  [--file "<context-file-if-needed>"] \
  -- "The first attached file contains skill instructions. Follow them to complete this task: <task-prompt>" \
  2>&1 | tee /tmp/opencode-ab/opencode-output.jsonl
```

**Step 2** — 等待两者完成，收集结果：

```bash
# Claude 输出（subagent 已写入文件）
cat /tmp/opencode-ab/claude-output.md

# opencode 文本输出
cat /tmp/opencode-ab/opencode-output.jsonl | \
  jq -r 'select(.type == "text") | .part.text' | paste -sd '' -

# opencode token 用量
cat /tmp/opencode-ab/opencode-output.jsonl | \
  jq 'select(.type == "step_finish") | .part.tokens'
```

**Step 3** — 用以下格式展示对比：

```
## A/B 对比结果：<skill-name>

**Prompt：** <task-prompt>

---

### Claude 输出
<claude-output>

---

### opencode 输出
<opencode-output>

---

### 对比摘要

| 维度 | Claude | opencode |
|------|--------|----------|
| 输出字数 | X | Y |
| Token 用量 | 未统计 | M total |
| 遵循 skill 指引 | 评估... | 评估... |
| 主要差异 | ... | ... |
```

**Step 4** — 引导用户分析：
- 两者都正确 → skill 指令表达清晰，逻辑健壮
- 仅一方正确 → 找出哪段指令产生了歧义，建议修改
- 两者都偏差 → skill 的核心意图表述需要重写

---

## 注意事项

- **权限提示**：opencode 在非交互模式下遇到权限询问会阻塞。若 skill 涉及文件操作，考虑加 `--dangerously-skip-permissions`（仅限受信任的 skill）
- **工具差异**：部分 Claude skill 依赖 Claude Code 特有的工具（如 `Edit`、`Write`）。opencode 有自己的工具集，行为可能不同——这正是 A/B 对比有价值的地方
- **长输出**：opencode 的 JSON 流是逐步输出的，`tee` 保存完整流，最后再用 `jq` 提取文本

---

## 输出文件路径

| 文件 | 说明 |
|------|------|
| `/tmp/opencode-run-output.jsonl` | Execute 模式原始 JSON 流 |
| `/tmp/opencode-ab/opencode-output.jsonl` | Compare 模式 opencode 原始输出 |
| `/tmp/opencode-ab/claude-output.md` | Compare 模式 Claude subagent 输出 |

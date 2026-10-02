---
name: runby-opencode
description: "Use opencode as an independent AI agent to verify a skill's instruction logic, or A/B compare Claude vs opencode following the same skill. Trigger when user says: verify this skill with opencode, validate skill logic, use opencode to check this skill, compare Claude vs opencode on this skill. Always use this skill when the user mentions opencode and skill validation together."
user_invocable: true
version: "1.1.1"
---

# opencode-runner

让 opencode 通过原生 skill 机制加载并执行待测 skill，验证其指令逻辑；仅在 `compare` 模式下与 Claude 的执行结果比较。

> **定位**：不是把 SKILL.md 当上下文喂给 opencode，而是让 opencode 真正加载这个 skill，触发它自己的 skill 机制来完成任务。`verify` 只评价 opencode 一端；`compare` 才评价 Claude 与 opencode 的差异。

---

## 前置检查

```bash
which opencode   # 必须可用
which jq         # 用于解析 JSON 输出
```

---

## 参数收集

| 参数 | 说明 | 获取方式 |
|------|------|---------|
| **skill 路径** | 包含 SKILL.md 的目录绝对路径 | 用户显式提供时优先；否则查仓库 `skills/` 或经用户确认的目标安装目录 |
| **task prompt** | 要测试的 prompt | 用户提供 |
| **模式** | `verify`（仅 opencode） 或 `compare`（Claude vs opencode） | 见下方说明 |

---

## Step 1：确认 skill 来源与 opencode 可发现性

先确认选定源目录包含 `SKILL.md`，记录其绝对路径和版本。用户显式提供的路径优先；未提供时，先查仓库 `skills/`，再查用户确认过的安装目录，不把 Claude 安装目录当默认值。

然后检查当前 opencode 实际使用的 skill 搜索位置或配置，确认所选 skill 能被 opencode 发现。若尚不可发现，报告源目录与缺口，向用户提出安装到 opencode target 或配置搜索路径的方案；未经用户确认不修改 opencode 配置，也不把「文件存在」当成「已加载」。挂载 Claude 安装目录只是在用户明确选择该来源时的可选方案，不是通用前置条件。

---

## 模式 1：Verify — 用 opencode 独立验证

确认可发现后，让 opencode 通过原生 skill 触发机制执行任务。

```bash
opencode run --format json \
  -- "<task prompt — 用会触发该 skill 的自然语言描述>" \
  2>&1 | tee /tmp/opencode-verify-output.jsonl
```

提取输出：
```bash
cat /tmp/opencode-verify-output.jsonl | \
  jq -r 'select(.type == "text") | .part.text' | paste -sd '' -

# token 用量
cat /tmp/opencode-verify-output.jsonl | \
  jq 'select(.type == "step_finish") | .part.tokens'
```

向用户展示结果后询问：「opencode 是否触发了该 skill？输出是否符合预期？如果没有触发，说明 skill 的 description 触发词需要调整。」

---

## 模式 2：Compare — Claude vs opencode 独立性验证

同一 prompt，Claude subagent 和 opencode 并行运行，对比输出一致性。

先确认当前会话有可用的 Claude 执行端，且两端都能加载同一版本的 skill。缺少 Claude 或 opencode 任一端时，说明缺口并停止 `compare`；不得将单端 `verify` 冒称比较结果，也不擅自改用户配置补齐另一端。

**在同一轮内并行启动：**

**Claude subagent**（Agent 工具）：
```
使用 skill：<skill-path>
任务：<task-prompt>
将最终输出保存到 /tmp/opencode-ab/claude-output.md
```

**opencode**（Bash 工具，同一 turn）：
```bash
mkdir -p /tmp/opencode-ab
opencode run --format json \
  -- "<task-prompt>" \
  2>&1 | tee /tmp/opencode-ab/opencode-output.jsonl
```

收集结果后，用以下框架分析：

| 结果 | 诊断 |
|------|------|
| 两者输出一致 ✓ | Skill 指令健壮，触发词清晰 |
| 仅 Claude 正确 | Skill description 对 opencode 触发不足，或指令有 Claude 特有假设 |
| 仅 opencode 正确 | Claude 侧可能存在 skill 加载问题，或测试 prompt 有误 |
| 两者都偏差 | Skill 核心意图表述需要重写 |

---

## 输出文件路径

| 文件 | 说明 |
|------|------|
| `/tmp/opencode-verify-output.jsonl` | Verify 模式原始 JSON 流 |
| `/tmp/opencode-ab/opencode-output.jsonl` | Compare 模式 opencode 原始输出 |
| `/tmp/opencode-ab/claude-output.md` | Compare 模式 Claude subagent 输出 |

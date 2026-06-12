---
name: opencode-runner
description: "Use opencode as an independent AI agent to verify a Claude skill's instruction logic, or A/B compare Claude vs opencode following the same skill. Trigger when user says: verify this skill with opencode, validate skill logic, use opencode to check this skill, compare Claude vs opencode on this skill, 用 opencode 验证 skill, 让 opencode 独立验证这个 skill. Always use this skill when the user mentions opencode and skill validation together."
user_invocable: true
version: "1.1.0"
---

# opencode-runner

将 Claude skill 安装到 opencode 的 skill 目录，让 opencode 通过原生 skill 机制加载并执行——验证 skill 指令逻辑在不同 AI 下是否健壮。

> **定位**：不是把 SKILL.md 当上下文喂给 opencode，而是让 opencode 像 Claude Code 一样真正加载这个 skill，触发它自己的 skill 机制来完成任务。两者都能正确执行 = skill 指令健壮；结果有差异 = 找到了需要改进的歧义点。

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
| **skill 路径** | 包含 SKILL.md 的目录绝对路径 | 用户提供，或在 `~/.claude/skills/` / 仓库 `skills/` 下查找 |
| **task prompt** | 要测试的 prompt | 用户提供 |
| **模式** | `verify`（仅 opencode） 或 `compare`（Claude vs opencode） | 见下方说明 |

---

## Step 1：安装 skill 到 opencode

opencode 的 skill 格式与 Claude Code 完全兼容（相同的 YAML frontmatter），存放路径为 `~/.config/opencode/skills/<name>/`。

```bash
SKILL_NAME=$(grep '^name:' "<skill-path>/SKILL.md" | head -1 | sed 's/name: *//' | tr -d '"')
OPENCODE_SKILL_DIR="$HOME/.config/opencode/skills/${SKILL_NAME}"

mkdir -p "${OPENCODE_SKILL_DIR}"

# 软链接：Claude skill 更新时 opencode 侧自动同步
ln -sf "<skill-path>/SKILL.md" "${OPENCODE_SKILL_DIR}/SKILL.md"

# 若 skill 有 references/ 或 scripts/ 子目录，一并链接
for subdir in references scripts assets; do
  [ -d "<skill-path>/${subdir}" ] && ln -sf "<skill-path>/${subdir}" "${OPENCODE_SKILL_DIR}/${subdir}"
done

echo "Installed: ${OPENCODE_SKILL_DIR}"
```

---

## 模式 1：Verify — 用 opencode 独立验证

安装完成后，让 opencode 通过原生 skill 触发机制执行任务。

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

## 卸载

测试完成后若不需要保留：
```bash
rm -rf "$HOME/.config/opencode/skills/${SKILL_NAME}"
```

---

## 输出文件路径

| 文件 | 说明 |
|------|------|
| `/tmp/opencode-verify-output.jsonl` | Verify 模式原始 JSON 流 |
| `/tmp/opencode-ab/opencode-output.jsonl` | Compare 模式 opencode 原始输出 |
| `/tmp/opencode-ab/claude-output.md` | Compare 模式 Claude subagent 输出 |

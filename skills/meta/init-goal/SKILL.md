---
name: init-goal
version: "1.3.0"
description: "Generate a structured /loop Goal Prompt through guided dialogue. Parses user's initial message to auto-fill known fields and match the best template, then clarifies only what's missing (depth-first, one question at a time). Outputs the Goal Prompt as text — the skill writes no files; the loop agent persists prompt.md/log.md/summary.md during execution per the embedded rules. Triggers: user says /init-goal, 'initialize a loop goal', 'set up a GOal', 'help me use /loop to accomplish X', or describes a repetitive autonomous task they want Claude to run in a loop."
user_invocable: true
---

# init-goal

对话式向导，帮助用户为 `/loop` 命令生成一段结构化的 **Goal Prompt 文本**。

**这个 skill 的唯一产物就是这段 Goal Prompt 文本。** 它内含「执行期间维护文档」的规则——这些规则是写给跑 loop 的 agent 的指令，由那个 agent 在执行 loop 时落盘三个文件。**init-goal 自己不创建任何目录、不写任何文件。**

执行期间由 loop agent 生成的文件（slug 取自 GOAL）：
- `~/.hskill/init-goal/<goal-slug>/prompt.md`（agent 首轮存档，静态不变）
- `~/.hskill/init-goal/<goal-slug>/log.md`（agent 每轮追加）
- `~/.hskill/init-goal/<goal-slug>/summary.md`（agent 退出时生成）

**规则：每次只发一条消息，等用户回复后再继续。**

---

## Step 0 — 解析输入，自动填充，深度优先澄清

### 0a: 解析

从用户的初始消息中提取所有已知信息，填入对应字段：

| 字段 | 提取什么 |
|---|---|
| GOAL | 用户想达成的目标，含成功标准 |
| EXECUTION | 用户描述的每轮步骤或动作 |
| EVAL | 用户提到的衡量进展的方式 |
| CONSTRAINTS | 用户提到的限制（不能改什么、最多多少轮…） |
| EXIT_EXPLICIT | 用户提到的停止条件 |
| EXIT_FALLBACK | 用户提到的兜底行为 |

### 0b: 匹配模版

根据用户描述，选最匹配的模版：

| 匹配信号 | 模版 |
|---|---|
| 测试 / test / bug / 修复 / fix | Fix Until Green |
| 研究 / 搜索 / 信息收集 / search | Research Loop |
| 优化 / 改进 / 迭代 / refine / 润色 | Refine Until Satisfied |
| 监控 / 检查状态 / watch / monitor | Monitor & React |
| 探索 / 代码库 / 结构 / map / 未知领域 | Explore & Map |
| 无明显匹配 | 从零开始（所有字段留空） |

匹配后，读取 `references/templates.md` 获取该模版的字段默认值，填充所有**用户未提供**的字段。置信度高时直接套用，不问用户确认模版名称。

### 0c: 深度优先澄清

按以下优先级，逐一澄清**缺失或不够具体**的字段。每次只问一个，等回复后再判断是否还需要继续问。

**优先级（从高到低）：**

1. **GOAL** — 如果目标不够具体（缺少成功标准、范围不清楚），先把这个搞清楚。其他一切从 GOAL 派生。
2. **EXIT_EXPLICIT** — 如果用户没有明确说"达到什么状态停止"，问这个。这是 loop 的终点，必须清晰。
3. **CONSTRAINTS** — 如果用户提到了限制但不完整（比如"不能改某些文件"但没说具体哪些），确认一下。
4. **EXECUTION** — 如果模版默认步骤明显不适用当前场景，才问。通常不需要问。
5. **EVAL / EXIT_FALLBACK** — 几乎不需要问；模版默认值在绝大多数情况下够用。

**什么时候停止澄清：**
- GOAL 足够具体（有明确的成功标准）
- EXIT_EXPLICIT 已知
- 其余关键字段都有合理的值（用户提供的或模版默认值）

澄清完成后，进入 Step 1。

---

## Step 1 — 展示预填摘要，确认

展示所有字段的当前值（用户已提供的 + 模版默认值），一次性呈现：

---
**这是根据你的描述整理的 loop 配置，请确认：**

**目标：** [GOAL]

**每轮执行：**
[EXECUTION]

**评估指标：** [EVAL]

**约束：** [CONSTRAINTS]

**退出条件：**
- 明确：[EXIT_EXPLICIT]
- 兜底：[EXIT_FALLBACK]

---

询问：「确认后直接生成文件，或告诉我需要调整哪个字段。」

若用户要调整，只修改被指出的字段，重新展示摘要。直到用户确认。

---

## Step 2 — 生成并输出 Goal Prompt 文本

这一步**不写任何文件**。init-goal 的产物就是下面这段文本——把它生成出来，直接展示给用户，由用户拿去喂给 `/loop`。文本里的 `## 文档维护` 段是写给执行 loop 的 agent 的指令，三个文档由那个 agent 在跑 loop 时落盘。

**先生成 goal-slug：**
若 GOAL 是英文，转为 kebab-case（小写 + 连字符），截取前 40 字符。
若 GOAL 是中文，生成一个简短的英文描述（5-8 个单词，kebab-case）。
把生成的 slug 填进下面文本里所有 `[goal-slug]` 占位处。

**生成并展示这段 Goal Prompt 文本**（占位符全部替换为实际值后呈现）：

```markdown
## GOal

[GOAL]

## 每轮执行

[EXECUTION]

## 评估（每轮末尾）

[EVAL]

## 约束

[CONSTRAINTS]

## 退出条件

- 明确条件：[EXIT_EXPLICIT]
- 兜底逻辑：[EXIT_FALLBACK]

## 文档维护（由运行本 loop 的 agent 负责，工作目录 ~/.hskill/init-goal/[goal-slug]/）

- **首轮：** 若 prompt.md 不存在，`mkdir -p` 工作目录并把本 prompt 完整存为 prompt.md（静态存档，之后不改）。
- **每轮：** 开始前读 log.md 末条 Round 获取上下文（首轮无则跳过）；结束时向 log.md 追加一条 `### Round N — YYYY-MM-DD HH:MM`，含三行——执行内容 / 评估结果 / 下一轮建议。
- **退出时**（明确条件 / 兜底 / 用户中断）：在同目录写 summary.md，含——目标、结果（一句话）、关键轮次、退出原因、总轮数、可选下一步。
```

**展示完文本后，附上启动说明：**

---
✅ Goal Prompt 已生成（如上）。复制整段，启动 loop（interval 自选）：

```
/loop <interval> <粘贴上面整段 Goal Prompt>
```

首轮运行时，loop agent 会按 `## 文档维护` 的指令把它存为 `~/.hskill/init-goal/[goal-slug]/prompt.md`，每轮追加 `log.md`，结束时写 `summary.md`。

---

---
name: init-goal
version: "1.1.0"
description: "Generate a structured /loop prompt file through guided dialogue. Parses user's initial message to auto-fill known fields and match the best template, then clarifies only what's missing (depth-first, one question at a time). Saves prompt.md to ~/.hskill/init-goal/<goal-slug>/. Triggers: user says /init-goal, 'initialize a loop goal', 'set up a GOal', 'help me use /loop to accomplish X', or describes a repetitive autonomous task they want Claude to run in a loop."
user_invocable: true
---

# init-goal

对话式向导，帮助用户为 `/loop` 命令生成结构化的初始化 prompt 文件。

输出：`~/.hskill/init-goal/<goal-slug>/prompt.md`（静态，loop 不修改）
过程记录：`~/.hskill/init-goal/<goal-slug>/log.md`（每轮追加）
总结文档：`~/.hskill/init-goal/<goal-slug>/summary.md`（loop 退出时生成）

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

根据用户描述，选最匹配的模版，用模版默认值填充所有**用户未提供**的字段：

| 匹配信号 | 模版 |
|---|---|
| 测试 / test / bug / 修复 / fix | Fix Until Green |
| 研究 / 搜索 / 信息收集 / search | Research Loop |
| 优化 / 改进 / 迭代 / refine / 润色 | Refine Until Satisfied |
| 监控 / 检查状态 / watch / monitor | Monitor & React |
| 探索 / 代码库 / 结构 / map / 未知领域 | Explore & Map |
| 无明显匹配 | 从零开始（所有字段留空） |

置信度高时直接套用，不问用户确认模版名称。

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

## 模版数据

### 模版 1: Fix Until Green

```
GOAL: 持续修复代码问题，直到所有测试通过。
EXECUTION:
1. 运行测试套件，记录当前通过数和失败列表
2. 分析失败用例，定位根因
3. 针对根因做最小化修复（每轮最多修改 3 个文件，不修改测试文件）
4. 重新运行测试，记录新的通过数
EVAL: 测试通过率（通过数 / 总数），本轮净增通过数。
CONSTRAINTS: 不修改测试文件本身；每轮最多修改 3 个源文件。
EXIT_EXPLICIT: 所有测试通过（通过率 100%）
EXIT_FALLBACK: 连续 2 轮通过率无变化则停止，汇报当前卡点和失败原因。
```

### 模版 2: Research Loop

```
GOAL: 持续搜索和整理信息，直到对目标主题有足够深度的理解。
EXECUTION:
1. 回顾当前已知信息和未解答的问题
2. 选择下一个最有价值的搜索方向（不重复已用关键词组合）
3. 执行搜索（每轮不超过 5 个查询）
4. 摘要新发现，追加到 log
EVAL: 本轮新增有效信息条数；预设问题中已有答案的比例。
CONSTRAINTS: 每轮搜索不超过 5 个查询；不重复已搜索过的关键词组合。
EXIT_EXPLICIT: 所有预设问题均已有答案，且连续 1 轮无新发现。
EXIT_FALLBACK: 连续 2 轮无新发现则停止，输出当前已知信息汇总。
```

### 模版 3: Refine Until Satisfied

```
GOAL: 反复优化指定输出，直到质量达到满意标准。
EXECUTION:
1. 评审当前版本，列出最重要的 3 个改进点
2. 执行改进（每轮只改 3 处，不推翻上一轮已确认的改动）
3. 对新版本自评分（1-10），说明理由
EVAL: 自评分（1-10），记录分数变化趋势。
CONSTRAINTS: 每轮只改进不超过 3 处；不推翻上一轮已确认的改动。
EXIT_EXPLICIT: 自评分 ≥ 8。
EXIT_FALLBACK: 连续 2 轮分数不再提升则停止，说明当前瓶颈。
```

### 模版 4: Monitor & React

```
GOAL: 持续监控指定状态，发现变化时执行响应动作。
EXECUTION:
1. 检查目标状态
2. 与上轮状态（见 log 最后条目）对比，判断是否有变化
3. 若有变化则执行预定响应动作（仅限预定范围）
4. 记录本轮状态快照
EVAL: 状态是否稳定；本轮是否触发响应动作。
CONSTRAINTS: 响应动作仅限预定范围，不做范围外操作。
EXIT_EXPLICIT: 目标状态连续 3 轮稳定。
EXIT_FALLBACK: 超过 20 轮未达到稳定则停止并上报当前状态。
```

### 模版 5: Explore & Map

```
GOAL: 系统性探索未知领域/代码库，建立完整的结构地图。
EXECUTION:
1. 从未探索节点中选择下一个最重要的节点
2. 深入分析该节点（结构、依赖、行为）
3. 记录发现与关联，更新探索进度
EVAL: 已探索节点数 / 总节点估算数；覆盖率百分比。
CONSTRAINTS: 每轮只深入一个节点；不跳跃式探索。
EXIT_EXPLICIT: 覆盖率达到目标阈值，或确认无新节点。
EXIT_FALLBACK: 连续 2 轮无新节点则汇总已知结构并停止。
```

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

## Step 2 — 生成文件

**生成 goal-slug：**
若 GOAL 是英文，转为 kebab-case（小写 + 连字符），截取前 40 字符。
若 GOAL 是中文，生成一个简短的英文描述（5-8 个单词，kebab-case）。

**创建目录并写入：**
```bash
mkdir -p ~/.hskill/init-goal/<goal-slug>
```

写入 `~/.hskill/init-goal/<goal-slug>/prompt.md`：

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

## 过程文档

路径：~/.hskill/init-goal/[goal-slug]/log.md

每轮开始前：读取 log.md 最后一个 Round 条目获取上下文（首轮若 log.md 不存在则跳过）。
每轮末尾：将本轮记录追加到 log.md，格式如下：

### Round N — YYYY-MM-DD HH:MM

**执行内容：** <本轮做了什么>

**评估结果：** <指标 / 分数 / 检查项结果>

**下一轮建议：** <继续方向，或已达退出条件>

---

Loop 退出时（明确条件触发、兜底逻辑触发或用户中断），在同目录生成 summary.md：

# GOal Summary — [goal-slug]

## 目标
[GOAL]

## 结果
<最终达成状态，一句话>

## 关键轮次
<哪几轮发生了重要转折，简要说明>

## 退出原因
<明确条件触发 / 兜底逻辑触发 / 用户中断>

## 执行统计
共 N 轮

## 建议（可选）
<若未完全达成，建议的下一步方向>
```

**向用户展示：**

---
✅ 已生成：`~/.hskill/init-goal/[goal-slug]/prompt.md`

启动 loop（选择你合适的 interval）：
```
/loop <interval> $(cat ~/.hskill/init-goal/[goal-slug]/prompt.md)
```

过程记录：`~/.hskill/init-goal/[goal-slug]/log.md`
结束总结：`~/.hskill/init-goal/[goal-slug]/summary.md`

---

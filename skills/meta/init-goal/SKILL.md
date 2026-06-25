---
name: init-goal
version: "1.0.0"
description: "Generate a structured /loop prompt file through guided dialogue. Elicits goal, per-round execution steps, evaluation metrics, constraints, and exit conditions. Supports 5 built-in templates (Fix Until Green, Research Loop, Refine Until Satisfied, Monitor & React, Explore & Map). Saves prompt.md to ~/.hskill/init-goal/<goal-slug>/. Triggers: user says /init-goal, 'initialize a loop goal', 'set up a GOal', or 'help me use /loop to accomplish X'."
user_invocable: true
---

# init-goal

对话式向导，帮助用户为 `/loop` 命令生成结构化的初始化 prompt 文件。

输出：`~/.hskill/init-goal/<goal-slug>/prompt.md`（静态，loop 不修改）
过程记录：`~/.hskill/init-goal/<goal-slug>/log.md`（每轮追加）
总结文档：`~/.hskill/init-goal/<goal-slug>/summary.md`（loop 退出时生成）

**规则：每个步骤只发一条消息，等待用户回复后再进入下一步。**

---

## Step 1 — 模版选择

向用户展示以下菜单，**一次性发送**，等待选择：

---
请选择一个模版，或输入 0 从零开始：

**1. Fix Until Green** — 持续修 bug 直到测试全通过
**2. Research Loop** — 反复搜索直到信息足够
**3. Refine Until Satisfied** — 迭代优化某个输出（文案/代码/方案）
**4. Monitor & React** — 持续监控状态并响应变化
**5. Explore & Map** — 系统性探索未知领域/代码库

**0. 从零开始**（不使用模版）

---

根据用户选择，将对应模版的默认值存为工作变量（见下方模版数据）。
选 0 则所有字段为空，需逐步填写。

然后进入 Step 2。

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

## Step 2 — 目标

若使用模版，展示默认 GOAL 并询问：

> 目标预设为：「[GOAL]」
> 直接回车接受，或输入你自己的目标描述（成功是什么样子？）：

若从零开始，直接问：

> 你想达成什么？成功是什么样子？

将用户回答记为 `GOAL`。

---

## Step 3 — 每轮执行内容

若使用模版，展示默认 EXECUTION 并询问：

> 每轮执行步骤预设为：
> [EXECUTION]
> 直接回车接受，或描述你想要的步骤：

若从零开始：

> 每次 loop 应该做什么动作？请描述每轮的具体步骤。

将用户回答记为 `EXECUTION`。

---

## Step 4 — 评估指标

若使用模版，展示默认 EVAL 并询问：

> 评估方式预设为：「[EVAL]」
> 直接回车接受，或输入你的评估方式（打分 / 检查清单 / 比对结果…）：

若从零开始：

> 每轮结束后如何判断进展？（例如：打分 1-10、检查特定文件是否存在、对比前后差异）

将用户回答记为 `EVAL`。

---

## Step 5 — 约束条件

若使用模版，展示默认 CONSTRAINTS 并询问：

> 约束预设为：「[CONSTRAINTS]」
> 直接回车接受，输入"无"跳过，或输入你的约束：

若从零开始：

> 有什么限制？（例如：最多运行 10 轮、不能修改某些文件、必须保留某个行为）
> 输入"无"跳过。

将用户回答记为 `CONSTRAINTS`（若为"无"则写入"无"）。

---

## Step 6 — 退出条件

**子问题 6a（明确条件）：**

若使用模版，展示默认 EXIT_EXPLICIT 并询问：

> 明确退出条件预设为：「[EXIT_EXPLICIT]」
> 直接回车接受，或输入达到什么状态可以停止：

若从零开始：

> 达到什么状态可以停止？（例如：测试全通过、找到 10 条有效结果、评分 ≥ 8）

将用户回答记为 `EXIT_EXPLICIT`。

**子问题 6b（兜底逻辑）：**

若使用模版，展示默认 EXIT_FALLBACK 并询问：

> 兜底逻辑预设为：「[EXIT_FALLBACK]」
> 直接回车接受，或描述当 Claude 无法判断是否达到目标时应该怎么做：

若从零开始：

> 如果 Claude 无法判断是否达到目标，应该怎么做？
> （例如：连续 2 轮无实质进展则停止并汇报原因）

将用户回答记为 `EXIT_FALLBACK`。

---

## Step 7 — 汇总确认

展示所有字段摘要：

---
**请确认以下内容：**

**目标：** [GOAL]

**每轮执行：**
[EXECUTION]

**评估指标：** [EVAL]

**约束：** [CONSTRAINTS]

**退出条件：**
- 明确：[EXIT_EXPLICIT]
- 兜底：[EXIT_FALLBACK]

---

询问：「确认无误吗？直接回车生成文件，或告诉我需要修改哪个字段。」

若用户指出修改，回到对应步骤重新问，然后再次展示摘要。直到用户确认。

---

## Step 8 — 生成文件

**生成 goal-slug：**
将 GOAL 转为 kebab-case：小写，空格和标点替换为连字符，去掉连续连字符，截取前 40 个字符。
例："持续修复代码直到测试通过" → 先取英文关键词或拼音简写，或直接用英文摘要。
若 GOAL 是英文："fix auth tests until all pass" → `fix-auth-tests-until-all-pass`（截取前 40 字符）。
若 GOAL 是中文，生成一个简短的英文 slug 来描述目标（5-8 个英文单词，kebab-case）。

**创建目录：**
```bash
mkdir -p ~/.hskill/init-goal/<goal-slug>
```

**写入 `~/.hskill/init-goal/<goal-slug>/prompt.md`：**

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

如需修改目标后重新运行：
```
# 编辑 prompt.md 后重启
/loop <interval> $(cat ~/.hskill/init-goal/[goal-slug]/prompt.md)
```

过程记录将自动写入：`~/.hskill/init-goal/[goal-slug]/log.md`
Loop 结束后总结：`~/.hskill/init-goal/[goal-slug]/summary.md`

---

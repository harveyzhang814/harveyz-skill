# 研究：三个 Skill 生态对"用户提问"哲学的实践（重跑版）

> 关联文档：[[principle]]
>
> 研究对象：
> - G stack → `/office-hours`（`~/.claude/skills/gstack/office-hours/SKILL.md`）
> - Superpowers → `brainstorming`（`superpowers/6.0.3/skills/brainstorming/SKILL.md`）
> - MSkill → `grilling`（`~/Repositories/mattpocock-skills/skills/productivity/grilling/SKILL.md`）
>
> 示例场景：帮用户规划一篇技术文章（三种思路的示例写法统一用此场景）

---

## 一、三个 Skill 的逐一解剖

### 1. G stack — `/office-hours`

**核心定位**：YC Office Hours 风格的产品诊断，分 Startup Mode（诊断施压）和 Builder Mode（创意协作）。

**核心机制——三层结构：**

**第零层：Brain Context 预加载**

开始提问之前，先读取项目缓存（product / goals / user-profile / recent-decisions / salience），跳过已有答案的问题。这是所有提问的前置条件，不是可选步骤。

**第一层：阶段路由（问哪些问题）**

| 产品阶段 | 问题子集 |
|---------|--------|
| 前产品期（无用户） | Q1, Q2, Q3 |
| 有用户 | Q2, Q4, Q5 |
| 有付费用户 | Q4, Q5, Q6 |
| 纯工程/基建项目 | Q2, Q4 |

不是每次都问六个。路由是机制的一部分。

**第二层：六个"逼迫性问题"（具体提问）**

| # | 核心问题 | "合格答案"标准 | "不合格"红线 |
|---|---------|-------------|------------|
| Q1 | 需求现实：最强的需求证据是什么？ | 具体行为、付钱、流失时会出问题 | 等待名单、"大家觉得不错" |
| Q2 | 现状替代：用户现在用什么凑合？ | 具体工作流、时间成本、工具组合 | "什么都没有，所以机会很大" |
| Q3 | 具体到人：最需要这个的具体是谁？ | 名字、职位、后果 | 行业标签、"SMB"、"营销团队" |
| Q4 | 最窄切入：这周能卖钱的最小版本是什么？ | 可在数天内交付、有人愿意付钱 | "平台建好才有人用" |
| Q5 | 观察惊喜：你有没有看过用户不受引导地用它？ | 具体意外发现 | 问卷调查、演示 call |
| Q6 | 未来适配：3年后这个产品更重要还是更不重要？ | 关于市场变化的具体论点 | "市场增长20%" |

**第三层：每问的推进机制**

每个问题不是问完就过，有明确的推进规则：

- **推进标准**：答案必须是"specific, evidence-based, and uncomfortable"。不满足就继续追问。
- **Q1 特别子探针**：Q1 收到第一个答案后，还要检查三件事——(1) 关键词是否有定义？(2) 有什么隐含假设？(3) 是真实案例还是假设情境？
- **推进姿态**："Push once, then push again. The first answer is usually the polished version."
- **校准式认可**：好答案不奖励，而是"名什么是好的，然后转向更难的问题"。不停留。

**关键设计决策（明确写出的）：**
- `"Ask these questions ONE AT A TIME via AskUserQuestion. STOP after each question."`
- `"Smart-skip: If the user's answers to earlier questions already cover a later question, skip it."`
- `"Push on each one until the answer is specific, evidence-based, and uncomfortable."`

**关键设计决策（隐含的）：**
- 问题集预先定义，不是动态生成
- 每个问题附有正面示例（FORCING exemplar）和负面示例（SOFTENED），强制执行语气标准
- 产品阶段评估发生在提问之前（Phase 1），是路由的前置条件

**原文关键句：**

> "Push once, then push again. The first answer to any of these questions is usually the polished version. The real answer comes after the second or third push."

→ 这是"逐题深挖"哲学的直接表达：不是问完就换，而是推到真实答案。

> "If the user expresses impatience: 'I hear you. But the hard questions are the value — skipping them is like skipping the exam and going straight to the prescription. Let me ask two more, then we'll move.'"

→ 逃生舱不是随时触发，而是有一次协商机会（"再两个"），第二次才真正降级。

**边界（什么情况下这种方式会失效）：**
- 用户已有充分证据和清晰计划时，提问反而是摩擦（但 escape hatch 处理了这种情况）
- 对于没有产品假设的开放性探索，预定义问题集会变成限制
- Builder Mode（纯创意类）用的是完全不同的生成性问题，同一套诊断框架不适用

---

### 2. Superpowers — `brainstorming`

**核心定位**：把想法转化为完整设计规格的协作对话流程，以 HARD-GATE 为核心约束，checklist 驱动执行。

**核心机制——不是单一提问阶段，而是多节点审批循环：**

```
探索上下文 → 问题澄清（一次一问）→ 提出 2-3 个方案 → 逐段展示设计（每段确认）
→ 写设计文档 → 自检 → 用户 Review 门控 → 调用 writing-plans
```

每个箭头都是一次用户接触点，不是问完再做。

**提问机制的关键设计决策（明确写出的）：**
- `"Only one question per message — if a topic needs more exploration, break it into multiple questions"`
- `"Prefer multiple choice questions when possible, but open-ended is fine too"`
- `"Focus on understanding: purpose, constraints, success criteria"`
- `"HARD-GATE: Do NOT invoke any implementation skill, write any code... until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity."`
- `"You MUST create a task for each of these items and complete them in order"` → checklist 驱动

**提问机制的关键设计决策（隐含的）：**
- **Scope 前置检查**：如果请求描述了多个独立子系统，在开始提问之前就要先做拆解决策，不进入正常提问流程
- **方案在问题之后**：问完澄清问题后，先提 2-3 个方案，用户选方案之后才进入设计展示阶段——中间插入了一个"选型"环节
- **视觉伴侣的 JIT 触发**：在某个问题"如果能看到会比文字更清楚"时，才在那个时刻单独提供浏览器伴侣选项。不是开场时提供。
- **用户 Review 门控独立于分段确认**：分段确认是展示设计时的实时验证；写完 spec 文档之后还有另一个"请查看文件并确认"门控

**原文关键句：**

> "HARD-GATE: Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY project regardless of perceived simplicity."

→ 这个门控不是对"提问"的，而是对"实施"的。提问阶段本身比较灵活，约束在实施入口处。

> "Ask after each section whether it looks right so far"

→ 这是"渐进确认"的核心操作：不是一次性给完，而是每段都要回应。

> "Before asking detailed questions, assess scope: if the request describes multiple independent subsystems, flag this immediately. Don't spend questions refining details of a project that needs to be decomposed first."

→ 这是原研究中遗漏的重要步骤：scope 筛查在提问之前，先判断值不值得问。

**边界（什么情况下这种方式会失效）：**
- 需求极度清晰时，"问 → 提方案 → 逐段确认"的循环是纯摩擦
- 用户已经有具体想法不需要探索时，提问和方案选择变成绕路
- 长期维护场景（修复已知 bug）不适合走完整 brainstorming 流程

---

### 3. MSkill — `grilling`

**完整内容（原文）：**

> Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.
>
> Ask the questions one at a time, waiting for feedback on each question before continuing. Asking multiple questions at once is bewildering.
>
> If a question can be answered by exploring the codebase, explore the codebase instead.

**核心机制——决策树遍历，AI 代理自答：**

每个设计分支 = 一棵决策子树。AI 主动遍历，但每个节点都先给出自己的推荐答案，用户只需确认或纠正。

**关键设计决策（明确写出的）：**
- 深度优先：`"Walk down each branch of the design tree"`
- 依赖关系排序：`"resolving dependencies between decisions one-by-one"`
- AI 自答：`"provide your recommended answer"`（每问都有）
- 一次一问：`"one at a time, waiting for feedback"` + 给出了原因
- 探索代替提问：`"If a question can be answered by exploring the codebase, explore the codebase instead"`

**关键设计决策（隐含的）：**
- 问题集不预定义，由 AI 从计划/设计结构中动态导出
- "提供推荐答案"意味着问题的形式是"我认为答案是 X，你看对吗？"而不是开放填空
- 目标是"shared understanding"，不是收集信息——这是对话的终止条件
- 没有逃生舱——但 AI 自答机制本身大幅减轻了用户负担，不需要逃生舱

**原文关键句：**

> "Asking multiple questions at once is bewildering."

→ 这是"一次一问"原则唯一一处给出了功能性解释：认知负荷，不是礼节问题。

> "For each question, provide your recommended answer."

→ 这是最重要的一句话。提问变成了"确认题"而不是"填空题"。

**边界（什么情况下这种方式会失效）：**
- 没有可遍历的具体计划/设计时，"走决策树"无从下手（适合压测现有方案，不适合从零探索）
- 对于开放性创意类任务，深度优先+自答可能过于结构化，会压缩探索空间
- 新建项目早期，代码库中找不到可以探索的答案时，"explore codebase"无法替代提问

---

## 二、三种核心思路提炼

### 思路 A：有标准的逼迫式提问（G stack office-hours）

**核心逻辑**：用预定义问题框架筛选信息质量——每个问题都有"合格答案"标准，不达标就继续施压，直到答案具体、有证据、有点不舒服。

**特征：**
- 问题集预定义，但通过阶段路由实现智能裁剪（不是每次都问全套）
- 每问都有明确的通关标准（push until 准则）和红线（什么不算数）
- AI 不自答，但始终持有立场并指出具体什么是不够的
- Brain 预加载 + 智能跳问：不问已知的答案
- 逃生舱：一次协商（"再两个"），第二次才彻底降级
- 每问之后给"校准式认可"（不夸奖，命名好在哪，然后转向更难的问题）

**适用场景**：目标验证类——"这个东西值不值得做"、"你的用户到底是谁"。需要用施压帮对方看清现实。

**广度/深度策略**：问题集广度（覆盖 6 个角度），但每问内部是深度（推到合格才放行）。同时有阶段路由裁剪广度。

**边界**：对已有清晰计划的用户是摩擦；纯创意探索时预定义框架变成限制；Builder Mode 需要切换成完全不同的提问范式。

**示例写法：**

```
开始写作之前，先加载项目上下文（有没有已知的读者定位、发布渠道、已有草稿）。
有答案的问题直接跳过。

然后逐题向用户提问，一次只问一个：

Q1. 这篇文章写给谁看？说出职位、经验水平、对这个话题已知什么。
    合格标准：一个具体的人，不是"开发者"这类标签。
    不合格："感兴趣的人"、"想学这个的人"。

Q2. 读完之后，读者应该能做到什么？
    合格标准：一个动作，不是感受（不接受"理解"、"了解"）。

Q3. 这篇文章里最反直觉的观点是什么？
    合格标准：一个具体主张，说不出来则这篇文章可能不需要存在。

每题收到回答后，判断是否达标。未达标：命名具体缺什么，继续追问。
达标：名一句"这个具体——"，然后进入下一题。

逃生舱：用户不耐烦时说"最后一题然后开始"；再次抗拒则直接进入写作。
```

---

### 思路 B：多节点渐进确认式（Superpowers brainstorming）

**核心逻辑**：不是"问完问题再执行"，而是整个流程拆成多个节点，每个节点都有用户确认作为通行证。问题是探索工具，不是筛选器。

**特征：**
- 每次只问一个问题（选择题优先，降低用户认知成本）
- Scope 前置检查：先判断请求是否过大，再开始问问题
- 问完问题后，不直接进入执行，而是先提出 2-3 个方案
- 设计分段展示，每段确认（"这部分方向对吗？"）
- Spec 写完之后还有独立的用户 Review 门控
- HARD-GATE 保护实施入口，提问阶段本身比较灵活
- 全程 checklist 驱动，明确任务顺序

**适用场景**：设计探索类——从模糊想法到完整 spec。用户知道想要什么方向但不知道怎么实现。

**广度/深度策略**：广度优先——先过目的/约束/成功标准，拿到全局轮廓，再在提方案时深入某个方向。

**边界**：需求极度清晰时整个循环是纯摩擦；没有创作空间的维护性任务不需要走完整 brainstorming 流程。

**示例写法：**

```
任务：先检查当前目录是否有草稿、相关资料或历史文章，理解背景。

Scope 检查：如果用户的文章描述了多个独立的话题（"同时写 A、B、C 三个主题"），
先帮助拆分，不进入单篇提问流程。

然后每次只问一个问题，优先选择题：
  1. 目的（选 A/B/C）
  2. 受众（选 A/B/C）
  3. 形式（选 A/B/C）

澄清完成后，提出 2-3 个结构方案，带取舍说明和你的推荐。

方案确认后，逐段展示大纲：
"**引言部分**：[内容描述]。这个方向对吗，还是需要调整再继续？"

每段确认后再继续下一段。全部确认后写 spec 文档。

写完后：
"Spec 已写入 <路径>，请看一下，有什么需要改的吗？"
等用户回复后才进入实施。
```

---

### 思路 C：AI 代理自答的决策树遍历（MSkill grilling）

**核心逻辑**：把计划视为决策树，AI 主动遍历所有分支——但不是"等用户回答"，而是"AI 先给推荐，用户确认或纠正"。提问的形式从填空变成确认。

**特征：**
- 问题动态从计划结构中导出，不预定义
- 按依赖关系排序：先解决其他决策依赖的那个
- 每问附上 AI 的推荐答案——用户只需说"对"或"不对，因为..."
- 代码库优先：可以自答的问题自己查，不问用户
- 一次一问 + 明确说了原因（"bewildering"）
- 终止条件是"达成共识"，不是"问完预设清单"

**适用场景**：方案压测类——"这个计划每个分支都想清楚了吗"。有具体方案需要全面验证。

**广度/深度策略**：深度优先——每个分支走到底（resolve dependencies），不先浏览所有分支。

**边界**：没有具体计划可遍历时无法启动；创意探索期深度优先会压缩探索空间；新项目代码库没有可查询的信息时，自答机制失效。

**示例写法：**

```
逐个遍历这篇文章的决策树，按依赖关系顺序处理。
每个问题附上你的推荐答案，用户只需确认或纠正。
一次只问一个——同时问多个问题会让人迷失。
如果某个问题可以通过阅读用户已有的材料来回答，先读，不问。

决策树（深度优先，先处理上游节点）：

- 受众                          ← 阻塞所有下游
  - 预设知识水平                ← 阻塞：深度、术语、示例难度
  - 读者的核心目标              ← 阻塞：什么算"有收获"
- 核心论点                      ← 阻塞：章节结构
  - 需要什么支撑证据            ← 阻塞：篇幅、是否需要调研
  - 需要回应哪些反对意见        ← 阻塞：语气、顺序

示例提问格式：
"文章的核心读者是谁？我的推荐：[具体描述]。对还是需要调整？"
```

---

## 三、三种思路的对比

| 维度 | 思路 A（有标准的逼迫式） | 思路 B（多节点渐进确认式） | 思路 C（AI 代理自答遍历式） |
|------|---------------------|----------------------|------------------------|
| 问题来源 | 预定义框架，阶段路由裁剪 | 即兴生成，scope 前置筛查 | 从计划结构动态导出 |
| 每问深度 | 深（有通关标准，推到合格） | 浅（一问一答即推进） | 中（AI 自答，用户确认/纠正） |
| 遍历策略 | 广度框架 + 每问内部深挖 | 广度优先（目的→受众→形式） | 深度优先（依赖顺序） |
| AI 自答 | 不自答，但有立场和反馈 | 提方案时给推荐 | 每问必须自答 |
| 逃生舱 | 有（一次协商，二次彻底降级） | 有（scope 检查 + 用户可快进） | 无（AI 自答已减轻负担） |
| 对用户的预设 | 用户需要被推，才能给出真实答案 | 用户有模糊想法，需要协作探索 | 用户有具体方案，需要帮助验证 |
| 核心哲学 | 问题是筛选器（过滤信息质量） | 问题是探索工具（扩展可能性） | 问题是决策确认器（缩小不确定性） |

---

## 四、对原始哲学问题的回答

### 关于"如何一步步质问用户"

三个来源全部收敛于同一个答案：**一次只问一个问题**。

但"一步步"的执行机制在三者间有实质差异：
- **思路 A**：问完有通关标准，不达标继续追问同一题，达标才换下一题
- **思路 B**：一问一答即推进，但问完问题后不是直接执行，而是进入提方案阶段
- **思路 C**：每问先给推荐答案，用户的工作从"回答"变成"确认或纠正"

MSkill 给出了"一次一问"的功能性原因：`"Asking multiple questions at once is bewildering"` — 认知负荷，不是礼节。

### 关于"广度优先还是深度优先"

研究未收敛，但有清晰的选择逻辑：

| 情况 | 推荐策略 | 来源 |
|------|---------|------|
| 目标是建立整体理解 | 广度优先 | Superpowers brainstorming |
| 各维度之间有依赖 | 广度优先（避免问了白问） | Superpowers brainstorming |
| 目标是压测具体计划 | 深度优先（走完每个分支） | MSkill grilling |
| 需要覆盖多个固定角度 | 广度框架内深挖每角度 | G stack office-hours |

**新发现：AI 自答是减少提问负担的核心机制**

三个来源在这点上有不同程度的体现：
- G stack：不自答，但每问都有推荐选项（via AskUserQuestion format）
- Superpowers：提方案时有推荐，但问题阶段本身是开放的
- MSkill：每个问题必须附上推荐答案

**推论**：好的前置确认不是"让用户填空"，而是"AI 先尽量自答，只把真正需要用户判断的那部分变成确认题"。这将用户的认知成本从"生成答案"降低到"评估答案"。

---

研究完成 → [[principle]]

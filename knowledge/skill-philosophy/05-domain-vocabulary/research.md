---
title: 领域术语统一研究报告
created: 2026-07-03
---

> 关联文档：[[principle]]
> 示例场景：全栈电商应用，前端叫"购物车"后端叫"Cart"，AI 有时叫"basket"——如何统一？

---

# 研究对象

| 生态 | 研究对象 | 路径 |
|------|----------|------|
| MSkill | `domain-modeling` | `skills/engineering/domain-modeling/SKILL.md` |
| gstack | `jargon-list.json` 系统 | `scripts/jargon-list.json` + `plan-tune/SKILL.md` |
| superpowers | `writing-plans` | `skills/writing-plans/SKILL.md` |

*附参考：MSkill `ubiquitous-language`（已废弃）和 `codebase-design` 作为对照。*

---

# 阶段四：深度解析

## 研究对象一：MSkill `domain-modeling`

### 核心机制

`domain-modeling` 是一个**主动维护型**词汇管理 skill。它不是在对话结束后提取术语，而是在设计进行时实时更新。核心文件是 `CONTEXT.md`（单上下文）或 `CONTEXT-MAP.md`（多上下文）。

### 关键设计决策

**1. 实时写入，不批量积累**
> "When a term is resolved, update CONTEXT.md right there. Don't batch these up — capture them as they happen."

这个决策解决了"遗漏"问题——术语在对话热点时最清晰，事后补录容易失真。

**2. 主动冲突检测**
> "When the user uses a term that conflicts with the existing language in CONTEXT.md, call it out immediately."

AI 不是被动记录者，而是主动的语言守卫。一旦用词偏离术语表，立即叫停。

**3. 用场景对话压测术语**
> "When domain relationships are being discussed, stress-test them with specific scenarios."

术语不是孤立定义，而是在具体场景对话中检验它的边界。这是 `ubiquitous-language` 没有的功能。

**4. CONTEXT.md 是纯词汇表**
> "CONTEXT.md should be totally devoid of implementation details. Do not treat CONTEXT.md as a spec, a scratch pad, or a repository for implementation decisions. It is a glossary and nothing else."

强边界：实现细节不混入。词汇表和架构决策分离（ADR 另存）。

**5. ADR 的高门槛**
只在"难以逆转 + 不解释让人困惑 + 有真实取舍"三条同时满足时才写 ADR。防止词汇表膨胀成设计文档。

### 对照：废弃的 `ubiquitous-language`

`ubiquitous-language` 是 `domain-modeling` 的前身：
- 触发方式：用户主动调用（"我们来梳理一下术语"）
- 输出：`UBIQUITOUS_LANGUAGE.md`
- 机制：从当前对话中提取，标记歧义，给出规范词

它被废弃的原因未说明，但从设计对比可以推断：被动提取 → 主动维护，是成熟化的方向。

### 对照：`codebase-design` 的嵌入式词汇

`codebase-design` 采用了完全不同的策略：词汇不存在外部文件里，而是**内嵌于 skill 定义本身**：

> "Use these terms exactly — don't substitute 'component,' 'service,' 'API,' or 'boundary.' Consistent language is the whole point."

词汇表是 skill 内容的一部分，每次调用 skill 时自动注入。不需要任何外部文件，不依赖用户维护。代价是：只覆盖这个 skill 的专有词汇，无法扩展到项目业务层。

---

## 研究对象二：gstack `jargon-list.json` 系统

### 核心机制

gstack 的词汇管理策略完全不同：一个**工具生态共享的外部 JSON 文件**，包含 80+ 条通用技术术语（idempotent、backpressure、N+1、circuit breaker 等），由所有 gstack skill 共享引用。

### 关键设计决策

**1. 懒加载：遇到才读**
> "On the first jargon term you encounter this session, Read that file once; treat the `terms` array as the canonical list."

不是每次 session 都读，而是遇到第一个术语时才读。降低了 context window 负担。

**2. Repo 所有权，PR 流程扩展**
> "The list is repo-owned and may grow between releases. Contributions: open a PR."

词汇表不属于任何一个项目，而是属于 gstack 这个工具生态。用户/贡献者通过 PR 添加术语，而不是在对话中动态添加。

**3. 目的是"解释"而非"统一"**
> "Curated list of technical terms that get a one-sentence gloss on first use per skill invocation."

gstack 的目标是让 AI 在首次使用术语时给出简明解释，而不是强制统一用词。这解决的是"理解"问题，不是"收敛"问题。

**4. 覆盖范围：通用技术术语，非业务领域**
词汇表里是：idempotent、deadlock、CORS、rate limit……完全没有项目特定的业务术语。这是一个工具级词汇，而非项目级词汇。

---

## 研究对象三：superpowers `writing-plans`

### 核心机制

`writing-plans` 不是词汇管理 skill，但它**在计划层面引入了词汇约束机制**：

### 关键设计决策

**1. Global Constraints 捕获命名规则**

每个实现计划都有 `## Global Constraints` 段，用于记录"项目范围内的命名规则、版本约束、平台要求"：

> "The spec's project-wide requirements — version floors, dependency limits, naming and copy rules, platform requirements — one line each, with exact values copied verbatim from the spec."

这是计划级的命名约束——不是独立的词汇表，而是嵌入计划文档的命名规范。

**2. 接口签名的精确约束**

每个任务有 `Interfaces` 段：

> "Produces: [what later tasks rely on — exact function names, parameter and return types. A task's implementer sees only their own task; this block is how they learn the names and types neighboring tasks use.]"

命名一致性通过"精确接口契约"而非词汇表来保证。

**3. 跨任务一致性检查**

> "Type consistency: Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called clearLayers() in Task 3 but clearFullLayers() in Task 7 is a bug."

把命名漂移视为 bug，在计划审查阶段捕获。

---

# 阶段五：核心思路提炼

## 思路一：主动守卫式（MSkill `domain-modeling`）

**核心逻辑**：用一个专职 skill 实时维护项目词汇表，AI 承担主动的语言冲突检测责任。

**特征**：
- 独立外部文件（`CONTEXT.md`），版本可控
- 实时写入，不批量积累
- AI 主动检测用词冲突并叫停
- 场景对话压测术语边界
- 词汇表与实现细节严格隔离

**适用场景**：有持续迭代的中大型项目，需要跨 session 积累和维护领域语言。

**广度/深度策略**：深度优先。术语一旦确定，立刻写入并在后续对话中严格遵守。

**边界**：需要 AI 有意识地承担"语言守卫"角色，若 AI 不主动检测冲突则失效。

**示例写法（购物车场景）**：
```
## 发现冲突 → 立即更新

用户："把 basket 里的商品数量显示在导航栏上"
AI："你的词汇表里这个概念叫 Cart，basket 是要避免的说法。我现在更新 CONTEXT.md，然后继续。"
→ 写入 CONTEXT.md：Cart: 用户添加商品等待结算的临时集合。Avoid: basket, shopping bag
```

---

## 思路二：懒加载共享式（gstack `jargon-list.json`）

**核心逻辑**：把通用技术词汇集中管理在一个工具级 JSON 文件里，所有 skill 共享引用，遇到时按需读取。

**特征**：
- 工具生态所有权（非项目所有权）
- 懒加载（首次遇到术语才读文件）
- PR 流程管理词汇扩展
- 目的是"解释"（gloss on first use），而非"统一用词"
- 覆盖通用技术术语，不覆盖业务领域词汇

**适用场景**：需要降低 AI 使用技术术语时的解释成本，适用于面向非技术用户的 skill 输出场景。

**广度/深度策略**：广度优先。80+ 个术语，每个只做一句话解释。

**边界**：无法处理项目特定的业务词汇。本质上解决"理解"问题，而非"收敛"问题。

**示例写法（购物车场景）**：
```
## 遇到术语时解释

AI："我们接下来要实现 Cart 的幂等操作（idempotent: 多次执行结果相同的操作）——"
→ 此处 "idempotent" 在 jargon-list 里，首次遇到时附加一句解释。
→ 但 "Cart" vs "basket" 的命名冲突，jargon-list 无法处理。
```

---

## 思路三：嵌入式词汇（MSkill `codebase-design`）

**核心逻辑**：把这个 skill 的专有词汇直接写入 skill 定义，每次调用时自动注入，无需外部文件。

**特征**：
- 词汇表是 skill 内容的一部分，不依赖外部文件
- 每次调用 skill 时词汇表自动生效
- 词汇带有强制性（"use these terms exactly"）
- 只覆盖这个 skill 的核心概念
- 无法动态扩展

**适用场景**：skill 本身需要一套稳定的专有语言，且这套语言不会随项目变化（如 DDD 概念、设计模式术语）。

**广度/深度策略**：深度优先，但范围固定。对 skill 内的核心术语做完整定义（含 Avoid 列表），但不覆盖项目业务层。

**边界**：无法处理项目特定词汇，词汇变更需要修改 skill 本身。

**示例写法（购物车场景）**：
```
## skill 内嵌词汇（设计层）

## 词汇表
使用以下术语，不要替换：
**Cart** — 用户待结算的商品集合。Avoid: basket, shopping bag
**CartItem** — Cart 中的单行记录，含商品 + 数量。Avoid: product, item, entry

（但前端叫"购物车"、后端叫"Cart"这种跨语言边界问题，嵌入式词汇无法处理。）
```

---

## 思路四：计划级命名约束（superpowers `writing-plans`）

**核心逻辑**：在实现计划文档里用 Global Constraints + 接口签名来约束命名，把命名一致性转化为计划执行时的 bug 检查。

**特征**：
- 命名规则嵌入计划文档，不独立存在
- 接口签名精确到函数名和参数类型
- 跨任务一致性在计划审查阶段捕获
- 约束只在这份计划的生命周期内有效
- 每次新计划需要重新声明约束

**适用场景**：单次开发任务内的命名一致性，适合防止 AI agent 在多步骤实现中自发引入不一致命名。

**广度/深度策略**：任务级别的精确约束，不追求历史积累。

**边界**：跨计划的术语积累需要其他机制；无法处理"AI 在对话中漂移"的问题。

**示例写法（购物车场景）**：
```markdown
## Global Constraints
- 购物车统一叫 Cart（前端组件名、后端类名、API 字段名保持一致）
- 不用 basket、shopping bag、bag

### Task 3: Cart API
**Interfaces:**
- Produces: `getCartItems(userId: string): CartItem[]`
- Produces: `addToCart(userId: string, productId: string, qty: number): Cart`
```

---

# 阶段六：对比与回答

## 对比表

| 维度 | 主动守卫式 | 懒加载共享式 | 嵌入式词汇 | 计划级约束 |
|------|-----------|-------------|-----------|-----------|
| 词汇归属 | 项目（`CONTEXT.md`） | 工具生态（`jargon-list.json`） | skill 本身 | 计划文档 |
| 覆盖范围 | 项目业务领域 | 通用技术术语 | skill 专有概念 | 单次计划 |
| 触发方式 | 实时（遇到就更新） | 懒加载（遇到术语才读） | 自动注入 | 计划起草时声明 |
| 跨 session 持久 | ✓（文件） | ✓（文件） | ✓（skill 定义） | ✗（计划生命周期） |
| 处理业务层命名漂移 | ✓ | ✗ | 部分（skill 范围内） | ✓（计划期内） |
| AI 主动冲突检测 | ✓ | ✗ | 隐式（靠 skill 指令） | ✓（审查阶段） |
| 维护成本 | 中（AI 维护，需要主动性） | 低（PR 流程，工具团队维护） | 极低（随 skill 版本） | 低（每计划声明一次） |

## 回答悬而未决的设计问题

### 问题一：触发时机

**结论**：实时触发优于专门触发。MSkill 从 `ubiquitous-language`（专门触发）到 `domain-modeling`（实时触发）的演化方向已经回答了这个问题。关键设计原则是"不批量积累"——术语在被讨论时最清晰，事后收集容易失真。

### 问题二：词汇归属

**结论**：项目级和工具级不互斥，各有用途。用户场景（前后端业务命名对齐）属于项目级需求，需要 `CONTEXT.md` 风格的项目词汇表。工具级（jargon-list）解决的是不同的问题。

### 问题三：冲突时谁说了算

**结论**：强制统一优于记录映射，但可以设过渡标记。MSkill 和 gstack 均选择"选一个规范词 + Avoid 列表"。实践中可在术语条目里加"代码暂用 Y，目标统一为 X"作为过渡标记，避免强制重命名带来的破坏性。

---

# 设计建议

对于用户的场景（跨前后端、跨 AI/人类的业务术语统一），建议采用**主动守卫式**为主、**计划级约束**为辅的组合策略：

1. **`CONTEXT.md` 作为项目通用语锚点**：参照 `domain-modeling` 的格式，在项目根目录维护一个领域词汇表。前后端对齐的目标词汇、Avoid 列表都存这里。

2. **AI 承担主动守卫责任**：在 CLAUDE.md 里指令 AI："每次对话中遇到与 CONTEXT.md 不一致的用词，立即指出并更新文件。"

3. **实现计划用 Global Constraints 强化**：每次写实现计划时，把 CONTEXT.md 里的关键术语摘入 Global Constraints，确保 AI agent 在实现阶段不漂移。

4. **跨 session 读取**：在 CLAUDE.md 里加一行"每次新 session 开始时读取 CONTEXT.md"，解决 AI 跨 session 遗忘的问题。

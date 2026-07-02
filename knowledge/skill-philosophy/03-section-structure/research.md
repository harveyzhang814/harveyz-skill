# 研究报告：Skill 章节划分的设计哲学

> 关联文档：[[principle]]
> 示例场景：一个"如何写 Skill"的 Skill（恰好三个研究对象本身就是这个场景）

---

## 研究对象

| 生态 | Skill | 类型 |
|------|-------|------|
| Superpowers 6.1.0 | `writing-skills` | 混合型（参考 + 执行） |
| MSkill (mattpocock) | `writing-great-skills` | 纯参考型 |
| G stack | `spec` | 纯执行型 |

---

## 阶段四：各研究对象解析

### 4.1 Superpowers `writing-skills`

**章节列表（精简）：**
```
Overview → What is a Skill? → TDD Mapping → When to Create → Skill Types →
Directory Structure → SKILL.md Structure（模板）→ SDO（可发现性）→
Flowchart Usage → Code Examples → File Organization →
The Iron Law → Testing All Skill Types → Common Rationalizations →
Match the Form to the Failure → Bulletproofing → RED-GREEN-REFACTOR →
Anti-Patterns → Checklist → Discovery Workflow → The Bottom Line
```

**核心机制：**
Skill 写作被映射为 TDD（测试驱动开发）。章节结构沿着"概念层 → 模板层 → 优化层 → 强制执行层"展开。

**关键设计决策：**
- **内容类型驱动分区**：定义、模板、反模式、检查清单各占独立章节，因为它们服务不同的"查阅动机"
- **SDO 单独成章**，没有并入"SKILL.md Structure"模板：因为可发现性是独立关注点，解决的问题与结构设计不同
- **Checklist 作为独立末章**，而不是整合进每个步骤后：因为检查清单的阅读模式是"完成时扫描"，而不是"执行时逐条"

**原文关键句：**
> "The description should ONLY describe triggering conditions. Do NOT summarize the skill's process or workflow in the description. Testing revealed that when a description summarizes the skill's workflow, an agent may follow the description instead of reading the full skill content."

解读：章节独立存在的必要性在这里被逆向证明——如果 description 里混入了流程摘要，AI 就不再读正文。说明不同访问入口对应不同内容，混合会导致错误的内容被"捷径命中"。

---

### 4.2 MSkill `writing-great-skills`

**章节列表：**
```
（无标题）核心命题 → Invocation → Writing the description →
Information hierarchy → When to split → Pruning → Leading words → Failure modes
```

**核心机制：**
整个 Skill 是纯参考型，无步骤。它建立了一套**词汇系统**（information hierarchy、leading word、context pointer、branch 等），通过词汇的精确定义来锚定行为，而非用步骤来约束流程。

**关键设计决策：**
- **没有"步骤"章节**：这个 Skill 描述原则，不描述流程。章节 = 概念的语义领域
- **"Information hierarchy" 是核心章节**：明确定义了 in-skill step / in-skill reference / external reference 三级梯度，这是整个 Skill 其余内容的理论基础
- **Failure modes 作为独立末章**：不是"怎么写"，而是"出什么问题时对照哪里"，访问模式是诊断性的，不是执行性的

**原文关键句：**
> "An in-skill step — an ordered action in SKILL.md, the primary tier: what the agent does, in order. Each step ends on a completion criterion... In-skill reference — a definition, rule, or fact in SKILL.md, consulted on demand."

解读：MSkill 明确区分了两种内容：步骤（有序执行，有完成标准）和参考（按需查阅）。这是整个研究中**最清晰的章节存在理由的理论表达**：步骤和参考的访问模式不同，混合会导致 AI 把参考当步骤执行，或把步骤当参考跳过。

> "Co-location decides what sits beside it once there: keep a concept's definition, rules, and caveats under one heading rather than scattered."

解读：章节的存在理由之一是**共置原则**——一个概念的定义、规则、注意事项应该在同一个标题下，不能散落在 Skill 各处。章节 = 概念的归属地。

---

### 4.3 G stack `spec`

**章节列表（结构性）：**
```
When to invoke → Preamble（run first）→
[共享区：Plan Mode / Skill Routing / AskUserQuestion Format / Artifacts Sync /
  Model Patch / Voice / Context Recovery / Writing Style / Behavioral Rules / Telemetry]
→ Flag Reference → Process（Phase 1-5）→ Issue Quality Standards
```

**核心机制：**
G stack Skill 有明显的**访问模式分层**：
- "Preamble（run first）"= 每次必须先执行的初始化代码
- 中间大量章节 = 按需查阅的规则库（AskUserQuestion 的格式只有真正要问问题时才看）
- "Process" = 核心执行流程，有严格的相位顺序
- "Issue Quality Standards" = 完成时对照的质量标准

**关键设计决策：**
- **AskUserQuestion Format 没有整合进 Process 的任一 Phase**：因为它在任何 Phase 都可能被用到，但不是每个 Phase 都需要它。如果整合进某个 Phase，其他 Phase 用到时就找不到；如果每个 Phase 都复制，则冗余
- **Process 章节标注"STRICT — do not skip or combine phases"**：说明 Process 的存在意义在于序列强制，而不仅是信息组织
- **共享区的章节（Voice、Context Recovery 等）**：在模板生成时从共享库注入，但在 Skill 中表现为独立章节——因为 AI 需要能独立查阅"如果遇到上下文丢失怎么办"，而不是在流程中间找

**原文关键句：**
> "## Preamble (run first)"  
> "## Process (STRICT — do not skip or combine phases)"

解读：G stack 用章节标题本身就承载了访问指令——"run first" 和 "STRICT" 是元数据，告诉 AI 这个章节的访问模式，而不只是给人类看的标签。

---

## 阶段五：核心思路提炼

### 思路 A：内容类型驱动分章（Superpowers `writing-skills`）

**核心逻辑：** 同类型的内容聚合在一起，不同类型的内容物理隔离。

**特征：**
- 定义独占章节，模板独占章节，反模式独占章节，检查清单独占章节
- 章节数量多，每章职责单一
- 读者可以根据"我现在想知道什么"直接跳到对应章节

**适用场景：** 内容种类繁多的复杂 Skill；需要被反复部分引用的参考手册型 Skill

**广度/深度策略：** 广度优先——先铺开所有类型，再在每类内部深入

**边界：** 内容不多的短 Skill 用这种方式会过度分割，造成结构感大于内容量

**示例写法（"如何写 Skill"场景）：**
```markdown
## 什么是 Skill
...定义...

## SKILL.md 结构模板
...模板...

## 发现优化（SDO）
...关键词覆盖、命名规范...

## 反模式
...叙事型、多语言稀释、通用标签...

## 检查清单
- [ ] frontmatter 完整
- [ ] description 以"Use when"开头
```

---

### 思路 B：访问模式驱动分章（G stack `spec`）

**核心逻辑：** 按 AI 访问这块内容的时机和方式分区，而非按内容类型。

**特征：**
- "run first"区：初始化，无条件执行
- "查阅区"：按需跳转，不是步骤
- "Process 区"：严格顺序执行，有相位编号
- "Quality Standards 区"：完成时对照
- 章节标题本身携带访问指令（"run first"、"STRICT"）

**适用场景：** 执行类 Skill，特别是流程复杂、中途需要查阅辅助规则的场景

**广度/深度策略：** 深度优先——每个访问模式只有一个区，区内尽量完整

**边界：** 纯参考类 Skill 没有"执行顺序"概念，访问模式分章无意义

**示例写法（"如何写 Skill"场景）：**
```markdown
## 开始前（run first）
检查已有 Skill 是否覆盖同一问题。

## 查阅：frontmatter 规范
name 只能用字母、数字、连字符...
description 上限 1024 字符...

## 流程（STRICT，不可跳过或合并步骤）
### 阶段 1：运行基线测试
### 阶段 2：写最小化 Skill
### 阶段 3：验证通过后部署

## 完成标准
- 基线场景在有 Skill 时通过
- 新理由都有对应的反驳条目
```

---

### 思路 C：词汇共置驱动分章（MSkill `writing-great-skills`）

**核心逻辑：** 章节 = 概念的归属地。一个概念的定义、规则、注意事项必须在同一标题下，不能散落。

**特征：**
- 没有步骤，只有概念
- 每个章节回答一个"这是什么"或"这里的权衡是什么"
- 章节间用粗体术语形成隐式交叉引用（术语在 GLOSSARY.md 有完整定义）
- 极度精简——没有任何冗余章节

**适用场景：** 纯参考类、词汇体系型 Skill；内容是原则而非步骤

**广度/深度策略：** 深度优先——概念少但每个概念挖深，外延用 GLOSSARY 承接

**边界：** 没有执行性内容时适用；一旦需要告诉 AI"做什么"，纯词汇模式就不够了

**示例写法（"如何写 Skill"场景）：**
```markdown
Skill 的核心美德是**可预测性**——AI 每次运行走同样的过程，而非产生同样的输出。

## 信息层级
**步骤**：有序动作，有完成标准。**参考**：按需查阅，无序列。
步骤和参考混合会导致**提前完成**（把参考当步骤读完就收手）。

## 何时分章
按**分支**：只有部分执行路径需要的内容，推出正文外。
按**序列**：后续步骤会诱导提前完成时，隐藏后续。

## 失效模式
- **提前完成**：完成标准模糊时出现，先收紧标准，再考虑分章
- **沉积**：每次添加都安全，删除都危险，最终 Skill 慢慢腐烂
```

---

## 阶段六：对比与回答

### 对比表

| 维度 | Superpowers（内容类型） | G stack（访问模式） | MSkill（词汇共置） |
|------|------------------------|--------------------|--------------------|
| **章节存在理由** | 内容种类不同 | 访问时机不同 | 概念归属不同 |
| **章节数量** | 多（15+） | 中（8-10 个功能区） | 少（6-8 个） |
| **有无步骤** | 有（工作流 + 检查清单） | 有（严格相位） | 无 |
| **强制机制** | Iron Law + 禁止清单 | STRICT 标记 + 标题指令 | 失效模式（诊断式） |
| **章节间关联** | 弱（各章独立） | 强（Process 引用查阅区） | 中（术语交叉引用） |
| **对极短 Skill 的适用性** | 低（结构感大于内容） | 中（Process 可只有 1 阶段） | 高（词汇即结构） |

---

### 回答 `principle.md` 中的悬而未决问题

#### 问题 1：章节独立存在，还是整合进流程？

**研究结论：取决于内容的访问模式。**

- 如果某内容在流程的**任意阶段**都可能被查阅（如 G stack 的 AskUserQuestion Format），整合进某个阶段反而造成"找不到"或"重复"
- 如果某内容有**完全不同的阅读动机**（执行 vs. 诊断 vs. 完成后对照），整合进统一流程会导致 AI 把所有内容当成同一种步骤处理
- MSkill 提供了最清晰的理论：步骤（有序，有完成标准）和参考（按需）的**访问模式不同**，混合导致提前完成或提前跳过

**结论：** 独立章节的正当性来自于"不同的访问时机"，而不是"内容足够多"。访问模式相同的内容整合；访问模式不同的内容分章。

---

#### 问题 2：执行类和诊断类应否有本质不同的结构？

**研究结论：是的，本质不同，但共享一个底层原则。**

- 执行类（G stack spec）：以 Process 为骨架，其余章节都是执行过程中的"查阅资源"
- 诊断类/参考类（MSkill writing-great-skills）：以概念体系为骨架，没有步骤，只有词汇和失效模式
- 混合类（Superpowers writing-skills）：两套都有，但体积膨胀，维护成本高

底层共享原则：**章节 = 一种访问模式下的内容聚合**。无论执行还是诊断，都遵循"同类访问模式的内容聚合在一起"。

---

#### 问题 3：何时把内容推出正文，变成独立章节或外部文件？

**研究结论：MSkill 的"分支驱动"原则最清晰。**

> 内联 = 每条执行路径都需要的内容；推出 = 只有部分路径需要的内容

MSkill 的 "When to split" 给出了两种切割方式：
- **按调用**：有独立触发词的内容，拆成独立 Skill
- **按序列**：看到后续步骤会诱导跳跃的内容，推出视野

G stack 的实践印证了这一点：AskUserQuestion Format 被推成独立章节，因为只有"要问问题时"才需要它。

---

## 最终结论：通用结构规范的起点

从三个生态的共性中，可以提炼出一套 Skill 章节的**最小必要结构**：

```
1. 触发区（何时调用）  ← 所有 Skill 都有，有时在 frontmatter
2. 基础区（核心概念 / 初始化）  ← 建立语义前提或运行环境
3. 主体区（步骤 OR 概念体系）  ← 执行类=流程，参考类=词汇
4. 查阅区（按需参考的规则）  ← 只有部分路径需要时才独立成章
5. 完成区（质量标准 / 反模式 / 失效模式）  ← 完成时对照，诊断时查阅
```

**不是所有区都必须存在**——执行类可以没有词汇区；参考类可以没有步骤区；极短 Skill 可以把所有区内联为隐含分层。

**章节不应该存在的理由：**
- 内容和另一章节的访问模式相同 → 合并
- 内容在所有路径都需要，且篇幅小 → 内联进相邻内容
- 内容只是某章节的子细节 → 降级为该章节内的列表项，不单独成章

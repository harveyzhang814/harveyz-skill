# Principle 07：description 的职责是触发命中，不是传递操作参数

## 核心命题

Skill 的 description 字段只应服务于一个目的：让 AI 在合适的场景下选中这个 Skill。操作约束、参数说明、执行细节不属于这里。当 description 同时承担触发和说明两种职责，两者都会变差——触发语言被稀释，操作说明又没人读。

## 悬而未决的设计问题

### 问题 1：边界在哪里？

**两个对立选项：**
- 选项 A：description 只写触发语言，操作内容零容忍，全部移入 body
- 选项 B：允许少量操作提示出现在 description，只要它同时也强化了触发信号

**张力：** A 原则干净，但可能导致某些关键约束被跳过；B 灵活，但"少量"的边界难以量化，容易滑坡。

**研究结论**：三方高度一致，倾向选项 A。可操作判断标准：这句话帮 Agent 决定"要不要用这个 Skill"（属于 description），还是帮 Agent 决定"怎么用这个 Skill"（属于 body）？Superpowers 有实测证据：哪怕一句流程摘要，Agent 都会把 description 当捷径、跳过 body。→ 见 `research.md` § 五·问题 1

---

### 问题 2：额外信息的必要性

**两个对立选项：**
- 选项 A：description 只需触发语言，任何额外信息都是噪音
- 选项 B：某些元信息（如适用范围、前置条件）有时必须出现在 description，否则触发后会产生严重误用

**张力：** A 保持 description 精简，B 承认触发和约束有时无法完全分离。

**研究结论**：三种额外信息有研究支撑，都合法：①触发信号的具体化（症状、情境、前提条件）；②Skill 互调时的可达性声明（"when another skill needs…"）（MSkill）；③负向触发（"when NOT to use" / 技术范围约束）。操作能力描述、步骤摘要不属于合法额外信息。→ 见 `research.md` § 五·问题 2

---

### 问题 3：操作内容的归宿

**两个对立选项：**
- 选项 A：操作约束统一移入 body，由 Skill 执行时读取
- 选项 B：操作约束分散在多处——部分在 body，部分在调用时通过 args 传入，部分在外部文档

**张力：** A 结构清晰，B 更灵活但维护成本高。

**研究结论**：三方共识：操作约束进 body。MSkill 提供最清晰的层级框架：优先写成 body 里的有序步骤（in-skill step），其次是按需查阅的规则（in-skill reference），只有"部分 branch 才需要"的内容才推到外部文件（progressive disclosure）。→ 见 `research.md` § 五·问题 3

---

## 尚未解答的更深问题

- description 的触发语言应该写成什么风格——自然语言、关键词列表、触发场景枚举？
- 当一个 Skill 有多个触发场景，description 如何兼顾而不变得冗长？
- 如果 description 写得太"操作化"，对触发精度的实际影响有多大？

---

---

## 研究完成

研究报告：[[research]]（`research.md`）

**新发现的深层问题**（在原始命题之外）：
- 当 description 和 triggers 字段同时存在时，二者冲突如何解决？
- description 多长算"太长"，context load 的量化阈值在哪里？
- MSkill 的 leading word 策略对工具型 Skill（无明确概念词）是否适用？

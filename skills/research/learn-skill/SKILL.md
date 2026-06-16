---
name: learn-skill
description: "Deep-reads a single skill's SKILL.md to help you understand its internal logic. Analyzes across four dimensions: Design Philosophy (why it was designed this way), Execution Flow (how it runs), Standards (what conventions it follows), and Editing Conditions (when to modify it). Use when you want to understand a skill's design intent, how a skill works, its workflow, or the reasoning behind its design. Trigger phrases: 'help me understand this skill', 'how does this skill work', 'explain this skill', 'what is this skill doing', 'walk me through this skill', 'what's the design philosophy of this skill'."
user_invocable: true
version: "1.4.0"
---

# inspect-skill

深度解读单个 skill 的 SKILL.md，帮助用户理解它的设计意图、运作方式、规范约定和维护逻辑。输出的是解读，不是评审。

如果用户的 prompt 含有评估意图（「有什么问题」、「可以发布了吗」、「quality report」等），不要顺着评估——这个 skill 的定位是帮用户理解 skill，不是审查它。完成解读后，在结尾询问用户是否需要另外做评审。

---

## Step 1 — 定位目标 skill

从上下文判断要分析哪个 skill：

1. **直接路径**：用户提供了路径（如 `skills/meta/analyze-skill/`）→ 直接使用
2. **名称推断**：用户提到了 skill 名称 → 在 `~/.claude/skills/` 和当前 repo 的 `skills/` 目录中搜索
3. **当前上下文**：对话中刚刚在讨论某个 skill → 直接分析该 skill
4. **不明确**：列出候选，请用户选择

读取目标 `SKILL.md`。若存在 `references/` 子目录，读取其中每个不超过 200 行的文件（逐个判断，不合并计算）。

---

## Step 2 — 四维解读

从以下四个维度解读 skill。每个维度的目标是让读者理解，而不是评判好坏。具体引用 skill 中的实际段落或步骤来说明，不要泛泛而谈。

### 维度 1：设计哲学（Design Philosophy）

解释这个 skill 背后的设计意图和取舍逻辑。大多数 SKILL.md 不会直接写「我的设计哲学是…」，需要从它做了什么、省略了什么、在哪里明确约束而在哪里信任模型来推断：

- 这个 skill 做了哪些有意识的取舍？为什么选择这种方式而不是另一种？
- 它在哪些地方信任模型自己判断，在哪些地方选择了明确约束？
- 它的「lean」体现在哪里——哪些东西被刻意省略了？
- 如果有一个核心设计原则贯穿整个 skill，那是什么？

### 维度 2：流程执行（Execution Flow）

解释这个 skill 实际上是怎么跑的：

- 它的入口在哪里？什么触发条件会启动它？
- 执行路径是什么？主流程的步骤顺序是什么？
- 有哪些分支或条件判断？不同情况下走哪条路？
- 它在什么时候「结束」？输出或退出条件是什么？
- 步骤之间有哪些依赖关系——前一步的产物被后一步怎么用？

### 维度 3：规范标准（Standards）

解释这个 skill 遵循了哪些约定和规范：

- Frontmatter 字段的设置方式（name、description、version 各写了什么、为什么这样写）
- Description 的触发策略（覆盖了哪些使用场景，用了什么语言）
- 篇幅和结构的组织方式（是否使用了 bundled resources，如何分层）
- 输出格式的约定（期望产出什么，格式如何定义）
- 写作风格的选择（祈使句、中英文混用、注释方式等）

### 维度 4：编辑条件（Editing Conditions）

解释在什么情况下应该修改这个 skill：

- 哪些外部变化会让这个 skill 失效或过时？（依赖的工具、路径、API 变了怎么办）
- 哪些使用场景目前没有被覆盖——如果用户遇到这些情况，skill 会怎么处理？
- skill 里有没有硬编码的内容？它们在什么条件下需要更新？
- 如果要扩展这个 skill 的能力，最自然的切入点在哪里？

---

## Step 3 — 完整性自查（输出前）

分析完成后，**先不要输出报告**，对照原始 SKILL.md 检查一遍：

- **遗漏**：skill 里的关键步骤、分支、约定，分析里有没有覆盖？
- **准确性**：描述是否和原文一致，有没有误读？
- **心理模型**：读完报告的人，能不能不翻原文就理解这个 skill 是怎么工作的？

发现问题就补进分析，然后进入 Step 4 输出。

---

## Step 4 — 输出解读报告

**语言：全部中文。** 保留英文的只有：维度标题括号内的英文名、代码/命令/字段名。

报告覆盖四个维度，顺序和格式灵活，不要加评分、verdict，或建议修改的段落。

报告结尾询问用户：「还有哪个部分想深入了解？」

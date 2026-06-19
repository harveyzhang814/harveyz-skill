---
name: learn-skill
description: "Deep-reads a single skill's SKILL.md to help you understand its internal logic. Analyzes across four dimensions: Execution Flow (how it runs and all branches), Standards (design thinking and hard specs), Boundary Conditions (what it's designed for and not), and Design Philosophy (synthesized from the first three). Use when you want to understand a skill's design intent, execution flow, condition branches, applicable boundaries, or the reasoning behind its design. Trigger phrases: 'help me understand this skill', 'how does this skill work', 'explain this skill', 'what is this skill doing', 'walk me through this skill', 'what's the design philosophy of this skill', 'what are the branches in this skill', 'what are the limitations of this skill'."
user_invocable: true
version: "2.0.0"
---

# learn-skill

深度解读单个 skill 的 SKILL.md，帮助用户理解它的运作方式、规范约定、能力边界，以及基于这三者推断出的设计意图。输出的是解读，不是评审。

如果用户的 prompt 含有评估意图（「有什么问题」、「可以发布了吗」、「quality report」等），不要顺着评估——这个 skill 的定位是帮用户理解 skill，不是审查它。完成解读后，在结尾询问用户是否需要另外做评审。

---

## Step 0 — 读取或初始化配置

读取 `$HOME/.hskill/config.json`，检查是否存在 `skillDir` 字段。

**如果不存在**：
1. 询问用户目标目录路径（建议默认值：`$HOME/Documents/skill-library`）
2. 将用户输入的路径解析为绝对路径（展开 `~` 和 `$HOME`）
3. 若目录不存在则创建
4. 将解析后的绝对路径写入 `$HOME/.hskill/config.json`（文件不存在则新建）

**如果已存在**：直接使用，不打扰用户。

---

## Step 1 — 定位目标 skill

从上下文判断要分析哪个 skill：

1. **直接路径**：用户提供了路径（如 `skills/meta/analyze-skill/`）→ 直接使用
2. **名称推断**：用户提到了 skill 名称 → 在当前 repo 及常见 skill 安装目录中搜索
3. **当前上下文**：对话中刚刚在讨论某个 skill → 直接分析该 skill
4. **不明确**：列出候选，请用户选择

读取目标 `SKILL.md`。若存在 `references/` 子目录，读取其中每个不超过 200 行的文件（逐个判断，不合并计算）。

---

## Step 2 — 四维解读

从以下四个维度解读 skill，**按顺序执行**：先分析现象（流程、规范、边界），最后综合推断本质（设计哲学）。每个维度的目标是让读者理解，不是评判好坏。具体引用 skill 中的实际段落或步骤来说明，不要泛泛而谈。

---

### 维度 1：流程执行（Execution Flow）

解释这个 skill 实际上是怎么跑的。**分析重心是每个节点的具体行为**；Mermaid 图仅作为概览索引辅助定位，在节点分析完成后输出，不是分析本身。

**逐节点详细分析**：

- **入口与触发**：什么操作或上下文启动这个 skill？触发条件是什么？有哪些触发变体？
- **主流程步骤**：每一步具体做了什么？接收什么输入、执行什么操作、产出什么结果？产出如何被下一步使用？
- **条件分支**：逐一列出所有判断点，用「如果…则…否则…」格式说明每条路径的执行差异和后续行为
- **步骤依赖**：哪些步骤依赖上一步的产物？依赖什么、怎么用？
- **出口与结束**：skill 在什么情况下结束？有几种退出路径？

节点分析完成后，输出 Mermaid flowchart 作为概览——覆盖主流程和所有条件分支，节点标签与上方分析保持一致，条件判断用菱形表示，分支边标注具体条件文字。

---

### 维度 2：规范标准（Standards）

解释这个 skill 遵循了哪些约定，分为两类——**思维标准**是解读重心，**硬性指标**是快速参考。

#### 思维标准（Thinking Standards）

解读设计决策背后的思考方式：

- 这个 skill 以什么粒度控制模型行为？哪些步骤选择了明确约束，哪些留给模型自主判断？
- 它的分步结构背后是什么组织逻辑？为什么是这个顺序，而不是另一种？
- 它在哪些地方做了「最小必要」的选择——刻意省略了什么，为什么省略？
- 它对执行者（模型）的信任边界在哪里？

#### 硬性指标（Hard Specifications）

可直接核查的规范条目：

- Frontmatter 字段（`name`、`description`、`version` 各写了什么、格式是否符合约定）
- 文件命名、保存路径、目录结构约定
- 输出格式（期望产出什么，格式如何定义）
- 语言约定（中英文混用规则、术语选择）
- 写作风格（祈使句、注释方式等）

---

### 维度 3：边界条件（Boundary Conditions）

界定这个 skill 的能力边界和适用范围。

- **设计假设**：这个 skill 假设使用者处于什么场景？有哪些前置条件（路径存在、有 git 环境、用户已知某些信息等）？
- **有意不覆盖的场景**：哪些使用场景被刻意排除在外？为什么这些场景不在设计范围内？
- **越界后的处理**：当前置条件不满足、或使用场景超出边界时，skill 会如何响应——降级处理、静默跳过、还是报错退出？
- **隐性限制**：有哪些未被明说但实际上限制了使用范围的约束？（如依赖特定目录结构、只处理单个 skill 等）

---

### 维度 4：设计哲学（Design Philosophy）

**本维度是综合分析，不是独立推断。** 基于维度 1-3 的分析结论，结合对原始 SKILL.md 的直接阅读，推断这个 skill 背后的设计意图和取舍逻辑。

推导路径：
1. 从维度 1（流程）中发现 skill 如何分配执行权重
2. 从维度 2（规范）中发现它对「什么重要」的判断
3. 从维度 3（边界）中发现它有意识的取舍
4. 结合原始 skill 的措辞、结构、省略点，直接推断设计意图

重点解答：
- 这个 skill 做了哪些有意识的取舍？为什么选择这种方式而不是另一种？
- 它在哪些地方信任模型自己判断，在哪些地方选择了明确约束？这个边界是怎么定的？
- 如果有一个核心设计原则贯穿整个 skill，那是什么？

---

## Step 3 — 完整性自查（输出前）

分析完成后，**先不要输出报告**，对照原始 SKILL.md 检查：

- **遗漏**：skill 里的关键步骤、分支、约定，分析里有没有覆盖？
- **准确性**：描述是否和原文一致，有没有误读？
- **心理模型**：读完报告的人，能不能不翻原文就理解这个 skill 是怎么工作的？
- **逻辑链**：维度 4（设计哲学）中的每一个结论，是否都能在维度 1-3 的分析或原始 SKILL.md 中找到支撑证据？
  - 找到证据：在输出时标注来源（来自维度 X 或原文第 N 步）
  - 未找到证据：**先回到原始 SKILL.md 主动寻找支撑**；找到则补入对应维度；仍无法找到则修改或删除该结论

发现问题就补进分析，然后进入 Step 4 输出。

---

## Step 4 — 输出解读报告

**语言：全部中文。** 保留英文的只有：维度标题括号内的英文名、代码/命令/字段名。

报告按维度 1→2→3→4 顺序输出，Mermaid 图放在维度 1 的开头。不要加评分、verdict，或建议修改的段落。

报告结尾询问用户：「还有哪个部分想深入了解？」

---

## Step 5 — 保存报告

将报告保存到 `{skillDir}/{repo-name}/{skill-name}.md`，同名文件存在时直接覆盖。

- `skillDir`：config.json 中的绝对路径
- `repo-name`：执行 `basename $(git rev-parse --show-toplevel)` 取得；若不在 git 仓库中则使用 `unknown`
- 目录不存在时自动创建

文件结构：

```markdown
---
skill: {skill-name}
repo: {repo-name}
path: {skill 的完整路径}
version: {skill 的 version 字段值，若无则省略}
analyzed_at: {YYYY-MM-DD}
---

{四维报告正文}
```

保存完成后，在对话中告知用户文件路径。

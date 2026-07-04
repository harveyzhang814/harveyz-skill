> 关联文档：[[principle]]

> 示例场景统一使用：**一个在提交代码前强制检查 lint 的 Skill**（discipline-enforcing 类型，有明确触发条件和明确工作流）

---

# 研究报告：description 的职责是触发命中，不是传递操作参数

## 一、研究对象

| 生态 | 研究对象 | 路径 |
|------|---------|------|
| MSkill | `writing-great-skills` | `~/Repositories/mattpocock-skills/skills/productivity/writing-great-skills/SKILL.md` |
| Superpowers | `writing-skills` | `~/.claude/plugins/cache/claude-plugins-official/superpowers/6.1.1/skills/writing-skills/SKILL.md` |
| gstack | 所有 Skill 的 description 样本 + CONTRIBUTING.md | `~/.claude/skills/gstack/*/SKILL.md` |

---

## 二、深度解析

### 2.1 MSkill — writing-great-skills

**核心机制**

MSkill 明确区分两种调用模式（model-invoked vs user-invoked），两种模式下 description 的写作逻辑完全不同：

- **model-invoked**：description 承担双重职责——说清楚 Skill 是什么 + 列出触发它的 **branches**（分支场景）。每个 token 都是 context load，所以必须极度精简。
- **user-invoked**：`disable-model-invocation: true`，description 变成给人看的一行摘要，触发列表全删。

**关键设计决策**

- "Front-load the skill's leading word" — description 的第一个词就是 Skill 的核心概念（leading word），既做路由又做锚点
- "One trigger per branch. Synonyms that rename a single branch are duplication" — 不同触发场景保留，同一场景的近义词删掉
- "Cut identity that's already in the body" — body 里会重述的内容不要出现在 description
- 唯一允许额外内容的例外："any 'when another skill needs…' reach clause"（Skill 互相调用时的可达性声明）

**原文关键句**

> "A model-invoked description does two jobs — state what the skill is, and list the branches that should trigger it. Every word increases context load, so a description earns even harder pruning than the body."

解读：description 承认有双重职责，但优化方向是压缩而不是分离——通过 leading word 把"是什么"和"何时触发"合并成一个高密度的信号。

---

### 2.2 Superpowers — writing-skills

**核心机制**

Superpowers 基于**实测**得出最强结论：description 只能是触发条件，不能包含任何工作流摘要。这是这三个生态中立场最明确、论据最充分的一个。

**关键设计决策**

- description 必须以 "Use when..." 开头，强制写触发条件
- 明确禁止：总结 Skill 的流程和工作方式
- 明确允许：具体的症状、场景、上下文（但只有当它们服务于触发时）
- 字数建议：500 字符以内

**最核心的实测证据**

> "Testing revealed that when a description summarizes the skill's workflow, an agent may follow the description instead of reading the full skill content. A description saying 'code review between tasks' caused an agent to do ONE review, even though the skill's flowchart clearly showed TWO reviews."

解读：description 里的工作流摘要会成为**捷径陷阱**——Agent 读完 description 以为已经知道怎么做了，就不读 body。这不是理论推测，是实测发现。改成纯触发条件后，Agent 正确读取了 flowchart 并执行了完整流程。

**额外信息的规则**

> "Include specific symptoms, situations, and contexts" — 允许的额外内容是**触发信号的具体化**，不是操作说明。症状（flaky tests）、情境（when using React Router）、前提条件（before writing implementation code）——这些都服务于"让 Agent 认出自己应该用这个 Skill"，而不是"告诉 Agent 怎么用这个 Skill"。

---

### 2.3 gstack — `triggers` 字段 + description 样本分析

**核心机制**

gstack 采用**结构性分离**策略：在 frontmatter 中设置独立的 `triggers` 字段，专门存放路由关键词，description 字段因此被**解放**，变成产品能力描述而非触发条件列表。

```yaml
description: Fast headless browser for QA testing and site dogfooding. (gstack)
triggers:
  - browse
  - open a site
  - QA testing
```

**关键设计决策**

- `triggers` 字段承担路由工作（关键词列表）
- description 变成"产品介绍风格"——说清楚这是什么工具，能做什么
- 允许 description 包含功能范围描述，甚至少量流程说明（autoplan 的 description 就包含了工作流概要）
- 统一在 description 末尾加 `(gstack)` 品牌标记

**实际样本**

```yaml
# 简洁能力型
description: Post-deploy canary monitoring. (gstack)

# 功能范围型
description: Chief Security Officer mode. (gstack)

# 含流程摘要型（gstack 允许这样写）
description: Auto-review pipeline — reads the full CEO, design, eng, and DX review skills
  from disk and runs them sequentially with auto-decisions using 6 decision principles. (gstack)
```

**原文关键句**（CONTRIBUTING.md）

> "Frontmatter | Full (name, description, hooks, version) vs minimal (name + description)"

解读：gstack 的设计哲学是 description + triggers 共同承担触发职责，description 承担"理解"层，triggers 承担"匹配"层，两者职责分离。

---

## 三、核心思路提炼

### 思路 A：条件触发式（Superpowers writing-skills）

**核心逻辑**：description 只写触发条件，用触发条件本身说清楚 Skill 是什么。

**特征列表**：
- 必须以 "Use when..." 开头
- 只包含症状、场景、情境
- 不包含任何工作流、流程步骤
- 不包含 Skill 的能力总结
- 500 字符以内

**适用场景**：
- Skill 有明显的触发症状（"tests are flaky", "race conditions"）
- Skill 被 Agent 自动路由，需要精确命中
- Skill body 有复杂工作流，防止 Agent 跳过

**广度/深度策略**：宽泛触发，深度执行于 body——description 只管"进门"，进门后完全由 body 驱动。

**边界**：
- 当 Skill 的触发场景难以用症状描述时（纯工具型 Skill）写起来别扭
- 当多个 Skill 症状相近时，单靠条件描述难以区分

**示例写法（lint 前置检查 Skill）**：
```yaml
description: Use when committing code, before creating a pull request,
  or when running CI locally to ensure lint passes before merge
```

---

### 思路 B：双职融合式（MSkill writing-great-skills）

**核心逻辑**：description 同时做"是什么"和"何时触发"，通过 leading word（高密度概念词）把两者压缩进最少的 token。

**特征列表**：
- 开头放 leading word（Skill 的核心概念）
- 每个真正不同的触发场景保留一条
- 近义词和同义场景合并，不重复
- model-invoked 和 user-invoked 写法完全不同
- 允许"当另一个 Skill 需要此 Skill 时"的可达性声明

**适用场景**：
- Skill 有一个高度概括的核心概念可以作为 leading word
- Skill 会被其他 Skill 调用（需要声明可达性）
- 需要同时服务 Agent 路由和人类理解

**广度/深度策略**：精准触发——通过 leading word 对接 Agent 的预训练先验，而不是列举所有可能的场景。

**边界**：
- 需要找到合适的 leading word，不是所有 Skill 都有这样的概念
- "双职"的本质是经济压缩，不是随意增加内容

**示例写法（lint 前置检查 Skill）**：
```yaml
description: Pre-commit gate — fires when committing, creating a PR,
  or another skill needs lint validation before merge
```

---

### 思路 C：结构分离式（gstack triggers 字段）

**核心逻辑**：用专用 `triggers` 字段承担路由匹配，description 回归产品描述，两层职责物理分离。

**特征列表**：
- `triggers` 字段：路由关键词列表
- `description` 字段：能力/产品描述，说清楚这个工具是什么
- description 允许包含功能范围、少量流程说明
- description 更像"README 第一行"而不是触发条件
- 品牌/来源标记（如 `(gstack)`）可以加在 description 末尾

**适用场景**：
- 生态规模大，需要系统化路由管理
- Skill 更像"工具/产品"，有自己的品牌定位
- 触发关键词和能力描述天然是两套语言

**广度/深度策略**：`triggers` 负责广度（关键词覆盖），`description` 负责深度（能力边界）。

**边界**：
- 依赖宿主平台支持 `triggers` 字段（Claude Code 不原生支持此字段）
- 如果平台只读 description 做路由，此方案会失效

**示例写法（lint 前置检查 Skill）**：
```yaml
description: Pre-merge lint gate — runs ESLint and TypeScript checks,
  blocks commits until they pass. (project)
triggers:
  - lint check
  - pre-commit
  - before PR
  - code quality gate
```

---

## 四、对比表

| 维度 | 条件触发式（Superpowers） | 双职融合式（MSkill） | 结构分离式（gstack） |
|------|--------------------------|---------------------|---------------------|
| **description 的核心职责** | 触发条件，仅此一项 | 触发 + 是什么，压缩共存 | 能力描述（触发外包给 triggers）|
| **工作流摘要** | 严格禁止（有实测证据） | 不建议，但通过 leading word 压缩可接受 | 允许（autoplan 案例） |
| **起始格式** | 必须 "Use when..." | 以 leading word 开头 | 产品名或动名词 |
| **额外信息标准** | 服务触发的症状/场景 | 可达性声明（reach clause） | 功能范围、品牌标记 |
| **context load 意识** | 强（500 字符上限） | 极强（token 经济是核心） | 弱（triggers 分担了精确匹配） |
| **依赖平台特性** | 不依赖 | 不依赖 | 依赖 triggers 字段 |
| **操作约束的去向** | 进 body | 进 body（信息层级 #1） | 进 body |

---

## 五、逐条回答悬而未决的设计问题

### 问题 1：边界在哪里？

**研究结论**：操作内容（工作流、步骤、参数）一律不进 description——这三个生态对此高度一致，分歧只在"多严格"。

Superpowers 给出最强约束，有实测证据支持：哪怕一句流程摘要都会让 Agent 把 description 当捷径、跳过 body。MSkill 通过 leading word 经济压缩，隐式避免了操作内容（leading word 替代的是概念，不是步骤）。gstack 因为有 `triggers` 字段承担路由，description 可以稍微宽松，但操作约束也进 body。

**实际可操作的边界判断**：问自己一句话——"这句话帮 Agent 决定'要不要用这个 Skill'，还是帮 Agent 决定'怎么用这个 Skill'？" 前者属于 description，后者属于 body。

---

### 问题 2：额外信息的必要性

**研究结论**：三种"必要额外信息"有研究支撑：

1. **触发信号的具体化**（所有三方认同）：症状、情境、前提条件——只要它们服务于"让 Agent 认出该触发这个 Skill"，都是合法的。比如 "before writing implementation code" 是前提条件，帮 Agent 判断时机。

2. **可达性声明**（MSkill 独有）：当这个 Skill 需要被其他 Skill 调用时，description 里需要有 "when another skill needs…" 这样的声明，否则调用方 Skill 无法找到它。

3. **负向触发信号**（Superpowers）："when NOT to use" 有时需要出现在 description（或 "When to Use" 节），避免误触发。技术领域标注（"when using React Router"）也是必要的范围约束。

**不必要的额外信息**：Skill 能做什么（能力边界）、分几步完成、输出格式——这些都进 body。

---

### 问题 3：操作内容的归宿

**研究结论**：操作约束进 body，这是三方共识，但层级策略有差异。

MSkill 提供了最清晰的 **信息层级**（information hierarchy）框架：
1. In-skill step — 进 SKILL.md 作为有序步骤（最高优先级）
2. In-skill reference — 进 SKILL.md 作为规则/定义，按需查阅
3. External reference — 推出到独立文件，通过 context pointer 加载

操作约束大多属于第 1 层（步骤）或第 2 层（规则）。什么时候推到第 3 层？MSkill 的判断标准是：只有部分 branch 需要的内容，才需要 progressive disclosure（推到外部文件）；所有 branch 都需要的内容，留在主文件。

---

## 六、尚未解答的更深问题（补充）

研究过程中新发现的问题，原始 principle.md 未收录：

- **双系统问题**：当 Agent 同时拥有 description（触发）和 triggers（关键词匹配），两者冲突时谁优先？gstack 的实践隐含了答案（description 为主，triggers 为辅），但未显式说明。
- **context load 的实际影响**：MSkill 和 Superpowers 都强调压缩 description 以减少 context load，但没有量化阈值——多长算"太长"？这个边界在哪里？
- **leading word 的可用性**：MSkill 的 leading word 策略对有明确概念的 Skill 效果最好（lesson, tracer bullets），但对"工具型"Skill（如 "run-lint"）效果存疑——这类 Skill 缺乏合适的 leading word 候选。

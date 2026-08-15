---
title: 研究报告 — Skill 代码块使用标准
date: 2026-07-04
---

> 关联文档：[[principle]]
> 示例场景统一使用：**"在 Skill 中说明「创建数据目录」这一步"**

---

## 研究对象

| 生态 | Skill | 选取理由 |
|------|-------|----------|
| G stack | `ship` | 最重度执行类 Skill，代码块使用密度最高 |
| Superpowers | `writing-skills` | 直接关于如何写 Skill，对代码块使用有明确立场 |
| MSkill | `writing-great-skills` | 直接关于如何写 Skill，代表极简主义方向 |

---

## 逐一解析

### G stack — `ship`

**核心机制**

ship 的代码块分两层：

1. **Preamble（基础区）**：整块 50+ 行 bash 脚本，一次性运行，设置会话状态（branch、session_kind、telemetry、routing 等）。这里的代码块是"脚手架"——必须按此精确执行，不能让 agent 自行推导。

2. **主流程（决策区）**：改用散文 + inline code。例如：
   > "run `~/.claude/skills/gstack/bin/gstack-config set telemetry community`"
   > "run `touch ~/.gstack/.telemetry-prompted`"

   短小且精确的命令嵌在句子中（inline code），而非独立代码块。

**关键设计决策**

- 脚手架代码（需精确执行的多步初始化）→ 独立代码块
- 单条精确命令（运行特定 CLI 工具）→ 散文内 inline code
- 条件判断逻辑（if/else 路由）→ 纯散文，不写成 bash

**原文关键句**

> "If A: run `~/.claude/skills/gstack/bin/gstack-config set telemetry community`"

解读：知道这个命令不显而易见（路径很长、有特定参数），所以保留；但它足够短，不需要独立代码块——inline code 够了。

---

### Superpowers — `writing-skills`

**核心机制**

代码块用于**对比示范**，不用于执行指令。模式是：

```yaml
# ❌ BAD: ...
description: ...

# ✅ GOOD: ...
description: ...
```

即"错误 vs 正确"对比，帮助 agent（或人类）识别模式，而不是告诉 agent 运行什么。

**关键设计决策**

- 明确提出 **Token Efficiency**（词数）作为核心约束，并给出具体数字目标（getting-started workflows: <150 words）
- "Move details to tool help"：工具 flags 不要写进 Skill，写 `--help` 即可
- 代码块用于：YAML frontmatter 示例、特定命令（`wc -w`、`./render-graphs.js`）、结构模板

**原文关键句**

> "Move details to tool help: `search-conversations supports multiple modes and filters. Run --help for details.`"

解读：如果模型可以通过 `--help` 获取信息，就不应该把信息复制进 Skill——这会产生冗余，且信息会过时。

> "One excellent example beats many mediocre ones."

解读：代码块（示例）应精而少，不应覆盖所有情况。

---

### MSkill — `writing-great-skills`

**核心机制**

全文无 bash 代码块。完全依赖**概念词汇**（leading words）激活模型预训练知识。

例如，不是告诉 agent "按这个步骤审查"，而是定义 **premature completion**、**legwork**、**completion criterion** 等词，让 agent 在执行时自动调用这些概念。

**关键设计决策**

- **Leading words**：一个精准词汇比一段描述性文字更节省 token，且更稳定——模型对"premature completion"的理解来自预训练，不依赖 Skill 的具体措辞
- **单一真相源**（single source of truth）：避免重复，每个含义只写一次
- **No-op 测试**：每个句子问"如果删掉这句，模型行为会改变吗？"——不会就删

**原文关键句**

> "A leading word is a compact concept already living in the model's pretraining that the agent thinks with while running the skill. Repeated throughout the text, it accumulates a distributed definition and anchors a whole region of behaviour in the fewest tokens, by recruiting priors the model already holds."

解读：最高效的 Skill 写法不是"告诉模型做什么"，而是"激活模型已知的内容"。代码块与此思路相反——它是在告诉，而非激活。

---

## 三种核心思路

### 思路一：脚手架式（G stack ship）

**核心逻辑：** 代码块是执行路径的基础设施，必须精确运行时才写入。

**特征列表：**
- 复杂多步初始化 → 独立代码块
- 单条精确命令 → inline code（嵌在散文句子中）
- 条件路由逻辑 → 纯散文
- 「必须这样」→ 代码块；「通常这样」→ 散文

**适用场景：** Skill 依赖特定 CLI 工具链、有复杂的会话状态初始化、命令路径不可预测

**广度/深度策略：** 深度优先——把必须精确的那部分写清楚，其余信任 agent

**边界：** 不适用于纯逻辑描述；会产生大量 token 开销

**示例写法（「创建数据目录」）：**
> 创建 `.hskill/sync-design/` 目录，写入初始 manifest：
> ```bash
> mkdir -p .hskill/sync-design
> cat > .hskill/sync-design/manifest.json << 'EOF'
> { "version": 3, "entries": [] }
> EOF
> ```

---

### 思路二：对比示例式（Superpowers writing-skills）

**核心逻辑：** 代码块用于展示正确与错误的对比，不用于执行指令。

**特征列表：**
- 代码块 = ❌ bad vs ✅ good 对比
- 不展示执行路径，展示判断标准
- Token 词数作为硬约束，有具体数字目标
- 非显而易见的命令语法才写代码块（如渲染脚本）

**适用场景：** Skill 本身是关于"如何做判断"的指导文档；目标读者是生成 agent 或人类作者

**广度/深度策略：** 广度优先——覆盖所有判断场景，每个场景给一个对比示例

**边界：** 如果 Skill 是纯执行类（agent 需要运行命令），对比示例不够用

**示例写法（「创建数据目录」）：**
> ```
> # ❌ BAD: 写死命令，agent 照抄，跨环境可能出错
> mkdir -p .hskill/sync-design && echo '{}' > manifest.json
>
> # ✅ GOOD: 描述意图，agent 自行决定执行方式
> 创建 `.hskill/sync-design/` 目录，写入初始 manifest.json
> ```

---

### 思路三：激活式（MSkill writing-great-skills）

**核心逻辑：** 不写代码块。用精确的概念词汇激活模型预训练知识，而非告诉模型做什么。

**特征列表：**
- 几乎无代码块
- 大量"leading words"（premature completion、legwork、completion criterion）
- No-op 测试删除冗余：删掉后行为不变就删掉
- 单一真相源：同一含义不写两次

**适用场景：** 参考类 Skill；高层流程指导；目标是让 agent 内化判断逻辑而非执行步骤

**广度/深度策略：** 极度精简——只写模型不会自行激活的那一部分

**边界：** 对具体操作类的 Skill 不够用；需要 agent 有足够强的推断能力

**示例写法（「创建数据目录」）：**
> 创建数据目录，写入初始 manifest。

（无代码块；agent 自行处理路径和格式）

---

## 对比表

| 维度 | 脚手架式（G stack） | 对比示例式（Superpowers） | 激活式（MSkill） |
|------|---------------------|--------------------------|-----------------|
| 代码块功能 | 基础设施执行 | 判断对比示范 | 几乎不使用 |
| 判断标准 | 是否需精确执行 | 是否需对比展示 + token 预算 | 是否能激活预训练 |
| 散文 vs 代码块 | 逻辑散文 + 基础设施代码块 | 大量散文 + 对比代码块 | 全散文 |
| 对环境差异的处理 | 脚手架内处理（条件判断写在 bash 里） | 去除（告诉 agent 用 --help） | 完全交给 agent |
| 适用 Skill 类型 | 重度执行类（CI/deploy） | 指导类（如何写 Skill） | 参考类（概念体系） |
| 生成端友好性 | 中（脚手架需人工确认） | 高（对比模式易于生成） | 高（简单易写） |
| 审查端友好性 | 中（代码块清晰但量大） | 高（❌/✅ 一眼判断） | 低（难以验证行为） |

---

## 回答悬而未决的设计问题

### 问题一：如何判断"模型能否自行推断"？

**研究结论：** 三种生态提供了三个不同的判断框架，综合可得一个可操作的三层判断：

**第一层：语法层**（复杂度）
- 语法非标准或组合 flag 不显而易见 → 保留（G stack: git triple-dot, 特定 CLI 路径）
- 标准操作（mkdir、mv、cat）→ 去除（MSkill 完全不写；Superpowers 仅在对比时写）

**第二层：环境层**（跨平台差异）
- 命令跨环境行为有差异 → 去除，让 agent 自适应（Superpowers: 用 `--help` 代替写死 flags）
- 命令需要精确版本/路径（如特定 CLI 工具路径）→ 保留（G stack: `~/.claude/skills/gstack/bin/...`）

**第三层：功能层**（是否是脚手架）
- 是初始化脚手架的一部分（多步骤、设置状态）→ 保留为代码块
- 是单次精确命令 → inline code，不独立成代码块
- 是条件逻辑 / 判断 → 不写代码块，写散文

**收敛结论：** 出错代价（风险性）并不是独立维度——它通过"语法层"和"功能层"已经被覆盖。高风险操作（如 rm -rf）的"危险"来自语法的不显而易见，而不是风险本身需要代码块。

---

### 问题二：标准如何同时服务两种使用场景？

**研究结论：** 两种使用场景对格式的需求确实不同，但不矛盾：

- **生成时遵守（agent authoring）**：激活式和对比示例式最适合——生成 agent 可以直接应用"只有特殊语法/容易出错/脚手架才写代码块"这个原则，不需要每次人工判断
- **审查时兜底（human review）**：对比示例式的 checklist 最清晰——人类审查时可以对每个代码块问"这符合哪条保留条件？"

**结论**：原则用于生成时内化，checklist 用于审查时对照，两者互补而非冲突。

---

### 问题三：灰色地带的边界案例

**研究发现的新案例：**

| 案例 | 推荐处理 | 来源依据 |
|------|----------|----------|
| 特定 CLI 工具路径（`~/.gstack/bin/xxx`） | 保留 inline code（嵌入散文） | G stack: 路径不可预测 |
| 工具 flags（如 `--name-only`） | 保留代码块（语法层） | 本项目实践 |
| `--help` 可查的 flags | 去除，改写 "运行 `--help` 查看" | Superpowers: token 效率 |
| 多步骤初始化（mkdir + 写文件 + 配置） | 保留为独立代码块（脚手架层） | G stack: preamble 模式 |
| 单条 mkdir / touch | 去除，改为散文描述 | MSkill + 本项目实践 |
| 带副作用的操作（git push、rm）| 不依赖代码块，改用散文强调风险 | Superpowers: 用语言强调，非代码块 |

---

## 综合判断框架（可操作版）

**原则（生成时内化）：**

> 代码块的存在是为了传达"这里有语法非显而易见、或环境路径不可预测、或是多步脚手架"的信号。如果这三个条件都不满足，用散文描述。

**Checklist（审查时对照）：**

对每个代码块逐一问：

- [ ] **语法层**：这段命令的 flag 组合或语法，模型不熟悉的概率 > 50%？
- [ ] **环境层**：这个路径或工具名是当前生态特有的，跨环境会不一样？
- [ ] **脚手架层**：这是多步初始化的一部分，需要精确按顺序执行？
- [ ] **对比层**：这是在展示 ❌ vs ✅ 对比，用于教 agent 判断？

以上任一为是 → 保留。全部为否 → 改为散文。

**Inline code vs 独立代码块：**

- 单条命令，嵌在决策散文中 → inline code（`run <command>`）
- 多行命令或需要精确结构 → 独立代码块

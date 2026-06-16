---
name: migrate-spec
description: "Processes unprocessed design spec files into formal Diataxis documentation. Locates the superpowers/specs/ directory, scans for spec files whose YAML frontmatter lacks a 'migrated:' field, reads them all, does a cross-spec horizontal comparison to identify the latest authoritative content per topic, plans a document set from the topic matrix, cross-checks against INDEX.md, then writes or updates formal docs. Finishes by annotating each spec's frontmatter with migration metadata. Triggers: 'migrate specs', 'process spec files', 'spec migration to docs', 'process unprocessed specs'."
user_invocable: true
version: "1.0.0"
---

# migrate-specs

将原始设计 spec 整理成正式 Diataxis 文档的完整流程。核心原则：spec 往往成批写出、相互重叠、状态滞后，因此必须先读完所有内容、横向对比，再动手写文档。

---

## Step 1 — 定位 specs 目录，扫描未处理的 spec

首先找到 `superpowers/specs/` 目录，通常在 `docs/` 下，但先用搜索确认：

```bash
find . -type d -name "specs" | grep superpowers
```

找到后记住这个路径，本次 session 后续所有步骤都用它，不再重复搜索。

逐个读取该目录下的 `.md` 文件头部（约 15 行），检查是否有 `migrated:` 字段。

**未处理的 spec** 满足以下任一条件：
- 没有 YAML frontmatter（`---` 块），或
- frontmatter 中没有 `migrated:` 字段

向用户报告哪些 spec 未处理后再继续。若全部已迁移，直接告知并停止。

---

## Step 2 — 完整读取所有未处理的 spec

在开始分析之前，把每个未处理的 spec 全部读完。Step 3 的横向对比需要同时看到所有内容，不能边读边写。

---

## Step 3 — 横向对比（不可跳过）

这是最重要的一步。spec 之间经常重叠——两个 spec 可能覆盖同一主题，较新的那个会覆盖较旧的。逐个迁移会产生冗余或矛盾的文档。

### 3a. 构建主题矩阵

对跨 spec 发现的每个主题、设计决策或接口，记录哪些 spec 涉及它：

```
主题                          | 涉及的 spec                    | 最新
------------------------------|-------------------------------|------------------
hooks 安装逻辑                | hooks-design, hook-version    | hook-version ✅
tool 安装版本感知              | installer-cli, tool-upgrade   | tool-upgrade ✅
branch-cleanup 配置格式       | git-cleanup-design            | git-cleanup ✅
```

"最新"通常是日期更晚的 spec。同一天的两个 spec，优先选明确引用并扩展另一个的那个。

### 3b. 核实实现状态

对每个 spec，确认其描述的功能是否已实现。查看：
- `skills/` 下是否有对应的 skill 目录
- spec 自身的 `状态:` / `status:` 字段
- 必要时查 git 历史：`git log --oneline -- skills/`

不要只依赖 spec 自己的状态字段——它经常在实现后未更新。

### 3c. 处理覆盖关系

当 spec A 和 spec B 覆盖同一主题、且 B 更新或更完整时：
- B 的内容进入正式文档
- A 在 Step 6 标注 `superseded_by` 指向 B
- 仅当 A 包含 B 没有的补充内容时才保留 A 的那部分

---

## Step 4 — 从主题矩阵规划文档

在动任何文件之前，先决定需要写或更新哪些文档。直接从 Step 3 的主题矩阵出发。

### 4a. 起草文档计划

**逐段扫描每个 spec 的内容块**，对每一段（背景、设计决策、接口定义、实现说明……）单独判断类型，不要给整个 spec 贴一个标签——同一个 spec 经常同时含有多种类型的内容。

对每个内容块问一个问题：

```
"这段在回答什么问题？"
──────────────────────────────────────────────────────
用户怎么用这个功能？（操作步骤）      → how-to/
为什么这样设计？（原理、决策理由）    → explanation/
这个接口 / 格式 / 字段的准确定义？   → reference/
```

**explanation/ 的信号词**（出现时必须单独归类，不能混入 reference）：
- "为什么…"、"原因是…"、"选择…是因为…"
- "架构"、"设计原则"、"权衡"
- 某个函数 / 模块放在哪里以及为什么放在那里

逐段分类后，汇总成明确的文档计划再动笔：

```
文档计划
─────────────────────────────────────────────────────
hooks CLI 命令接口、输出格式      → reference/agent-cli-guide.md       # CLI 事实
getItemInfo() 设计原理、放置原因  → explanation/hskill-architecture.md  # why 内容
branch-cleanup 配置格式           → reference/branch-cleanup-config.md  # 配置规范
contribute-skill 使用指南         → how-to/contribute-skill.md          # 操作步骤
─────────────────────────────────────────────────────
```

**未实现功能的 spec**：稳定的架构决策仍规划进 `explanation/`，用简短注释标明功能待实现。

### 4b. 与 INDEX.md 比对

读取 `docs/INDEX.md`，对计划中的每个文档，找是否已有文件覆盖同一主题：
- **已存在，主题相同** → 改为更新该文件，不新建
- **已存在，角度不同** → 按计划新建，两篇文章互相加交叉链接
- **不存在** → 按计划新建

在动笔之前，为每个条目确定"新建还是更新"的最终结论。

### 4c. 执行计划

按最终计划逐一写作或更新文档，每个文件只放与其 Diataxis 类型匹配的内容。

---

## Step 5 — 更新 docs/INDEX.md

写完所有文档后，打开 `docs/INDEX.md`：
- 每个新文件在对应分类的表格中加一行
- 修改过的文件如果描述范围有变化，同步更新描述

描述要简洁、对 Agent 友好——它是判断是否需要读全文的主要依据。

---

## Step 6 — 标注已处理的 spec

对每个处理完的 spec，在文件顶部添加或更新 YAML frontmatter：

```yaml
---
migrated: YYYY-MM-DD
docs:
  - path/relative/to/docs/target.md   # 注释：什么内容放这里
  - path/relative/to/docs/other.md    # 章节或主题名
superseded_by:                         # 仅当该 spec 的某主题被更新 spec 完全覆盖时
  - other-spec-filename.md            # 注释：被覆盖的是哪个主题
implemented_in:                        # 仅当设计内容嵌在 skill 或代码文件里而非正式文档时
  - skills/category/skill-name/SKILL.md
---
```

字段规则：
- `migrated` — 始终设置，使用今天的日期
- `docs` — 接收了该 spec 内容的所有正式文档；用行内 YAML 注释（`#`）说明对应章节
- `superseded_by` — 仅当该 spec 对某主题的覆盖被更新 spec 完全取代时设置；注释说明是哪个主题
- `implemented_in` — 仅当设计实现在 skill 文件或 reference 文件中、而非正式文档时设置

若 spec 正文有 `**状态：** 待实现`，根据 Step 3b 核实的结果更新。

---

## 仅标注模式

若用户只要求"补标注"而不重新写文档，跳过 Step 4 和 5，只执行 Step 1–3（确定每个 spec 对应什么）和 Step 6。

---

## 常用命令

```bash
# 找 specs 目录
find . -type d -name "specs" | grep superpowers

# 列出未处理的 spec（frontmatter 中没有 migrated:）
grep -rL "^migrated:" <specs-dir>/

# 检查功能是否已实现
find skills/ -type d -name "<feature-name>"
```

frontmatter 完全缺失的文件也算未处理。

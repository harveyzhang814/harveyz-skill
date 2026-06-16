# init-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the `init-skill` meta skill that scaffolds a new skill from a design spec or free-form notes, applying skill authoring best practices during generation.

**Architecture:** Two files — `SKILL.md` (the skill itself, 6-step flow) and `references/skill-authoring-guide.md` (the living best-practices reference it reads at runtime). The skill extracts key fields from a design doc, checks them against the authoring guide, confirms with the user, then generates SKILL.md + directory + branch.

**Tech Stack:** Markdown, YAML frontmatter, Bash (git, mkdir), Node.js (for reading skills-index.json)

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `skills/meta/init-skill/SKILL.md` | The skill itself |
| Create | `skills/meta/init-skill/references/skill-authoring-guide.md` | Best-practices reference read at runtime |
| Modify | `skills-index.json` | Register the skill (via publish-skill in Task 3) |

---

## Task 1: Create skill-authoring-guide.md

**Files:**
- Create: `skills/meta/init-skill/references/skill-authoring-guide.md`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p /Users/harveyzhang96/Projects/harveyz-skill/skills/meta/init-skill/references/
```

- [ ] **Step 2: Write skill-authoring-guide.md**

Write the following content to `skills/meta/init-skill/references/skill-authoring-guide.md`:

```markdown
# Skill Authoring Guide

本文档是编写高质量 skill 的参考标准，供 `init-skill` 在生成新 skill 时检查并应用。分两类：
- **显性规范**：来自 `docs/reference/skill-spec.md` 的硬性规则
- **隐性模式**：从现有优质 skill 提炼的最佳实践

---

## 显性规范（F1–F7，来自 skill-spec.md）

### 命名规范（F7）

格式：`<verb>-<noun>`，恰好 2 词，连字符分隔，全小写。

**规范动词词表：**

| 动词 | 含义 |
|------|------|
| `extract` | 从来源提取结构化数据 |
| `learn` | 处理教学/视频内容 |
| `forge` | 生成文档产物 |
| `draw` | 创建可视化图表 |
| `manage` | 组织文件或目录 |
| `migrate` | 跨格式或位置转换数据 |
| `scout` | 调查外部来源 |
| `build` | 构建配置或制品 |
| `sync` | 保持两端同步 |
| `publish` | 推送到外部注册表 |
| `archive` | 移至归档或退役 |
| `contribute` | 将外部内容引入本仓库 |
| `analyze` | 深度检查或分析 |
| `clean` | 清理废弃项 |
| `release` | 创建版本发布 |
| `validate` | 验证或校验 |
| `init` | 初始化新配置 |
| `dispatch` | 派发任务 |
| `close` | 收尾完成任务 |
| `setup` | 准备环境 |
| `capture` | 记录想法或洞察 |
| `dedup` | 检测消除重复内容 |
| `runby` | 委托给指定外部工具（特殊前缀，后接工具名） |

**违规示例：** `skill-analyzer`（动词不在词表）、`diagram`（单词）、`doc-forge`（应为 `forge-doc`）

### frontmatter 字段（F1–F5）

每个 SKILL.md 必须包含：

```yaml
---
name: <与目录名完全一致>
description: "<英文，≥ 10 字符，含触发短语>"
user_invocable: true   # 或 false
version: "1.0.0"       # semver，新 skill 从 1.0.0 开始
---
```

### 语言规范（F3、F6）

- `description` 字段：**必须为英文**，不含中文字符
- 正文内容：**必须含至少一个中文字符**

---

## 隐性模式（从现有优质 skill 提炼）

### 正文结构惯例

推荐节顺序：
1. **触发条件**（覆盖"触发"和"不触发"两种情况）
2. **执行步骤**（Step 0 / Step 1 / Step N，每步一个原子操作）
3. **不在范围内**（明确边界，防止误用扩大）

每个 Step 应对应一个可验证的原子操作，不要把两个动作合并进一步。

### description 写法

**格式模板：**
```
"<动词短语描述功能>. Triggers: '<场景1>', '<场景2>', '<场景3>'."
```

**要点：**
- 触发词宁宽勿窄，但避免与现有 skill 重叠
- 举例比泛描述精确：用 `'create new skill', 'scaffold skill'` 而不是 `"when user wants to create skills"`
- 检查是否覆盖了中文触发方式（如 `'新建 skill'`、`'从 spec 创建'`）

检查现有 skill 的 description 是否有重叠：
```bash
grep -r "^description:" skills/*/*/SKILL.md
```

### 边界说明（不在范围内）

- **必须有**"不在范围内"节，列出 2-4 个常见误用场景
- 防止 skill 在对话中被过度扩展
- 推荐格式：
  ```
  ## 不在范围内
  - <误用场景>（应使用 <替代 skill>）
  ```

### references/ 子目录

**使用时机：**
- Skill 需要携带查找表、模板、禁忌清单
- 参考材料超过 20 行，内联会影响 SKILL.md 可读性

**不使用时机：**
- 小规模内容（< 20 行）直接内联在 SKILL.md

### Step 粒度

- 每步对应一个可验证的结果
- 步骤名用"动词 + 名词"：`Step 1 — 定位设计文档`
- 有用户交互（等待确认）的步骤，明确写"等用户确认后才进入 Step N+1"

### 触发条件与其他 skill 的区分

若功能与现有 skill 有重叠，在触发条件节明确区分：
```
不触发（其他 skill 负责）：
- 从其他项目导入已有 skill → contribute-skill
- 校验格式或注册 index → publish-skill
```

### 活文档原则

本 guide 是活文档。发现新的好/坏模式后，更新本文件而不是修改 init-skill 的 SKILL.md。init-skill 运行时读取最新版本，自动生效。
```

- [ ] **Step 3: Verify file exists**

```bash
ls -la /Users/harveyzhang96/Projects/harveyz-skill/skills/meta/init-skill/references/skill-authoring-guide.md
```

Expected: file listed with non-zero size.

---

## Task 2: Create SKILL.md

**Files:**
- Create: `skills/meta/init-skill/SKILL.md`

- [ ] **Step 1: Write SKILL.md**

Write the following content to `skills/meta/init-skill/SKILL.md`:

```markdown
---
name: init-skill
description: "Initialize a new skill from scratch in the harveyz-skill repo — scaffolds SKILL.md, directory structure, and a feature branch from a design spec or free-form notes. Triggers: 'create new skill', 'scaffold a skill', 'init skill', 'bootstrap skill from notes', 'create skill from spec', 'help me start a new skill', 'initialize a skill', '从 spec 创建 skill', '新建一个 skill', '初始化 skill'."
user_invocable: true
version: "1.0.0"
---

# 从设计文档初始化新 Skill

将设计文档（结构化 spec 或自由格式笔记）转化为符合规范的 SKILL.md，创建目录结构和功能分支，交棒给 `publish-skill` 完成注册。

---

## 触发条件

触发本 skill：
- "创建新 skill"、"初始化一个 skill"、"新建 skill"
- "从这份 spec 生成 skill"、"help me start a new skill"
- "scaffold skill"、"bootstrap skill"

不触发（其他 skill 负责）：
- 从其他项目**导入**已有 skill → 使用 `contribute-skill`
- **校验格式或注册** index → 使用 `publish-skill`
- **修改**已有 skill 内容 → 直接编辑对应 SKILL.md

---

## 执行流程（6 步）

### Step 0 — 需求澄清

在任何操作之前，确认以下信息是否完整：

- **核心用途**：要创建的 skill 做什么？（哪怕一句话）
- **设计文档**：是否有 spec 文件路径或可粘贴的描述？还是完全从对话出发？
- **命名偏好**：是否有指定名称，或由 Claude 根据内容推断？

澄清策略：
- 每次只问一个问题，不堆叠
- 上下文能推断的不再问
- 持续提问直到需求完整、无歧义为止

只有需求明确后才进入 Step 1。

### Step 1 — 定位设计文档

按优先级定位输入来源：

1. 用户在对话中粘贴的描述文本 → 直接使用
2. 用户指定的文件路径 → 用 Read 工具读取
3. 自动扫描最近修改的 spec：
   ```bash
   ls -t docs/superpowers/specs/*.md | head -5
   ```
   列出候选文件供用户选择。

### Step 2 — 提炼要素 + 最佳实践检查

用 Read 工具读取 `references/skill-authoring-guide.md`，然后从设计文档中提取以下字段，以表格 + 建议形式展示给用户：

**提炼结果：**

| 字段 | 提取值 | 规范约束 |
|------|--------|---------|
| `name` | `<verb>-<noun>` 格式 | 动词必须在规范词表中 |
| `bundle` | 从现有 bundleMeta 中选 | 可新建 |
| `description` | 英文，含触发短语 | ≥ 10 字符，不含中文 |
| 正文大纲 | 中文，核心步骤列表 | — |
| `category` 目录 | 对应 bundle 的目录名 | — |

读取现有 bundle 列表：
```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "const i=JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8')); Object.entries(i.bundleMeta).forEach(([k,v])=>console.log(k+': '+v))"
```

**适用的最佳实践提示**（从 authoring guide 逐条检查，只列出适用的）：

```
[✓] <规范通过>  — <说明>
[!] <需要注意>  — <具体建议>
```

**等用户明确确认后才进入 Step 3。**

### Step 3 — 生成 SKILL.md

根据确认后的要素，生成完整 SKILL.md，遵循以下结构：

```
---
name: <name>
description: "<英文，含触发短语列表>"
user_invocable: true
version: "1.0.0"
---

# <正文标题（中文）>

## 触发条件
（覆盖"触发"和"不触发"两种情况）

## 执行步骤（Step 0 — Step N）

### Step 0 — 需求澄清
（如适用）

### Step 1 — ...
...

## 不在范围内
（2-4 条明确边界）
```

将生成内容展示给用户预览，确认无误后进入 Step 4。

### Step 4 — 创建目录并写入文件

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
mkdir -p "${REPO_ROOT}/skills/<category>/<name>/"
```

若目标路径已存在：停止并报错，提示用户使用 `publish-skill` 更新已有 skill，不覆盖任何文件。

用 Write 工具写入 `skills/<category>/<name>/SKILL.md`。

### Step 5 — 创建功能分支并初始 commit

```bash
git checkout -b feature/init-<name>
git add skills/<category>/<name>/
git commit -m "feat(skill): scaffold <name>"
```

输出摘要：
```
✓ SKILL.md 已生成：skills/<category>/<name>/SKILL.md
✓ 分支：feature/init-<name>
下一步：运行 /publish-skill 完成格式校验和 skills-index.json 注册
```

---

## 不在范围内

- 注册到 `skills-index.json`（由 `publish-skill` 负责）
- 修改或更新已有 skill（目标路径已存在时直接报错）
- 批量创建多个 skill（每次只处理一个）
- 编写 skill 的实际业务逻辑（只生成符合规范的骨架）
```

- [ ] **Step 2: Verify file exists**

```bash
ls -la /Users/harveyzhang96/Projects/harveyz-skill/skills/meta/init-skill/SKILL.md
```

Expected: file listed with non-zero size.

---

## Task 3: Validate format and register

**Files:**
- Modify: `skills-index.json` (registration)

- [ ] **Step 1: Run publish-skill to validate format**

Invoke the `/publish-skill` skill and point it at `meta/init-skill`. It will check F1–F7 and report any issues.

Expected: all format checks pass (F1–F7 ✓). If any fail, fix the SKILL.md before continuing.

- [ ] **Step 2: Register in skills-index.json via publish-skill**

When publish-skill asks which bundle to register under, choose `meta`.

After registration, run the generate script:

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill && node scripts/generate-npmignore.js
```

Expected: no errors. `skills-index.json` now contains an entry for `meta/init-skill`.

- [ ] **Step 3: Verify registration**

```bash
node -e "const i=JSON.parse(require('fs').readFileSync('skills-index.json','utf8')); const s=i.skills.find(x=>x.path==='meta/init-skill'); console.log(s || 'NOT FOUND')"
```

Expected output (something like):
```
{ path: 'meta/init-skill', bundle: 'meta' }
```

- [ ] **Step 4: Run npm test to verify full suite passes**

```bash
cd /Users/harveyzhang96/Projects/harveyz-skill && npm test
```

Expected: all tests pass including `skills.bats` which now validates `meta/init-skill`.

---

## Task 4: Commit

**Files:**
- `skills/meta/init-skill/SKILL.md`
- `skills/meta/init-skill/references/skill-authoring-guide.md`
- `skills-index.json`
- `package.json` (if updated by generate-npmignore.js)
- `.npmignore` (if updated by generate-npmignore.js)

- [ ] **Step 1: Stage all files**

```bash
git add skills/meta/init-skill/ skills-index.json package.json .npmignore
```

- [ ] **Step 2: Commit**

```bash
git commit -m "feat(skill): add init-skill — scaffold new skills from design docs"
```

- [ ] **Step 3: Verify clean state**

```bash
git status
```

Expected: `nothing to commit, working tree clean`

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|-----------------|------------|
| Step 0 需求澄清 | Task 2 SKILL.md Step 0 |
| Step 1 定位设计文档 | Task 2 SKILL.md Step 1 |
| Step 2 提炼要素 + 最佳实践检查 | Task 2 SKILL.md Step 2 |
| Step 3 生成 SKILL.md | Task 2 SKILL.md Step 3 |
| Step 4 创建目录结构 | Task 2 SKILL.md Step 4 |
| Step 5 功能分支 + commit | Task 2 SKILL.md Step 5 |
| skill-authoring-guide.md 显性规范 | Task 1 (full verb table, F1–F7) |
| skill-authoring-guide.md 隐性模式 | Task 1 (structure, description写法, references/, step粒度, 边界说明) |
| 活文档原则 | Task 1 (活文档原则节) |
| 注册到 skills-index.json | Task 3 (via publish-skill) |
| npm test 通过 | Task 3 Step 4 |

All spec requirements covered. No gaps.

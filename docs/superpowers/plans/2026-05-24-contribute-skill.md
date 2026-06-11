# contribute-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `contribute-skill` 元技能，允许用户在任意项目中调用它，将该项目的某个 skill 目录贡献进 harveyz-skill 仓库，完成格式规范化、注册登记、双向同步的完整流程。

**Architecture:** 纯 SKILL.md 指令式实现。Skill 是一个详细的 9 步协议文档，Claude 按步执行：识别源 skill → 定位 harveyz-skill 仓库（带本地缓存）→ 交互选 bundle → 格式规范化 → 复制注册 → 同步回源 → commit 报告。

**Tech Stack:** Markdown SKILL.md + `skills-index.json` 注册 + `node scripts/generate-npmignore.js` 生成脚本

---

## 文件结构

| 操作 | 路径 | 说明 |
|------|------|------|
| Create | `skills/meta/contribute-skill/SKILL.md` | 主 skill 文件，含完整 9 步协议 |
| Create | `skills/meta/contribute-skill/.gitignore` | 排除运行时生成的 `.config` 缓存文件 |
| Modify | `skills-index.json` | 新增 `meta` bundle 和 skill 注册条目 |
| Auto-generated | `package.json` (files[]) | 由 `generate-npmignore.js` 自动更新 |
| Auto-generated | `.npmignore` | 由 `generate-npmignore.js` 自动更新 |

---

## Task 1: 创建 contribute-skill 目录和核心文件

**Files:**
- Create: `skills/meta/contribute-skill/SKILL.md`
- Create: `skills/meta/contribute-skill/.gitignore`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p skills/meta/contribute-skill
```

Expected: 目录创建成功，无报错。

- [ ] **Step 2: 写入 `.gitignore`**

创建 `skills/meta/contribute-skill/.gitignore`，内容：

```
.config
```

- [ ] **Step 3: 写入 `SKILL.md`**

创建 `skills/meta/contribute-skill/SKILL.md`，完整内容如下：

```markdown
---
name: contribute-skill
description: "将其他项目的 skill 贡献到 harveyz-skill 仓库，完成格式规范化、注册登记、双向同步。触发词：把这个 skill 贡献到 harvey-skill、将这个 skill 注册进 harvey-skill 仓库、导入这个 skill 到 harveyz-skill。"
user_invocable: true
version: "1.0.0"
---

# contribute-skill

将当前项目的某个 skill 目录贡献进 `harveyz-skill` 仓库，完成格式规范化、注册登记、双向同步的完整流程。

---

## 触发场景

用户在**非** harveyz-skill 项目中说：
- "把这个 skill 贡献到 harvey-skill"
- "把 `.claude/skills/my-deploy` 导入到 harveyz-skill"
- "将这个 skill 注册进 harvey-skill 仓库"

---

## 执行协议（9 步）

### Step 1 — 识别源 skill 目录

按优先级识别要贡献的 skill：

1. **上下文推断**：从对话中当前提到的 skill 名、文件路径、`SKILL.md` 内容直接推断
2. **用户显式指定**：用户明确说明路径或名称
3. **扫描列出**：若上下文不明确，执行以下命令并列出候选供用户选择：
   ```bash
   ls .claude/skills/
   ```

验证：确认该目录存在且包含 `SKILL.md`，否则停止并报错。

---

### Step 2 — 定位 harveyz-skill 仓库

**配置缓存路径：** `~/.claude/skills/contribute-skill/.config`

格式：
```json
{
  "harveyzSkillPath": "/absolute/path/to/harveyz-skill"
}
```

**查找逻辑（按优先级）：**

```
1. 读取 ~/.claude/skills/contribute-skill/.config
   └── 若存在且 <path>/skills-index.json 存在 → 直接使用，跳过后续步骤

2. 尝试默认路径：~/Projects/harveyz-skill
   └── 若 ~/Projects/harveyz-skill/skills-index.json 存在 → 使用此路径

3. 搜索：
   find ~ -name "skills-index.json" -path "*/harveyz-skill/*" -maxdepth 6 2>/dev/null | head -1
   └── 若找到 → 取其父目录

4. 以上均失败 → 询问用户手动输入路径

找到后：写入 ~/.claude/skills/contribute-skill/.config，后续调用直接读取
```

---

### Step 3 — 确定目标名称

1. 读取源 `SKILL.md` frontmatter 中的 `name:` 字段
2. 展示给用户确认：
   ```
   目标目录名：<name>
   确认使用此名称？(回车确认 / 输入新名称)
   ```
3. 目标路径将为：`<harveyzSkillPath>/skills/<bundle-category>/<name>/`（category 在 Step 4 确定）

---

### Step 4 — 交互选 bundle

读取 harveyz-skill 的 `skills-index.json`，列出 `bundleMeta` 中所有现有 bundle：

```
现有 bundle：
  1. analysis      — 分析工具（skill-analyzer + git-cleanup）
  2. brainstorming — 设计与规划工具
  3. dev           — 开发工作流
  4. meta          — 元操作工具
  ... （以实际 bundleMeta 为准）
  N. [新建 bundle]

请选择目标 bundle（输入编号）：
```

若用户选择新建 bundle：
```
请输入新 bundle 名称（英文，如 deploy）：
请输入 bundle 描述（如 部署工具）：
```

---

### Step 5 — 确认摘要

展示完整操作预览，**等待用户明确确认后再执行**：

```
即将执行以下操作：

[复制]
  源：<当前项目路径>/.claude/skills/<name>/
      （列出目录中所有文件）
  目标：<harveyzSkillPath>/skills/<bundle-category>/<name>/

[注册]
  skills-index.json 新增：{"path": "<bundle-category>/<name>", "bundle": "<bundle>"}
  （若新建 bundle）bundleMeta 新增：{"<bundle>": "<description>"}

[同步回源]
  格式化后完整目录 → <当前项目路径>/.claude/skills/<name>/

确认继续？(y/n)
```

用户输入 `n` 则中止，不做任何修改。

---

### Step 6a — 格式规范化

读取源 `SKILL.md`，对照 harveyz-skill 规范检查并修复：

**必检字段：**

| 字段 | 规范 | 缺失时处理 |
|------|------|-----------|
| `name` | 必须存在，值与目录名一致 | 自动补填目录名，无需确认 |
| `description` | 必须含触发短语，2-3 句 | 根据 skill 内容补写；展示 diff 让用户确认 |
| `version` | semver 格式，如 `"1.0.0"` | 自动补填 `"1.0.0"`，无需确认 |
| `user_invocable` | 显式声明 `true` 或 `false` | 自动补填 `true`，无需确认 |
| frontmatter 包裹 | 标准 `---` YAML 块 | 自动修正格式，无需确认 |

**修复策略：**
- 可自动确定的字段（`name`、`version`、`user_invocable`、frontmatter 格式）：直接修复，无需用户确认
- 涉及内容重写的字段（`description`）：以 diff 形式展示修改前后，等用户确认后再应用

**若 `SKILL.md` 格式严重损坏**（无法解析 frontmatter）：停止执行，报告具体问题，让用户手动修复后重试。

---

### Step 6b — 执行复制与注册

按序执行以下操作：

**1. 复制 skill 目录**
```bash
cp -r <源目录>/ <harveyzSkillPath>/skills/<bundle-category>/<name>/
```

**2. 用格式化后的 SKILL.md 覆盖目标目录中的 SKILL.md**
（将 Step 6a 规范化后的内容写入目标路径）

**3. 更新 `<harveyzSkillPath>/skills-index.json`**

在 `skills[]` 数组末尾新增：
```json
{ "path": "<bundle-category>/<name>", "bundle": "<bundle>" }
```

若新建 bundle，在 `bundleMeta` 中新增：
```json
"<bundle>": "<用户输入的描述>"
```

**4. 运行生成脚本**
```bash
cd <harveyzSkillPath> && node scripts/generate-npmignore.js
```

若脚本执行失败：报告错误，**不执行 git commit**，保留已复制文件供用户检查。

**边界情况：目标路径已存在同名 skill**
```
目标路径已存在：skills/<bundle-category>/<name>/
选择操作：
  1. 覆盖（替换已有 skill）
  2. 重命名（输入新目录名）
  3. 中止
```

---

### Step 7 — 同步回源仓库

将 harveyz-skill 中目标 skill 目录的**完整内容**同步回源项目：

```bash
# 检测差异
diff -rq <harveyzSkillPath>/skills/<bundle-category>/<name>/ <源目录>/
```

- **若无差异**：跳过，不产生 commit，提示用户"源目录内容已是最新，无需同步"
- **若有差异**：
  ```bash
  cp -r <harveyzSkillPath>/skills/<bundle-category>/<name>/. <源目录>/
  ```
  然后在**源项目**当前分支执行：
  ```bash
  cd <源项目路径>
  git add .claude/skills/<name>/
  git commit -m "chore: sync skill format from harveyz-skill"
  ```

**边界情况：源项目无 git 仓库**
跳过 commit 步骤，仅提示用户"文件已同步，但源项目不是 git 仓库，请手动提交"。

---

### Step 8 — 在 harveyz-skill 创建分支并 commit

```bash
cd <harveyzSkillPath>

# 创建 feature 分支
git checkout -b feat/contribute-<name>

# 暂存所有变更
git add skills/<bundle-category>/<name>/
git add skills-index.json
git add package.json
git add .npmignore

# 提交
git commit -m "feat: contribute <name> from <source-project-name>"
```

---

### Step 9 — 报告

输出两个仓库的操作摘要：

```
✓ harveyz-skill
  - 新增 skill：skills/<bundle-category>/<name>/
  - 已注册到 bundle：<bundle>
  - 分支：feat/contribute-<name>
  - 下一步：git push origin feat/contribute-<name>，然后创建 PR → staging

✓ 源项目（<project-name>）
  - 已同步格式化内容：.claude/skills/<name>/
  - commit：chore: sync skill format from harveyz-skill
  （或：无变化，跳过 commit）
```

---

## 边界情况汇总

| 情况 | 处理 |
|------|------|
| 目标路径已存在同名 skill | 询问覆盖 / 重命名 / 中止 |
| 源 SKILL.md 格式严重损坏 | 停止，报告问题，等用户修复后重试 |
| `generate-npmignore.js` 失败 | 报告错误，不 commit，保留文件 |
| `.config` 路径失效 | 清除 .config，重新触发路径查找 |
| 源项目无 git 仓库 | 跳过源项目 commit，提示用户手动处理 |
| 源目录与目标同步后无差异 | 跳过 Step 7 的 commit |

---

## 不在范围内

- 批量贡献多个 skill（每次只处理一个）
- 自动 push 或创建 PR（用户手动决定）
- 删除或更新已贡献的 skill
```

- [ ] **Step 4: 验证文件创建**

```bash
ls -la skills/meta/contribute-skill/
```

Expected output:
```
.gitignore
SKILL.md
```

- [ ] **Step 5: 运行测试验证 SKILL.md 格式**

```bash
npm test
```

Expected: 所有测试通过（SKILL.md 格式校验应包含新创建的 contribute-skill）。若测试失败，检查 SKILL.md frontmatter 格式是否正确。

- [ ] **Step 6: Commit 此 task 的变更**

```bash
git add skills/meta/contribute-skill/
git commit -m "feat: add contribute-skill SKILL.md and gitignore"
```

---

## Task 2: 注册到 skills-index.json

**Files:**
- Modify: `skills-index.json`
- Auto-generated: `package.json`, `.npmignore`

- [ ] **Step 1: 更新 `skills-index.json`**

在 `skills-index.json` 的 `bundleMeta` 对象中新增 `meta` 条目，并在 `skills[]` 数组末尾新增 skill 条目。

修改后的 `skills-index.json` 相关部分：

```json
{
  "bundleMeta": {
    "analysis": "分析工具（skill-analyzer + git-cleanup）",
    "brainstorming": "设计与规划工具（brainstorming + writing-plans）",
    "dev": "开发工作流（executing-plans + systematic-debugging + using-git-worktrees + git-workflow-init）",
    "document": "文档工具（diataxis-docs）",
    "harness": "测试工具（full-stack-debug-env）",
    "task": "任务管理（pm-task-dispatch + task-close）",
    "web-fetch": "网页抓取工具（article-fetcher）",
    "writing": "写作工具（mermaid-diagram）",
    "design": "设计同步工具（sync-design-html）",
    "meta": "元操作工具（对 harveyz-skill 仓库本身的管理）"
  },
  "skills": [
    { "path": "analysis/skill-analyzer", "bundle": "analysis" },
    { "path": "harness/diataxis-docs", "bundle": "document" },
    { "path": "harness/full-stack-debug-env", "bundle": "harness" },
    { "path": "superpowers-fork/brainstorming", "bundle": "brainstorming" },
    { "path": "harness/git-workflow-init", "bundle": "dev" },
    { "path": "superpowers-fork/executing-plans", "bundle": "dev" },
    { "path": "superpowers-fork/systematic-debugging", "bundle": "dev" },
    { "path": "superpowers-fork/using-git-worktrees", "bundle": "dev" },
    { "path": "superpowers-fork/writing-plans", "bundle": "brainstorming" },
    { "path": "task/pm-task-dispatch", "bundle": "task" },
    { "path": "task/task-close", "bundle": "task" },
    { "path": "web-fetch/article-fetcher", "bundle": "web-fetch" },
    { "path": "writing/mermaid-diagram", "bundle": "writing" },
    { "path": "design/sync-design-html", "bundle": "design" },
    { "path": "analysis/git-cleanup", "bundle": "analysis" },
    { "path": "meta/contribute-skill", "bundle": "meta" }
  ]
}
```

- [ ] **Step 2: 运行生成脚本，更新 package.json 和 .npmignore**

```bash
node scripts/generate-npmignore.js
```

Expected: 无报错输出。`package.json` 的 `files[]` 和 `.npmignore` 会自动更新，包含 `skills/meta/contribute-skill/` 路径。

- [ ] **Step 3: 验证生成结果**

```bash
grep "contribute-skill" package.json
grep "contribute-skill" .npmignore
```

Expected:
- `package.json` 的 `files[]` 中应包含 `"skills/meta/contribute-skill"` 或类似条目
- `.npmignore` 中**不应**出现 `contribute-skill`（已注册的 skill 不会被排除）

- [ ] **Step 4: 再次运行测试**

```bash
npm test
```

Expected: 所有测试通过。

- [ ] **Step 5: Commit**

```bash
git add skills-index.json package.json .npmignore
git commit -m "feat: register contribute-skill in meta bundle"
```

---

## 自检结果

**Spec 覆盖检查：**
- ✅ Step 1（识别源 skill）→ SKILL.md Step 1
- ✅ Step 2（定位 harveyz-skill，带缓存）→ SKILL.md Step 2
- ✅ Step 3（确认名称）→ SKILL.md Step 3
- ✅ Step 4（交互选 bundle）→ SKILL.md Step 4
- ✅ Step 5（确认摘要）→ SKILL.md Step 5
- ✅ Step 6a（格式规范化）→ SKILL.md Step 6a
- ✅ Step 6b（复制 + 注册 + 生成脚本）→ SKILL.md Step 6b
- ✅ Step 7（同步整个目录回源）→ SKILL.md Step 7
- ✅ Step 8（创建 feature 分支 + commit）→ SKILL.md Step 8
- ✅ Step 9（报告）→ SKILL.md Step 9
- ✅ 所有边界情况 → SKILL.md 边界情况汇总
- ✅ `.config` 缓存持久化 → SKILL.md Step 2 + .gitignore

**Placeholder 扫描：** 无 TBD / TODO / 占位符。

**类型一致性：** 纯 markdown，无代码类型问题。

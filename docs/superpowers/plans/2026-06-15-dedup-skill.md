# dedup-skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 创建 `dedup-skill` meta skill，检测两个或多个 skill 之间的语义块级别重叠内容，给出归属建议并输出报告。

**Architecture:** 三步流程——语义块提取（对每个 skill 正文做语义切割）→ 跨 skill 块聚类（一次性找出"描述同一件事"的块组）→ 职责边界分析（给出归属建议）。输出 Markdown 报告，路径优先遵循 DIR_METHOD.md，否则写入 `docs/skill-analysis/`。

**Tech Stack:** Markdown SKILL.md（纯指令文件），无脚本依赖；注册到 `skills-index.json`，通过 `generate-npmignore.js` 更新打包配置。

---

## 文件结构

| 操作 | 路径 | 职责 |
|------|------|------|
| 创建 | `skills/meta/dedup-skill/SKILL.md` | 主 skill 指令文件 |
| 创建 | `skills/meta/dedup-skill/references/auto-scan.md` | 全量扫描模式的补充步骤 |
| 修改 | `skills-index.json` | 注册新 skill，更新 meta bundle 描述 |
| 修改（自动）| `package.json` + `.npmignore` | `generate-npmignore.js` 自动更新 |
| 修改 | `.claude/skills/dedup-skill/SKILL.md` | 项目级安装，供当前会话立即使用 |

---

## Task 1: 创建 SKILL.md 主文件

**Files:**
- Create: `skills/meta/dedup-skill/SKILL.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p skills/meta/dedup-skill
```

- [ ] **Step 2: 写入 SKILL.md**

写入以下完整内容到 `skills/meta/dedup-skill/SKILL.md`：

```markdown
---
name: dedup-skill
description: "Detect semantic overlap between two or more skills at the logical-block level. Use this skill whenever someone wants to compare skills for duplication, find overlapping steps between skills, check if two skills share logic, or audit skill responsibilities. Triggers: 'compare X and Y skills', 'find overlap between X and Y', '对比 skill 重叠', '检查这两个 skill 有没有重复', 'do X and Y duplicate logic', 'audit skill duplication'."
user_invocable: true
version: "1.0.0"
---

# dedup-skill

检测两个或多个 skill 之间的语义重复内容，粒度为**语义块级别**（不依赖标题结构）。
发现重叠后给出职责归属建议，用户决定处置方式。

---

## 触发方式

### 方式 A：指定 skill（主流程）

用户指令中给出 2 个或多个 skill 名，如：

- "对比 contribute-skill 和 skill-publish"
- "检查 dir-manage 和 diataxis-docs 的重叠"
- "compare archive-skill and contribute-skill"

提取 skill 名后进行**模糊匹配**：

读取 `skills-index.json` 获取所有已注册 skill 的 path 末段：

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path.split('/').pop()));
"
```

| 匹配结果 | 行为 |
|---------|------|
| 完全匹配 | 直接使用 |
| 部分匹配 1 个 | 展示候选："是否对比 `<name>`？(y/n)" |
| 部分匹配多个 | 列出候选，用户选择编号 |
| 0 匹配 | 报错：`未找到 <keyword>，请检查名称后重试` |

所有 skill 匹配确认后，展示列表等待用户确认，然后继续。

### 方式 B：未指定 skill

提示用户：

```
请指定要对比的 skill，例如："对比 contribute-skill 和 skill-publish"

如需全量扫描所有 skill，参见 references/auto-scan.md
```

---

## Step 1 — 语义块提取

读取每个指定 skill 的 `SKILL.md` 正文（frontmatter 结束后的所有内容）。

对每个 skill，将正文划分为独立**语义块**：

- **语义块的定义**：可独立存在的逻辑单元——一个操作步骤、一套校验规则、一段路径约定、一个边界情况列表
- **不依赖标题**：一个 `## Step` 下可能含多个块，相邻 `##` 也可能合并为一个块
- **每块记录**：`{skill名, 位置描述（如"Step 6a 格式规范化"）, 原文摘要（50字内）}`

提取完成后，在内部列出各 skill 的块清单（不需要展示给用户），供下一步使用。

---

## Step 2 — 跨 skill 块聚类

将所有 skill 的所有语义块集中在一起，一次性分析：

找出"描述同一件事"的块组，即**聚类**。每个聚类代表一处潜在重叠。

**聚类维度：**
- **逻辑等价**：两块做的事情完全相同（如两处都在"读取 skills-index.json 并遍历 skills[]"）
- **逻辑交叉**：两块部分重叠但侧重不同（如"校验字段 + 自动修复" vs "校验字段 + 报告问题"）

不做 N² 逐对比——把所有块一起交给分析，整体聚类效率更高，也能发现三方以上重叠。

若无任何聚类，跳到"无重叠情况"输出。

---

## Step 3 — 职责边界分析

对每个聚类，分析：

1. 各来源 skill 的整体定位（从 description 和正文判断）
2. 该块内容在各自 skill 里是**核心逻辑**还是**附带步骤**
3. 哪个 skill 更适合作为这块内容的权威归属

**归属建议原则：**
- 内容是该 skill 的核心目的 → 建议留在此处
- 内容是附带实现、另一个 skill 更专注于此 → 建议迁移或引用
- 两个 skill 都不可或缺 → 建议提取为 `references/` 共享文件，两处引用

---

## 输出

### 确定输出目录

按以下优先级：

1. 从 `docs/skill-analysis/` 向上逐级查找 `DIR_METHOD.md`
   - 找到 → 按 `DIR_METHOD.md` 声明的方法论放置文件（调用 dir-manage skill 处理）
2. 未找到 → 使用默认路径 `docs/skill-analysis/`，目录不存在时执行：
   ```bash
   mkdir -p docs/skill-analysis
   ```

### 报告文件名

`dedup-<YYYYMMDD-HHMMSS>.md`

### 报告结构

```markdown
# Skill 重叠分析报告
对比范围：<skill-a>, <skill-b>
生成时间：<timestamp>

## 内容重叠

### 重叠 1 — <主题描述>
**来源 A**：<skill-a> / <位置描述>
> <原文摘要>

**来源 B**：<skill-b> / <位置描述>
> <原文摘要>

**分析**：<职责边界对比，2-3 句>
**建议**：<具体可操作的归属建议>

### 重叠 2 — ...

---
## 未发现重叠的范围
<列出已对比但未发现重叠的领域，让用户知道分析完整>

---
## 下一步
发现 N 处内容重叠。要我帮你处理哪一个？
  1. <重叠1主题>（<skill-a> ↔ <skill-b>）
  2. ...
输入编号，或"先不处理"。
```

### 无重叠情况

```
✓ 对比完成：未发现 <skill-a> 与 <skill-b> 之间的内容重叠。
报告已保存：<输出路径>
```

---

## 边界情况

| 情况 | 处理 |
|------|------|
| 用户未指定 skill | 提示手动指定，说明 references/auto-scan.md |
| skill 名模糊匹配失败 | 报错，列出所有可用 skill 名 |
| 某个 skill 正文为空或极短（< 5 行） | 跳过，报告中注明"内容不足，跳过分析" |
| 对比同一个 skill 与自身 | 报错："请指定不同的 skill" |
| 发现三方以上重叠 | 报告中合并为一个聚类，建议统一归属 |

---

## 不在范围内

- 自动执行合并、迁移或删除（由用户配合 archive-skill / contribute-skill 处理）
- 检测 skill 与 references/ 文件之间的重叠
- 检测 archived/ 目录下的 skill
```

- [ ] **Step 3: 验证文件存在**

```bash
ls skills/meta/dedup-skill/SKILL.md
```

Expected: 文件存在，无报错。

- [ ] **Step 4: Commit**

```bash
git add skills/meta/dedup-skill/SKILL.md
git commit -m "feat(dedup-skill): add main SKILL.md"
```

---

## Task 2: 创建 references/auto-scan.md

**Files:**
- Create: `skills/meta/dedup-skill/references/auto-scan.md`

- [ ] **Step 1: 创建目录**

```bash
mkdir -p skills/meta/dedup-skill/references
```

- [ ] **Step 2: 写入 auto-scan.md**

写入以下内容到 `skills/meta/dedup-skill/references/auto-scan.md`：

```markdown
# 全量扫描模式

对 `skills/` 目录下所有已注册 skill 执行重叠检测。频率低，按需使用。

## 执行步骤

### Step 1 — 获取所有 skill 列表

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
node -e "
  const idx = JSON.parse(require('fs').readFileSync('${REPO_ROOT}/skills-index.json','utf8'));
  idx.skills.forEach(s => console.log(s.path));
"
```

### Step 2 — 触发域扫描（轻量）

读取所有 skill 的 `description` 字段，两两比较触发意图：

- 找出 description 语义高度重叠的 skill 对（同一类用户需求可能触发多个 skill）
- 输出：触发域重叠对列表（若无则跳过）

### Step 3 — 内容重叠分析

对触发域重叠对，以及任何你判断值得深入检查的 skill 对，
执行主 SKILL.md 的 Step 1（语义块提取）→ Step 2（跨 skill 块聚类）→ Step 3（职责边界分析）。

### Step 4 — 汇总报告

按主 SKILL.md 的输出格式生成报告，标注"全量扫描"模式，
文件名：`dedup-full-<YYYYMMDD-HHMMSS>.md`
```

- [ ] **Step 3: Commit**

```bash
git add skills/meta/dedup-skill/references/auto-scan.md
git commit -m "feat(dedup-skill): add references/auto-scan.md for full scan mode"
```

---

## Task 3: 注册到 skills-index.json 并更新打包配置

**Files:**
- Modify: `skills-index.json`
- Modify (auto): `package.json`, `.npmignore`

- [ ] **Step 1: 在 skills[] 中添加条目**

在 `skills-index.json` 的 `skills[]` 数组中，在 `meta/archive-skill` 之后添加：

```json
{ "path": "meta/dedup-skill", "bundle": "meta" },
```

- [ ] **Step 2: 更新 bundleMeta.meta 描述**

将 `bundleMeta.meta` 的值从：
```
"元操作工具（skill-analyzer + git-cleanup + contribute-skill + skill-publish + archive-skill + project-release）"
```
改为：
```
"元操作工具（skill-analyzer + git-cleanup + contribute-skill + skill-publish + archive-skill + dedup-skill + project-release）"
```

- [ ] **Step 3: 运行打包配置生成脚本**

```bash
node scripts/generate-npmignore.js
```

Expected 输出包含：`skills: 25`（比之前多 1）

- [ ] **Step 4: 验证**

```bash
grep "dedup-skill" package.json
```

Expected: 输出包含 `skills/meta/dedup-skill/`

- [ ] **Step 5: 运行测试**

```bash
npm test 2>&1 | grep -E "^(ok|not ok|# )"
```

Expected: 所有 skill 格式检查通过（dedup-skill 的 SKILL.md 满足格式要求）。doc-forge 的 Python 依赖失败是预先存在的问题，可忽略。

- [ ] **Step 6: Commit**

```bash
git add skills-index.json package.json .npmignore
git commit -m "feat(dedup-skill): register in skills-index.json and update packaging"
```

---

## Task 4: 安装到项目 .claude/skills/ 并验证

**Files:**
- Modify: `.claude/skills/dedup-skill/` (新建或覆盖)

- [ ] **Step 1: 安装到项目级 skill 目录**

```bash
cp -r skills/meta/dedup-skill .claude/skills/dedup-skill
```

- [ ] **Step 2: 验证安装**

```bash
ls .claude/skills/dedup-skill/
```

Expected: 输出包含 `SKILL.md` 和 `references/`

- [ ] **Step 3: 用 skill-publish 检查格式**

调用 skill-publish skill，对 `meta/dedup-skill` 执行格式检查：

触发词："检查 dedup-skill 是否符合格式要求"

Expected 结果：F1-F5 全部通过，R1-R3 全部通过。

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/dedup-skill/
git commit -m "chore: install dedup-skill to project .claude/skills/"
```

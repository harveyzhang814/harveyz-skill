# git-cleanup Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现 `git-cleanup` skill，帮助用户周期性梳理本地 git 分支，通过规则匹配 + LLM 语义分析分组推荐删除/保留，分组确认后批量执行。

**Architecture:** `command` hook 模式：SKILL.md 作为 Claude 的执行指令，读取 `.claude/branch-cleanup.md` 中的规则，先做 glob 规则过滤，再对未命中分支调用内嵌 LLM 分析，最后分三组展示供用户逐组确认。

**Tech Stack:** Bash（git 命令）、Markdown（SKILL.md + 配置文件）、glob 模式匹配（Claude 执行）

---

## 文件清单

| 操作 | 路径 | 说明 |
|------|------|------|
| Create | `skills/analysis/git-cleanup/SKILL.md` | skill 主体 |
| Modify | `skills-index.json` | 注册新 skill |
| Create | `.claude/branch-cleanup.md` | 本 repo 的清理规则配置 |

---

### Task 1：注册 skill 到 skills-index.json

**Files:**
- Modify: `skills-index.json`

- [ ] **Step 1：读取当前 skills-index.json，确认 analysis bundle 已存在**

```bash
cat skills-index.json | jq '.skills[] | select(.bundle == "analysis")'
```

预期输出：看到 `skill-analyzer` 条目。

- [ ] **Step 2：在 `skills` 数组中添加 git-cleanup 条目**

在 `skills-index.json` 的 `.skills` 数组末尾添加：

```json
{
  "path": "analysis/git-cleanup",
  "bundle": "analysis"
}
```

- [ ] **Step 3：更新 bundleMeta 中 analysis 的描述**

将：
```json
"analysis": "分析工具（skill-analyzer）"
```
改为：
```json
"analysis": "分析工具（skill-analyzer + git-cleanup）"
```

- [ ] **Step 4：验证 JSON 语法正确**

```bash
cat skills-index.json | jq '.skills[] | select(.bundle == "analysis")'
```

预期：同时看到 `skill-analyzer` 和 `git-cleanup` 两条。

- [ ] **Step 5：Commit**

```bash
git add skills-index.json
git commit -m "chore: register git-cleanup skill in skills-index"
```

---

### Task 2：创建 SKILL.md

**Files:**
- Create: `skills/analysis/git-cleanup/SKILL.md`

- [ ] **Step 1：创建目录**

```bash
mkdir -p skills/analysis/git-cleanup
```

- [ ] **Step 2：写入 SKILL.md**

创建文件 `skills/analysis/git-cleanup/SKILL.md`，内容如下：

````markdown
---
name: git-cleanup
description: "梳理并清理本地 git 分支。规则匹配 + LLM 语义分析，分组确认后批量删除废弃分支。触发词：清理分支、branch cleanup、梳理分支、删除旧分支、整理分支"
user_invocable: true
version: "1.0.0"
---

# SKILL.md — git-cleanup

> **版本：** v1.0.0
> **定位：** 周期性梳理本地 git 分支，识别可安全删除的废弃分支

---

## 触发条件

- "清理分支" / "整理分支" / "梳理分支"
- "branch cleanup" / "删除旧分支"

---

## Step 1：读取配置

检查 `.claude/branch-cleanup.md` 是否存在：

**存在** → 解析三段内容：
- `## Always Delete` 段：每行 `` `pattern` `` 为必删 glob 规则
- `## Always Keep` 段：每行 `` `pattern` `` 为必留 glob 规则
- `## LLM 判断上下文` 段：整段文本作为 LLM 分析的 context

**不存在** → 使用内置默认规则，执行完毕后提示生成配置文件：
- Always Delete：`chore/bump-*`、`chore/sync-*`、`chore/fix-*`
- Always Keep：`test/*`
- LLM context：「通用项目。保留标准：功能仍在迭代的分支、测试框架。删除标准：一次性任务、已完成的独立功能。」

---

## Step 2：收集分支数据

运行以下命令，记录结果：

```bash
git branch --show-current          # 记录当前分支名
git branch                         # 所有本地分支列表
git branch --merged staging        # 已合并进 staging 的子集
```

**跳过列表（不参与任何分析）：** `main`、`staging`、当前分支名

---

## Step 3：分类

对每条本地分支（不在跳过列表中），按以下优先级归类：

1. **未合并进 staging** → 直接归入 `GROUP_KEEP`，标注 `[未合并]`
2. **已合并 + 命中 Always Keep** → 归入 `GROUP_KEEP`，标注 `[规则保留: <pattern>]`
3. **已合并 + 命中 Always Delete** → 归入 `GROUP_DELETE_RULE`，标注 `[规则: <pattern>]`
4. **已合并 + 未命中任何规则** → 归入 `GROUP_AMBIGUOUS`，待 LLM 分析

**glob 匹配规则：** `*` 匹配任意字符（不含 `/`）。`chore/bump-*` 匹配 `chore/bump-0.3.0`，不匹配 `feature/bump-test`。

---

## Step 4：LLM 分析 GROUP_AMBIGUOUS

若 `GROUP_AMBIGUOUS` 非空，执行以下步骤：

**4a. 收集每条分支的最近 commit message：**

```bash
git log -1 --format="%s" <branch>
```

**4b. 内嵌分析（直接在当前上下文推断，无需单独调用）：**

根据以下 prompt 逻辑对每条分支作出判断：

```
项目上下文：
<来自配置文件的 LLM 判断上下文>

保留标准：功能仍在迭代、测试框架、基础设施、近期可能继续开发
删除标准：一次性任务（已完成）、独立功能（已合并不再扩展）、重构（已完成）

待判断：
- <branch> | <最近 commit message>
```

每条分支输出 `keep` 或 `delete` + 一句中文理由，分配到：
- `GROUP_KEEP`，标注 `[LLM 保留: <理由>]`
- `GROUP_DELETE_LLM`，标注理由

---

## Step 5：分组展示 + 逐组确认

### 组 A — 明显可删（规则命中）

若 `GROUP_DELETE_RULE` 非空，展示并等待确认：

```
━━━ 组 A：明显可删（规则命中，共 N 条）━━━
  • chore/bump-0.3.0    [规则: chore/bump-*]
  • chore/fix-lockfile  [规则: chore/fix-*]

确认删除这 N 条？[y = 删除 / n = 跳过]
```

### 组 B — LLM 建议删除

若 `GROUP_DELETE_LLM` 非空，展示并等待确认：

```
━━━ 组 B：LLM 建议删除（共 N 条）━━━
  • feature/agent-friendly-cli  — 文档类功能，已完成，不再扩展
  • feat/skill-vars-substitution — 重构任务，已合并

确认删除这 N 条？[y = 删除 / n = 跳过]
```

### 组 C — 保留清单（仅展示，无需操作）

```
━━━ 组 C：保留（共 N 条）━━━
  • feature/mermaid-diagram-skill  [规则保留]
  • test/harness-skills-eval       [规则保留]
  • feature/tool-version-detection [未合并]
```

---

## Step 6：执行删除

对用户确认的分组，逐条执行：

```bash
git branch -d <branch>
```

- 成功 → 记录已删除
- 失败（-d 安全检查拒绝）→ 报告错误，跳过，继续执行

**检查 remote 同名分支：**

```bash
git branch -r | grep "origin/<branch>"
```

若存在，在删除后统一提示：

```
⚠️ 以下分支有对应的 remote 分支，需手动清理：
  git push origin --delete <branch1>
  git push origin --delete <branch2>
```

---

## Step 7：收尾

**打印执行摘要：**

```
✅ 清理完成
   删除：N 条
   保留：M 条

当前分支列表：
  • <branch1>
  • <branch2>
```

**若本次无配置文件，询问：**

```
未检测到 .claude/branch-cleanup.md。
是否根据本次规则生成配置文件，方便下次复用？[y/n]
```

若用户确认，生成 `.claude/branch-cleanup.md`，内容包含本次使用的 Always Delete / Always Keep 规则和 LLM context。
````

- [ ] **Step 3：验证文件存在且 frontmatter 合法**

```bash
head -10 skills/analysis/git-cleanup/SKILL.md
```

预期：看到 `name: git-cleanup`、`user_invocable: true`。

- [ ] **Step 4：Commit**

```bash
git add skills/analysis/git-cleanup/SKILL.md
git commit -m "feat(skill): add git-cleanup skill SKILL.md v1.0.0"
```

---

### Task 3：创建本 repo 的 branch-cleanup.md 配置

**Files:**
- Create: `.claude/branch-cleanup.md`

- [ ] **Step 1：写入配置文件**

创建 `.claude/branch-cleanup.md`，内容如下：

```markdown
# Branch Cleanup Rules

## Always Delete（已合并后直接删除）
- `chore/bump-*` — 版本号 bump，每次发布新建，无需保留
- `chore/sync-*` — lockfile/版本同步，一次性任务
- `chore/fix-*` — 一次性 chore 修复
- `doc/*` — 文档更新，完成即归档

## Always Keep（无论是否合并都保留）
- `test/*` — 测试基础设施，持续迭代

## LLM 判断上下文
这是一个 Claude Code skills 个人仓库（harveyz-skill）。

保留标准：
- Skill 仍在开发或预期持续迭代的功能分支
- Eval/测试框架类分支（test/、harness 相关）
- 基础设施类（CLI 核心、安装器等有扩展空间的）

删除标准：
- 一次性任务：版本 bump、lockfile 修复、frontmatter 补全
- 已完成的独立功能（合并后明确不再继续）
- 文档类更新（已合并）
- 重构任务（已完成）
```

- [ ] **Step 2：验证文件内容**

```bash
cat .claude/branch-cleanup.md
```

预期：看到三段（Always Delete / Always Keep / LLM 判断上下文）。

- [ ] **Step 3：Commit**

```bash
git add .claude/branch-cleanup.md
git commit -m "chore: add branch-cleanup rules config for this repo"
```

---

### Task 4：手动测试 skill

**Files:** 无（测试步骤）

- [ ] **Step 1：确认 skill 可被 Claude Code 识别**

在 Claude Code 中运行：

```
/git-cleanup
```

预期：skill 被触发，开始执行 Step 1（读取 .claude/branch-cleanup.md）。

- [ ] **Step 2：验证分组展示正确**

观察输出，确认：
- 组 A 包含命中 `chore/bump-*` 等规则的分支（若有）
- 组 B 包含 LLM 分析结果（附理由）
- 组 C 包含保留分支
- `main`、`staging`、当前分支不在任何删除组

- [ ] **Step 3：验证安全约束**

确认未合并分支不出现在组 A 或组 B 中。

- [ ] **Step 4：如测试通过，merge 到 staging**

```bash
git checkout staging
git merge doc/git-cleanup-skill-spec   # 合并 spec 分支
git merge <当前实现分支>
```

---

## 参考资料

- 设计 Spec：`docs/superpowers/specs/2026-05-24-git-cleanup-design.md`
- 参考 Skill：`skills/analysis/skill-analyzer/SKILL.md`（frontmatter 格式）
- skills-index.json 格式：`jq '.skills[0]' skills-index.json`

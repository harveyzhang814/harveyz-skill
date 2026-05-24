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

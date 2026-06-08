---
migrated: 2026-05-29
docs:
  - how-to/git-cleanup.md
  - reference/branch-cleanup-config.md
---

# Git Cleanup Skill — Design Spec

**日期：** 2026-05-24
**状态：** 已实现（v1.0.0）

---

## 概述

`git-cleanup` skill：帮助用户周期性梳理本地 git 分支，识别可安全删除的废弃分支，保留有未来复用价值的分支。用户手动触发，按分组批量确认执行。

---

## 目标

- 减少 `git branch` 噪音，保持分支列表整洁
- 通过规则 + LLM 兜底的混合方式，给出准确的保留/删除建议
- 保留标准透明可配置，固化在每个 repo 的配置文件里

---

## 文件结构

```
skills/
  analysis/
    git-cleanup/
      SKILL.md          ← skill 主体

.claude/
  branch-cleanup.md     ← 每个 repo 的保留/删除规则（可选）
```

---

## 配置文件：`.claude/branch-cleanup.md`

Markdown 格式，供 Claude 直接读取。不存在时 skill 使用内置默认规则运行，结束后提示生成。

**格式示例：**

```markdown
# Branch Cleanup Rules

## Always Delete（已合并后直接删除）
- `chore/bump-*` — 版本号 bump，每次发布新建，无需保留
- `chore/fix-*` — 一次性 chore 修复
- `doc/*` — 文档更新，完成即归档

## Always Keep（无论是否合并都保留）
- `test/*` — 测试基础设施，持续迭代
- `feature/interactive-*` — 交互式功能，预期持续扩展

## LLM 判断上下文
这是一个 Claude Code skills 仓库。
保留标准：skill 开发中可能继续迭代的功能分支、eval/测试框架、基础设施类。
删除标准：一次性任务（版本 bump、lockfile 修复）、已完成且不再扩展的独立功能。
```

**内置默认规则（无配置文件时）：**
- Always Delete：`chore/bump-*`、`chore/sync-*`、`chore/fix-*`
- Always Keep：`test/*`、`main`、`staging`
- LLM context：通用判断（已合并且名称暗示一次性任务 → 删除）

---

## 执行流程

### Step 1：读取规则
- 检查 `.claude/branch-cleanup.md` 是否存在
- 存在则解析 Always Delete / Always Keep / LLM 上下文三段
- 不存在则使用内置默认规则，并在末尾提示生成

### Step 2：收集分支数据
```bash
git branch                      # 所有本地分支
git branch --merged staging     # 已合并进 staging 的子集
```

### Step 3：分类

```
所有本地分支
  ├─ main / staging / 当前分支    → 跳过（不参与分析）
  ├─ 未合并进 staging             → 归入"保留"（安全硬规则）
  └─ 已合并进 staging
        ├─ 命中 Always Keep       → 归入"保留"
        ├─ 命中 Always Delete     → 归入"明显可删"
        └─ 未命中任何规则          → 批量送 LLM 分析
```

**LLM 分析：** 一次调用，传入：
- 未命中规则的分支列表（名称 + 最近 commit message）
- 配置文件中的 LLM 判断上下文
- 输出：每条分支的 keep/delete 决策 + 一句理由

### Step 4：分组展示 + 分组确认

按以下顺序逐组展示，每组独立确认：

**组 A — 明显可删（规则命中）**
```
以下分支命中删除规则，建议清除（共 N 条）：
  • chore/bump-0.3.0   [规则: chore/bump-*]
  • chore/fix-lockfile [规则: chore/fix-*]
确认删除？ [y/N/s(跳过)]
```

**组 B — LLM 建议删除**
```
以下分支经分析建议删除（共 N 条）：
  • feature/agent-friendly-cli — 文档类功能，已完成，不再扩展
  • feat/skill-vars-substitution — 重构任务，已合并
确认删除？ [y/N/s(跳过)]
```

**组 C — 保留清单（展示，无需操作）**
```
以下分支将保留（共 N 条）：
  • feature/mermaid-diagram-skill（规则命中 / LLM 建议）
  • test/harness-skills-eval（规则命中）
  • feature/tool-version-detection（未合并，不删）
```

### Step 5：执行删除
- 使用 `git branch -d`（安全模式，未合并分支会报错拒绝）
- 若有 remote 同名分支（`origin/<name>`），列出但**不自动删除**，提示手动执行：
  ```
  ⚠️ 以下 remote 分支需手动清理：
    git push origin --delete chore/bump-0.3.0
  ```

### Step 6：收尾
- 打印最终保留分支清单
- 若本次运行无配置文件，询问："是否根据本次操作生成 `.claude/branch-cleanup.md`？"

---

## 安全约束

| 场景 | 处理 |
|------|------|
| `main` / `staging` / 当前分支 | 始终跳过，不参与分析 |
| 未合并进 staging 的分支 | 归入保留，不建议删除 |
| remote 分支 | 只提示，不自动删除 |
| `git branch -d` 失败 | 报告错误，跳过该分支，继续执行 |
| 用户对某组选"跳过" | 该组全部保留，继续下一组 |

---

## Skill 元信息

```yaml
name: git-cleanup
description: "梳理并清理本地 git 分支。规则匹配 + LLM 语义分析，分组确认后批量删除废弃分支。触发词：清理分支、branch cleanup、梳理分支、删除旧分支"
user_invocable: true
version: "1.0.0"
bundle: analysis
path: analysis/git-cleanup
```

---

## 不在本次范围内

- remote 分支自动删除（需手动）
- 跨多个 base branch 合并检测（当前只检查 staging）
- PR 状态检查（未接入 GitHub API）
- 定时自动触发（用户明确要求手动）

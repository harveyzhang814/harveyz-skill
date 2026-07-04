---
title: domain-vocab Skill 设计
date: 2026-07-03
status: approved
---

# domain-vocab Skill 设计

## 概述

`domain-vocab` 是一个项目级领域术语字典 skill，供用户和 agent 管理和查询业务专有名词。设计对齐 skill philosophy 05（领域术语统一），采用"定义+查询"的被动字典模式——不含主动守卫或冲突检测逻辑。

## 存放位置

`skills/coding/domain-vocab/SKILL.md`，归入 `coding` bundle。

## 词汇文件格式

词汇表存储于项目根目录下：

```
<project-root>/hskill/domain-vocab/vocab.md
```

文件格式：

```markdown
# Domain Vocabulary

## 术语名
定义文本（一到两句话，说清楚概念是什么，不是它做什么）。
_Avoid_: 旧叫法, 混用词, alternative-name
```

- 每个术语对应一个 `##` section
- 首次执行 `add` 时 skill 自动创建文件（含 `# Domain Vocabulary` 标题）
- 文件不存在时，`query`/`remove`/`update` 输出明确错误，提示先用 `add` 初始化

## 操作

### add `<term>`

1. 检查术语是否已存在；若存在，提示"已存在，请用 update"并退出
2. 提示用户输入**定义**（必填）
3. 提示用户输入 **Avoid 列表**（可留空，逗号分隔）
4. 在 `vocab.md` 末尾追加新 section

### query `<term>`

1. 按 `## <term>` 标题匹配，大小写不敏感
2. 返回完整条目（定义 + Avoid）
3. 未找到时，列出所有已有术语名，方便用户确认拼写

### update `<term>`

1. 找到对应 section，展示当前内容
2. 逐字段提示新值（留空则保持不变）：定义、Avoid 列表
3. 写回文件

### remove `<term>`

1. 找到对应 section，展示内容
2. 要求用户确认
3. 删除该 section（包含空行）

## Agent 加载约定

Skill 本身不自动注入词汇表到 session 上下文。推荐在项目 `CLAUDE.md` 中加入：

```markdown
每次 session 开始，读取 `hskill/domain-vocab/vocab.md`（如存在）。
```

这样所有 agent 在任务开始前都能加载术语表，无需显式调用 skill。

## 范围边界

- **不在范围内**：主动冲突检测、自动纠正用词、跨 session 守卫（这些属于 philosophy 05 的"主动守卫式"）
- **不在范围内**：技术层命名（函数名、变量名）——词汇表只存业务领域概念
- **在范围内**：任何在前后端或 AI/人类之间都可能出现的领域层概念

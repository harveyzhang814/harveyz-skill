---
title: dedup-skill design
date: 2026-06-15
status: approved
---

# dedup-skill — 设计文档

## 概览

`dedup-skill` 是一个 meta skill，用于检测两个或多个 skill 之间的语义重复内容。
检测粒度为**语义块级别**（不依赖标题结构），发现重叠后给出职责归属建议，用户决定处置方式。

- **位置**：`skills/meta/dedup-skill/SKILL.md`
- **bundle**：`meta`
- **触发**：用户指定要对比的 skill，如 "对比 contribute-skill 和 skill-publish"、"检查这两个 skill 有没有重复"

---

## 输入方式

### 方式 1：手动指定（主流程）

用户在指令中给出 2 个或多个 skill 名：

```
"对比 contribute-skill 和 skill-publish"
"检查 dir-manage 和 diataxis-docs 的重叠"
```

**模糊匹配逻辑**（同 archive-skill）：

| 匹配结果 | 行为 |
|---------|------|
| 完全匹配 | 直接使用 |
| 部分匹配 1 个 | 展示候选，用户确认 |
| 部分匹配多个 | 列出候选，用户选择 |
| 0 匹配 | 报错退出 |

确认所有 skill 匹配后展示列表，等用户确认后继续。

### 方式 2：未指定 skill

提示用户手动指定，并说明全量扫描可参考 `references/auto-scan.md`：

```
请指定要对比的 skill，例如："对比 contribute-skill 和 skill-publish"
如需全量扫描所有 skill，参见 references/auto-scan.md
```

---

## 核心分析流程（三步）

### Step 1 — 语义块提取

逐一读取每个指定 skill 的 `SKILL.md` 正文。

对每个 skill，将正文划分为独立语义块：
- **判断标准**：一个语义块是"可独立存在的逻辑单元"——一个步骤、一套校验规则、一段路径约定、一个边界情况表
- **不依赖标题**：纯语义判断，一个 `## Step` 下可能含多个块，也可能多个 `##` 合并为一个块
- **记录来源**：每块附带 `{skill名, 位置描述（如"Step 6a 格式规范化"）, 原文摘要（50字内）}`

### Step 2 — 跨 skill 块聚类

将所有 skill 的所有语义块集中在一起，一次性分析：

- 找出"描述同一件事"的块组（聚类），每个聚类是一处潜在重叠
- 不做 N² 逐对比，整体聚类效率更高，也能发现三方以上的重叠

聚类维度：
- **逻辑等价**：两块做的事情完全一样（如"读取 skills-index.json 中的注册路径"）
- **逻辑交叉**：两块部分重叠但侧重不同（如"校验字段 + 修复" vs "校验字段 + 报告"）

### Step 3 — 职责边界分析

对每个聚类：

1. 各 skill 的定位是什么（从 description 和正文整体判断）？
2. 这块内容在各自 skill 里是**核心逻辑**还是**附带步骤**？
3. 哪个 skill 更适合作为这块内容的权威归属？

**归属建议原则**：
- 内容是该 skill 的核心目的 → 留在此处
- 内容是附带实现、另一个 skill 更专注于此 → 建议迁移或引用
- 两个 skill 都需要 → 建议提取为 `references/` 共享文件

---

## 输出

### 报告文件

**输出目录按以下优先级确定：**

1. 向上查找 `DIR_METHOD.md`（从 `docs/skill-analysis/` 开始，逐级向上）
   - 找到 → 按 `DIR_METHOD.md` 声明的方法论放置文件（调用 dir-manage skill 处理）
2. 无 `DIR_METHOD.md` → 默认保存到 `docs/skill-analysis/dedup-<YYYYMMDD-HHMMSS>.md`，目录不存在时自动创建

文件名格式：`dedup-<YYYYMMDD-HHMMSS>.md`

结构：

```markdown
# Skill 重叠分析报告
对比范围：<skill-a>, <skill-b>
生成时间：<timestamp>

## 内容重叠

### 重叠 1 — <主题描述>
  来源 A：<skill-a> / <位置描述>
    > <原文摘要>
  来源 B：<skill-b> / <位置描述>
    > <原文摘要>

  分析：<职责边界对比，2-3 句>
  建议：<归属建议，具体可操作>

### 重叠 2 — ...

---
## 未发现重叠的范围
<列出对比了但未发现重叠的领域，让用户知道分析是完整的>

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
报告已保存：docs/skill-analysis/dedup-<timestamp>.md
```

---

## 边界情况

| 情况 | 处理 |
|------|------|
| 用户未指定 skill | 提示手动指定，说明 references/auto-scan.md |
| skill 名模糊匹配失败 | 报错，列出所有可用 skill 名 |
| 某个 skill 正文为空或极短 | 跳过该 skill，在报告中注明 |
| 对比同一个 skill 与自身 | 报错："请指定不同的 skill" |
| 发现三方以上重叠 | 报告中合并为一个聚类，建议统一归属 |

---

## references/ 文件

### `references/auto-scan.md`

全量扫描模式的步骤，用于低频的整仓库重叠排查：

1. 读取 `skills-index.json` 获取所有注册 skill 列表
2. 对所有 skill 两两比较 description，筛出触发域重叠对
3. 对筛出的对执行主流程的 Step 1-3
4. 生成完整报告

---

## 不在范围内

- 自动执行合并、迁移或删除（由用户配合 archive-skill / contribute-skill 处理）
- 检测 skill 与外部文档（references/）之间的重叠
- 检测 archived/ 目录下的 skill

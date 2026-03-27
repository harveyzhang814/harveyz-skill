# 评估报告 v0.2

**评估对象：** `iteration-01-gstack-v0.2.md`
**源码仓库：** `~/Repositories/gstack`
**评估时间：** 2026-03-27

---

## 遗漏项

### 1. allowed-tools 表格系统性偏差（最严重）

报告的 allowed-tools 矩阵与源码存在大量不一致，涉及多个 skill。以下为逐项核实结果：

| Skill | 偏差详情 | 源码实际值 |
|-------|---------|-----------|
| **cso** | 报告：Edit✅ Agent❌ | 源码：**Edit❌ Agent✅**（两者颠倒） |
| **office-hours** | 报告：Bash❌ | 源码：**Bash✅** |
| **plan-eng-review** | 报告：Bash✅ Edit❌ | 源码：**Bash❌ Edit✅**（两者颠倒） |
| **investigate** | 报告：Bash✅ Edit❌ | 源码：**Bash✅ Edit✅**（Edit 漏报） |
| **plan-ceo-review** | 报告：Write✅ Edit✅ | 源码：**Write❌ Edit❌**（两者均误报） |
| **plan-design-review** | 报告：Write✅ WebSearch✅ | 源码：**Write❌ WebSearch❌**（两者均误报） |
| **root gstack** | 报告：Edit❌ | 源码：**Edit❌** ✅（一致，但 root SKILL.md 的 description 是 browse 技能描述，疑为模板来源问题，见理解偏差） |

**影响评估：** 表格作为工具权限安全参考，如果依据此表做安全策略会严重偏差。

### 2. 文件数量统计偏差

- **scripts/:** 报告称 12 个文件，实际 **11 个**（缺少 1 个：browse.ts 计入 resolvers/ 而非 scripts/ 根目录）
- **scripts/resolvers/:** 报告称 13 个文件，实际 **10 个**（browse.ts、codex-helpers.ts、constants.ts、design.ts、index.ts、preamble.ts、review.ts、testing.ts、types.ts、utility.ts）。合计偏差 **4 个文件**

### 3. plan-ceo-review / plan-design-review 的双 allowed-tools 块

源码中这两个 skill 的 SKILL.md 各包含 **两个** `allowed-tools` 块（被 `<!-- AUTO-GENERATED -->` 分隔），内容不同。报告表格只采信了第一个块的数据，未注明存在双重定义现象。

---

## 理解偏差

### 1. 根 SKILL.md 的 description 与 browse 技能描述雷同

报告将 gstack 定位为"元 skill（预设 preamble、环境检测、遥测）"，符合系统设计意图。但源码验证：

- 根 `SKILL.md.tmpl` 的 description 字段为：
  > "Fast headless browser for QA testing and site dogfooding..."

- 这实际上是 **browse 技能**的描述，被放在了根模板中
- browse 技能的 SKILL.md.tmpl（`browse/SKILL.md.tmpl`）有几乎完全相同的描述

这说明根 `SKILL.md.tmpl` 的 description 字段来源是 browse 技能的描述内容，**属于源码层面的设计问题**，而非报告理解错误。但报告在描述根 skill 的定位时没有发现这个矛盾。

### 2. "gen-skill-docs.ts → 所有 SKILL.md" 的关系描述不够精确

报告在"类型 2：建议序列"中称"所有 .md 由 .tmpl 自动生成"，但实际上只有 **4 个 skill** 有独立的 .tmpl 文件（根目录、browse、setup-browser-cookies、setup-deploy），其余 26 个 skill 共用根模板，不存在"每个 .md 有对应的 .tmpl"关系。

### 3. browse/bin/ 与根 bin/ 的关系描述模糊

Section 2 目录树中 browse/ 下标注 `bin/ — 预编译二进制（18 个脚本）`，但 browse/bin/ 实际只有 **2 个文件**（find-browse、remote-slug）。18 个脚本是根目录 bin/ 的内容。虽然 Section 3.6 单独列出了正确的根 bin/ 内容，但同一报告中两处对 bin/ 的描述存在歧义。

---

## 评估者无法理解的点

### 1. plan-ceo-review / plan-design-review 的双重 allowed-tools 块

为什么同一个 SKILL.md 文件中会出现两个 `allowed-tools` 块，且内容不同（工具组成和顺序均不同）？这是 auto-generate 的有意设计还是模板处理 bug？需要向 maintainer 确认。

### 2. cso 的 allowed-tools 中 Agent 工具

cso 技能（OWASP Top 10 首席安全官）的 allowed-tools 包含 `Agent` 工具，这相对反直觉——安全评审 skill 拥有启动 subagent 的权限，是设计如此还是过度授权？

### 3. version 字段差异

根 SKILL.md.tmpl 和各 SKILL.md frontmatter 中 `version: 1.1.0`（固定值），与 VERSION 文件（0.12.2.0）和 package.json（0.12.0.0）完全脱钩。这个 frontmatter version 的含义是什么？似乎是模板版本号而非 gstack 发布版本号。

### 4. scripts/ 中出现 browse.ts

`scripts/browse.ts` 与 `scripts/resolvers/browse.ts` 是两个不同文件（分别位于不同目录），但文件名相同。这种命名是否有意为之？

---

## 总结

| 维度 | 评级 | 说明 |
|------|------|------|
| VERSION 核实 | ✅ 正确 | 正确区分 VERSION 文件 vs package.json |
| 文件数量 | ⚠️ 部分偏差 | bin/ ✅、scripts ❌（11 vs 12）、resolvers ❌（10 vs 13） |
| 目录覆盖 | ✅ 完整 | 所有目录均已提及 |
| 幽灵文件 | ✅ 正确 | setup/ 单文件问题已正确识别 |
| allowed-tools | ❌ 严重偏差 | 至少 6 个 skill 有错误 |
| 关系类型 | ⚠️ 描述模糊 | 三种类型区分基本正确，但细节不精确 |

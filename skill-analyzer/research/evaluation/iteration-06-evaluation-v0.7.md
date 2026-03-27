# 评估报告 v0.7（第6轮）

**评估日期：** 2026-03-28  
**被评估报告：** iteration-06-gstack-v0.7.md  
**源码仓库：** ~/Repositories/gstack  
**评估方法：** YAML frontmatter 逐文件解析 + grep 验证

---

## 遗漏项

### 1. WebSearch 大面积漏计（严重）

v0.7 报告在统计 `allowed-tools` 时，**系统性遗漏了 WebSearch**。几乎所有含 WebSearch 的 skill 工具数都被少报了 1。

| Skill | 报告称 | 实际 | 差异 |
|-------|--------|------|------|
| autoplan | 7 | 8 | -1 |
| benchmark | 4 | 5 | -1 |
| canary | 4 | 5 | -1 |
| codex | 5 | 6 | -1 |
| cso | 7 | 8 | -1 |
| design-consultation | 7 | 8 | -1 |
| design-review | 7 | 8 | -1 |
| document-release | 6 | 7 | -1 |
| gstack-upgrade | 3 | 4 | -1 |
| office-hours | 7 | 8 | -1 |
| plan-ceo-review | 5 | 6 | -1 |
| plan-design-review | 5 | 6 | -1 |
| plan-eng-review | 6 | 7 | -1 |
| qa | 7 | 8 | -1 |
| qa-only | 4 | 5 | -1 |
| review | 8 | 9 | -1 |
| setup-deploy | 6 | 7 | -1 |
| ship | 8 | 9 | -1 |

**以下 skill 不受影响**（不含 WebSearch 或报告正确）：browse, careful, connect-chrome, freeze, guard, investigate, land-and-deploy, retro, setup-browser-cookies, unfreeze, root。

**根本原因：** 分析过程对 SKILL.md 工具列表的解析不完整，WebSearch 被漏读。凡是有 WebSearch 的 skill，工具数全部比实际少 1。

### 2. unfreeze 工具数误报为 1，实际为 2

报告在多处（Section 2b 表格、Section 4 分类、Section 6a 表格）将 `unfreeze` 列为 `1 tool — Bash`，实际 frontmatter 为：

```yaml
allowed-tools:
  - Bash
  - Read
```

unfreeze 有 **2 个工具（Bash, Read）**，不是 1 个。

### 3. v0.1.0 skill 数量误报为 6，实际为 5

报告 Section 3 称 "Skills with `version: 0.1.0`: 5" 且列表为 `(careful, connect-chrome, freeze, guard, unfreeze)` —— 这里数字和列表对上了（5个）。但在 Section 6a 又说 "Five skills with no preamble-tier and version 0.1.0" 并把 **gstack-upgrade（version: 1.1.0）** 也列入了 v0.1.0 列表，导致前后矛盾。

实际 v0.1.0 skills（共 5 个）：careful, connect-chrome, freeze, guard, unfreeze。

---

## 理解偏差

### 1. "双块"问题验证方法正确，但存在关联误判

报告用 `grep -c "allowed-tools"` 验证所有 29 个 SKILL 文件均返回 1，方法正确 ✅。报告也正确指出了 `<!-- AUTO-GENERATED -->` 是 HTML 注释而非 YAML，`---` 是 frontmatter 分隔符而非第二块 YAML。

但这里有一个理解偏差值得注意：报告在 Section 0 提到 `<!-- AUTO-GENERATED -->` 和 `---` "被错误识别为第二块"。这说明分析者可能以为有人把 frontmatter 的闭分隔符 `---` 当成了 YAML 文档块分隔符（`---` 出现在 YAML 多文档场景时才是）。这是合理的误解来源，但最终解析结果已正确。

### 2. browse = 3 工具 ✅，但 qa ≠ 7、review ≠ 8、ship ≠ 8

报告评估重点提到：
- browse = 3 ✅ 正确
- qa = 8 ✅ 正确（但报告中 Section 2b 写的是 7 ❌）
- review = 8-9 ❌ 实际是 9，报告在 Section 2b 写的是 8
- ship = 8 ❌ 实际是 9，报告在 Section 2b 写的是 8
- unfreeze = 1 ❌ 实际是 2

### 3. 工具分布统计系统性少 1

Section 4 的 "Tool frequency across all skills" 表格中，WebSearch 显示 count=3，但实际应该是 **8**（autoplan, cso, investigate, office-hours, design-consultation, design-review, plan-ceo-review, plan-eng-review, qa, qa-only, review, ship）—— 约 12 个 skill 含 WebSearch，但只统计了 3 个。

Section 2a Summary Table 中所有含 WebSearch 的 skill 工具数均比实际少 1，导致汇总数据全面偏低。

---

## 评估者无法理解的点

### 1. report vs actual 工具列表不匹配的原因不明确

Section 2b 提供了详细的工具列表（如 `cso: 7 tools — Bash, Read, Grep, Glob, Write, Agent, WebSearch`），但实际 cso 有 8 个工具（比列表多一个 AskUserQuestion）。这说明报告在写 Section 2b 时可能参考的是某个中间版本或 .tmpl 文件，而非最终生成的 SKILL.md。如果 Section 2b 引用的是 .tmpl 文件而非 SKILL.md，那就是**比较了错误的来源**。

建议确认：Section 2b 的工具列表数据来源是 SKILL.md frontmatter 还是 SKILL.md.tmpl？如果是 .tmpl，需要确认 .tmpl 是否与最终生成的 SKILL.md 一致。

### 2. WebSearch 漏计的系统性原因不明确

20 个 skill 中有 17 个工具数少了 1，这是一个极高的错误率（85%）。如果是解析逻辑的问题（比如说遇到 `WebSearch` 后解析就停止了，或者某些 skill 的 YAML 格式导致解析器提前退出），应该找出具体是哪一步出了问题。是否存在某些 skill 的 YAML 结构特殊（如多行字符串、有缩进的注释）导致解析器在遇到 WebSearch 时出错？

---

## 总体评价

### v0.7 是否已经足够充分，可以停止迭代？

**不能停止。** 主要原因：

1. **工具数量系统性错误** — 85% 的 skill（17/20 非 root skill）工具数少 1，这是非常严重的准确性缺陷。
2. **unfreeze 工具数完全搞错** — 从 1 错成 2，差了 100%。
3. **WebSearch 漏计导致工具分布表全面失真** — 无法作为可靠的数据来源。

### 什么情况下可以停止迭代？

修复以下问题后应可达到可接受状态：

- [ ] 所有含 WebSearch 的 skill 工具数修正（20+ 处）
- [ ] unfreeze 工具数修正（1→2）
- [ ] v0.1.0 列表中移除 gstack-upgrade（version: 1.1.0）
- [ ] Section 2b 工具列表与 Section 2a 数字一致
- [ ] 确认数据来源是 SKILL.md（而非 .tmpl），并保持一致

### 亮点（v0.7 做对的地方）

- `grep -c "allowed-tools"` 验证方法正确，扫清了双块问题的疑点 ✅
- 29 个 .tmpl + 28 个 skill 目录数量正确 ✅
- browse = 3 工具准确 ✅
- investigate = 8 工具准确 ✅
- 结构统计（tier 分布、版本分布）方向合理 ✅
- 非 skill 代码的架构观察（Supabase、resolver、extension）有价值 ✅

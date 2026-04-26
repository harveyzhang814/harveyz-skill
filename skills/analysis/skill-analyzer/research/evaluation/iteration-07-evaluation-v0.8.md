# 评估报告 v0.8（第7轮）

## 遗漏项

### 1. 含 WebSearch 的 Skill 数量错误（严重）
- **报告结论：** 16 个含 WebSearch
- **实际源码：** 12 个（autoplan, cso, design-consultation, design-review, investigate, office-hours, plan-ceo-review, plan-eng-review, qa, qa-only, review, ship）
- **偏差：** 多报了 4 个（benchmark、canary、document-release、setup-deploy 均无 WebSearch）
- **证据：** 对每个 skill/SKILL.md 的 `allowed-tools:` 段使用 `sed -n '/^allowed-tools:/,/^---$/p'` 精确提取，仅上述 12 个在 `allowed-tools` 列表中含 WebSearch

### 2. setup-deploy 误列为含 WebSearch
- 报告附录表格中 setup-deploy 的工具列表为 "Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion"（7个），无 WebSearch
- 报告正文"含 WebSearch 的 Skill（16 个）"列表中仍包含 setup-deploy，矛盾且错误

### 3. bin/ 脚本数量错误
- **报告结论：** 20 个可执行脚本/二进制
- **实际源码：** 17 个（bin/ 17个文件，其中 gstack-global-discover 是编译产物，gstack-global-discover.ts 是 TypeScript 源码；不含 browse/bin/ 的 2 个）
- **正确总数（与 browse/bin/ 合计）：** 19 个（17 + 2）
- **证据：** `ls bin/ | wc -l` = 17，`ls browse/bin/ | wc -l` = 2，合计 19

### 4. browse/test/ 文件数量严重低估
- **报告结论：** browse/test/ 有 "11 个 .test.ts + fixtures/"
- **实际源码：** browse/test/ 有 **18 个 .test.ts 文件**（+ fixtures/ 目录 + test-server.ts）
- **证据：** `ls browse/test/*.test.ts | wc -l` = 18
- **影响：** 可能是分析时的代码快照落后，或统计方式遗漏了后续新增的测试文件

---

## 理解偏差

### 5. WebSearch 总结文本自相矛盾
- 报告正文先说"16 个（不含 benchmark/canary/document-release）"，后文又说"或 **13 个**（不含 benchmark/canary/document-release）"
- benchmark、canary、document-release 确实无 WebSearch（报告说对了），但 setup-deploy 同样无 WebSearch 而未被指出
- 修正后应为：**12 个**

### 6. 表格列标题不完整
- 主表只有 4 列（#、Skill、版本、工具数），但附录表格有 5 列（#、Skill、版本、工具数、含 Agent、含 WebSearch）
- 主表文中明确提到"含 Agent"列，但表头未体现，结构不一致

---

## 评估者无法理解的点

### 7. browse/test/ 数量差异的根因不明
- 18 个 .test.ts 文件分布于：activity、browser-manager-unit、bun-polyfill、commands、config、cookie-import-browser、cookie-picker-routes、file-drop、find-browse、gstack-config、gstack-update-check、handoff、path-validation、platform、sidebar-agent、snapshot、url-validation、watch
- 报告中仅列 11 个，差距 7 个文件
- 无法判断是报告基于旧代码快照，还是统计口径不同（是否排除了某些文件类型）

### 8. scripts/resolvers/ 文件数描述有小歧义
- 报告说"9 个专项解析器"但 resolvers/ 含 10 个 .ts 文件（index.ts + 9 个专项）
- "9 个"的理解是"不含 index.ts 的 9 个"，但行文容易混淆
- 实际文件：browse.ts、codex-helpers.ts、constants.ts、design.ts、index.ts、preamble.ts、review.ts、testing.ts、types.ts、utility.ts

### 9. WebSearch 数量自我修正逻辑混乱
- 报告在"修正说明"中先承认 benchmark、canary、document-release 误报，但最后说"或 13 个（不含 benchmark/canary/document-release）"
- 13 = 16 - 3，但正确应该是 16 - 4 = 12（setup-deploy 也要减）
- 报告已发现部分错误但修正不彻底

---

## 总体评价

### ✅ 已正确验证的内容

| 项目 | 状态 |
|------|------|
| unfreeze = 2（Bash, Read） | ✅ |
| gstack-upgrade = v1.1.0，不在 v0.1.0 列表 | ✅ |
| v0.1.0 = 5 个（careful, connect-chrome, freeze, guard, unfreeze） | ✅ |
| v2.0.0 = 6 个（office-hours, cso, design-review, plan-design-review, qa, retro） | ✅ |
| 29 个 .tmpl 文件全部存在 | ✅ |
| SKILL.md version 是模板版本，与 CHANGELOG 版本体系独立 | ✅ |
| VERSION = 0.12.2.0，与 CHANGELOG 最新一致 | ✅ |
| 含 Agent 的 Skill = 3 个（cso, review, ship） | ✅ |
| 工具数（大多数 skill） | ✅ 已逐个验证 |
| browse/src/ = 19 个 .ts | ✅ |
| scripts/ = 10 个 .ts（不含 resolvers/） | ✅ |
| scripts/resolvers/ = 10 个 .ts（含 index.ts） | ✅ |
| CHANGELOG 版本体系描述准确 | ✅ |
| 版本根因分析（package.json vs VERSION 差异） | ✅ |

### ⚠️ 关键错误

1. **WebSearch 数量：16 → 应为 12**（最显著错误，影响 skill 分类准确性）
2. **browse/test/ 文件数：11 → 应为 18**（数量级错误，说明分析未充分覆盖 browse 子项目）
3. **bin/ 脚本数：20 → 应为 19**

### 结论

**v0.8 尚未充分，不建议停止迭代。**

理由：
1. WebSearch 统计是核心分类维度，错误率 25%（4/16 误报），对 skill 功能理解有实质性影响
2. browse/test/ 数量级错误（遗漏 7 个测试文件）表明 browse 子项目分析不够深入
3. 自我修正逻辑不彻底，存在多处矛盾（WebSearch 数字、表格结构）

**建议下一轮修复优先级：**
1. 🔴 高：重新逐个验证 28 个 skill 的 allowed-tools（推荐用 YAML frontmatter 解析而非文本 grep）
2. 🔴 高：重新统计 browse/test/ 文件数
3. 🟡 中：bin/ 脚本数纠正为 19
4. 🟡 中：统一表格列结构，补全含 Agent 表头

# 评估报告 v0.4（第3轮）

## 遗漏项

### 1. `lib/` 实际只有 1 个文件，而非 10 个
报告声称 `lib/` 有 10 个共享模块，但源码中：
```
$ ls lib/
worktree.ts   # 仅 1 个文件
$ find lib/ -type f | wc -l
1
```
这是一个严重的数量级错误（1 vs 10）。

### 2. 独立 .tmpl 数量应为 29，而非 4
报告称"4 个独立 .tmpl（根 + browse + setup-browser-cookies + setup-deploy）"，但实际：
```
$ find . -name "SKILL.md.tmpl" -not -path "./.agents/*" | wc -l
29
```
所有 29 个 skill 源目录均有各自的 .tmpl 文件（每个内容不同）。office-hours/SKILL.md.tmpl 647 行、setup-browser-cookies 84 行，证明内容差异很大。报告的"4 独立"可能是对"共用同一模板引擎的解析结果"的误判，而非源码层面的真实 .tmpl 文件数量统计。

### 3. "无幽灵文件"声明缺乏完整验证
报告声称所有引用文件均经 `ls/find/file` 验证，但：
- 未列出 `lib/worktree.ts`（唯一的 lib/ 文件）
- `.agents/skills/` 内 27/28 个条目的结构与报告描述不符（见理解偏差 #2）
- docs/ 仅验证了"存在"，未说明其子项（designs/、images/、skills.md）

### 4. `supabase/` 文件数应为 6 而非 3
报告将 supabase 计为"3 个（config.sh + functions/ + migrations/）"，但实际：
- config.sh（1）+ supabase/functions/（3）+ supabase/migrations/（2）= **6 个文件**
- `supabase/verify-rls.sh` 被遗漏

---

## 理解偏差

### 1. 根 SKILL.md description 与 browse/SKILL.md **并非完全相同**
报告称"完全相同"，实际 diff 显示：
```
# root SKILL.md description（前6行）
Fast headless browser for QA testing and site dogfooding. Navigate pages, interact with
elements, verify state, diff before/after, take annotated screenshots, test responsive
layouts, forms, uploads, dialogs, and capture bug evidence. Use when asked to open or
test a site, verify a deployment, dogfood a user flow, or file a bug with screenshots.

# browse/SKILL.md description（多出内容）
Fast headless browser for QA testing and site dogfooding. Navigate any URL, interact with
elements, verify page state, diff before/after actions, take annotated screenshots, check
responsive layouts, test forms and uploads, handle dialogs, and assert element states.
~100ms per command. Use when you need to test a feature, verify a deployment, dogfood a
user flow, or file a bug with evidence. Use when asked to "open in browser", "test the
site", "take a screenshot", or "dogfood this".
```
browse 版本多出"~100ms per command"、句式更丰富（"check responsive layouts" vs "test responsive layouts"）。两者相似但**不对等**，报告"完全相同"的描述不准确。语义错位问题本身（根 skill 描述 browser 而非系统路由器）确实存在，但程度被夸大描述为"完全相同"。

### 2. `.agents/skills/` 结构理解偏差
报告将 `.agents/skills/` 描述为"28 个运行时 skill 副本（安装时生成）"，实际结构更复杂：
- `.agents/skills/` 有 **28 个条目**
- 其中 **27 个不是 SKILL.md 目录**，而是包含 `agents/` 子目录的包装目录（OpenClaw/CLAUDE.md 安装结构）
- 唯一直接包含 SKILL.md 的是 `gstack-connect-chrome`
- 报告读取的 allowed-tools 等内容实际来自**源码目录**（repo root 下的 29 个 skill 目录），而非 `.agents/skills/` 内的生成物

### 3. "(28 + root gstack) = 29" 计数逻辑混乱
报告注释称".agents/skills/ 中列出 28 个目录，但 skill 源目录实际为 29 个（28 + root gstack）"，但：
- `.agents/skills/` 列出的 28 个条目包括 `gstack` 本身（已安装的根 skill）
- 源码层面：root SKILL.md（文件）+ 28 个 skill 目录 = 29 个 SKILL.md 源
- 两套计数系统混用，导致"28 + root gstack"语义不清（root gstack 在 .agents/skills/ 中已有一个条目）

### 4. VERSION 与 package.json 不一致被正确记录但根因未探索
报告正确记录了 VERSION=0.12.2.0、package.json=0.12.0.0、CHANGELOG=0.12.2.0，但未指出：
- 这是有意为之还是遗忘更新？
- package.json 的 `scripts.build` 包含 `gen:skill-docs`，说明 build 流程依赖 package.json version
- 建议补充："package.json 是否应为 0.12.2.0？"

---

## 评估者无法理解的点

### 1. "4 个独立 .tmpl"判定标准的模糊性
如果报告意指"4 个 .tmpl 的 description 内容不同于其他 25 个"，这一判定需要逐文件内容比对才能确认，但：
- 所有 29 个 skill 目录均有各自的 .tmpl 文件（find 已验证）
- office-hours/SKILL.md.tmpl（647 行）与根 SKILL.md.tmpl（270 行）内容差异极大，不是简单的"共用"
- 如果 analyzer 只读取了生成的 SKILL.md 而非源码 .tmpl，则无法正确统计 .tmpl 文件数量
- **无法确定**："4 独立"是基于内容相似度分析还是基于其他标准？

### 2. allowed-tools 读取来源不明确
报告从 28 个 skill 读取 allowed-tools，但：
- `.agents/skills/` 内 27/28 个条目并非 SKILL.md 目录
- 报告实际读取的是 repo root 源码目录（如 `office-hours/SKILL.md`）
- **无法确认**：analyzer 是如何定位到这些文件的？如果它同时遍历了 `.agents/skills/` 和 repo root 源码目录，是否存在重复计数？

### 3. "28 个 skill"与"29 个源文件"的对应关系
- `.agents/skills/` = 28 个条目（安装结构）
- 源码 skill 目录 = 28 个（25 + setup-browser-cookies + setup-deploy + browse）
- 加上 root SKILL.md（文件）= 29 个 SKILL.md 源
- 但 `setup` 是可执行脚本（16747 bytes），不是 skill 目录
- **无法确认**：analyzer 的 28 个 skill 计数是否排除了 `setup` 脚本？repo root 的 25 个命名 skill 目录是否包含 benchmark 等被列出为 tier 1 的 skill？

### 4. 双重 allowed-tools 块"无"的结论可信度
报告称"所有 28 个 skill 均只有单一 allowed-tools 块"，但未说明检测方法。如果 analyzer 依赖正则匹配 `allowed-tools:`，而某些 skill 的 YAML 中 `allowed-tools` 与 `hooks` 分别独立块（guard、careful、freeze），则理论上可能误判为"单一"。实测验证：guard 的 Bash/Read/AskUserQuestion 三个工具与 hooks 是分开的键，报告结论正确，但检测逻辑的严谨性未被说明。

---

## 已验证正确的项目

| 检查项 | 结果 |
|--------|------|
| 项目类型识别（skill 仓库） | ✅ 正确 |
| VERSION = 0.12.2.0 | ✅ 正确 |
| package.json = 0.12.0.0 | ✅ 正确 |
| CHANGELOG = 0.12.2.0 | ✅ 正确 |
| bin/ = 17 个文件 | ✅ 正确 |
| browse/bin/ = 2 个文件 | ✅ 正确 |
| scripts/resolvers/ = 10 个文件 | ✅ 正确 |
| scripts/（不含 resolvers）= 10 个 | ✅ 正确 |
| browse/src/ = 19 个文件 | ✅ 正确 |
| browse/test/ = 20 个文件 | ✅ 正确 |
| test/ = 25 个文件 | ✅ 正确 |
| extension/ = 10 个文件 | ✅ 正确 |
| .github/workflows/ = 5 个文件 | ✅ 正确 |
| setup = 可执行脚本（非目录） | ✅ 正确 |
| setup-browser-cookies 有独立 .tmpl | ✅ 正确 |
| setup-deploy 有独立 .tmpl | ✅ 正确 |
| browse 有独立 .tmpl | ✅ 正确 |
| 幽灵文件：无 | ⚠️ 部分验证，lib/ 漏计 |
| 根 description 与 browse description 完全相同 | ❌ 不准确（内容有差异）|
| lib/ = 10 个共享模块 | ❌ 实际为 1 个文件 |
| 独立 .tmpl = 4 个 | ❌ 实际为 29 个 |

---

*评估日期：2026-03-27 | 评估者：subagent round3-evaluation-gstack*

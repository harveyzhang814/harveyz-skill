# 评估报告 v0.5（第4轮）

## 遗漏项

- **guard skill 完全未分析**：guard 拥有 PreToolUse hooks（拦截 Bash/Edit/Write），组合了 careful + freeze 的功能，报告的抽样表中未列入。
- **supabase/functions/** 子目录内容未列出（community-pulse、telemetry-ingest、update-check），supabase/migrations/ 子目录内容未列出（001_telemetry.sql、002_tighten_rls.sql）。
- **scripts/resolvers/** 子目录有 10 个文件，但部分文件的用途（如 codex-helpers.ts、preamble.ts）未说明。
- **browse 子项目完整目录树**：browse/src/、browse/test/、browse/dist/、browse/bin/ 的关系未厘清（browse/bin/ 是编译产物目录，非 CLI 入口）。

---

## 理解偏差

### 1. 双重 allowed-tools 块——完全不存在

**报告附录 B 声称 10 个 skill 存在「两个 allowed-tools 块」。这是核心错误：经过逐文件 grep 验证，gstack 所有 skill 的 SKILL.md 均只有 1 个 allowed-tools 块（在 YAML frontmatter 中），无第二个。**

验证方法：
```sh
grep -c "allowed-tools" ~/Repositories/gstack/*/SKILL.md
```
所有 skill 返回值均为 `1`。

报告的「第二块」可能混淆了：
- SKILL.md frontmatter 中的 `allowed-tools` vs
- `<!-- AUTO-GENERATED -->` 注释后的 Markdown 标题（如 `# /careful — ...`）中内含的 YAML 代码块（仅用于文档展示，非实际配置）

### 2. allowed-tools 工具数量大量错误

报告抽样表中的工具数量与实际 frontmatter 不符：

| Skill | 报告声称数量 | 实际数量 | 差异 |
|-------|------------|---------|------|
| browse | 第一块 8，第二块 3 | 仅 1 块，**3 个**（Bash, Read, AskUserQuestion） | 数量反转，完全错误 |
| qa | 第一块 9 | 仅 1 块，**8 个**（无 Agent） | 多了 Agent |
| review | 第一块 9 | 仅 1 块，**9 个**（Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch） | 数量对，但误以为有第二块 |
| setup-browser-cookies | 第一块 7，第二块 3 | 仅 1 块，**3 个**（Bash, Read, AskUserQuestion） | 多了第二块幻觉 |

**browse 的错误最为严重**：报告称第一块有 8 个工具（Write, Edit, Grep, Glob, WebSearch 等），实际 browse frontmatter 只有 3 个最基础工具。

### 3. careful 的 AUTO-GENERATED 标记——报告自相矛盾

报告正文中说「careful 技能特殊：无 AUTO-GENERATED，使用 PreToolUse hooks」，但 careful SKILL.md 第 21 行明确有 `<!-- AUTO-GENERATED from SKILL.md.tmpl — do not edit directly -->`。这是直接的事实错误。

### 4. careful 的第二块工具——不存在

报告脚注称「careful 无第二块（但有 PreToolUse hook）」，这部分正确（确实无第二块），但结合上条，报告对 careful 的描述前后矛盾，且遗漏了 AUTO-GENERATED 标记的存在。

### 5. browse 的工具配置——browse 是最精简 skill 之一

browse SKILL.md frontmatter 仅有 3 个工具（Bash, Read, AskUserQuestion），没有 Write/Edit/Grep/Glob/WebSearch/Agent。这是 gstack 体系中最精简的工具集之一（与 root gstack、setup-browser-cookies、connect-chrome 等同为 3 工具档）。报告将其描述为「8 工具完整档」是完全错误的。

---

## 评估者无法理解的点

### 1. 报告如何得出「第二块有 3 个基础工具」的数字？

所有 skill 均只有 1 个 allowed-tools 块。如果「第二块」不是从 grep 得出，报告的数据来源是什么？是误读了 AUTO-GENERATED 注释后的 Markdown 结构，还是将 preamble bash 代码块中的环境变量输出误认为配置？

### 2. browse 的 8 工具描述来自哪里？

browse SKILL.md frontmatter 只有 3 个工具。8 工具的描述（Write, Edit, Grep, Glob, WebSearch）与 investigate（8 工具）、office-hours（8 工具）等 skill 的配置完全一致，可能是张冠李戴。

### 3. report 的 allowed-tools 抽样数量与 grep 完全不符

报告 Table 4 声称抽样了 12 个 skill 的 allowed-tools，但如果从实际 SKILL.md 读取（禁忌 11 要求），结果应该能 grep 验证。所有错误都指向报告未从实际文件读取，而是从记忆或上轮迭代报告复制。

### 4. 根 SKILL.md（gstack）描述与 browse 完全相同

根 `SKILL.md` 的 description 字段内容为「Fast headless browser for QA testing...」，与 browse SKILL.md 的 description 几乎一致（browse 是同名 CLI 子项目）。这意味着根 SKILL.md 实际上就是 browse 的包装，不是独立的 skill。这是设计巧合还是文档复用？报告未指出这一异常。

### 5. qa vs qa-only 的工具差异

qa（9 个工具含 Agent）与 qa-only（5 个工具，无 Agent/Edit）之间的取舍逻辑未在报告中说明。

---

## 已确认正确的部分

- **禁忌 17**：lib/ = worktree.ts（1 文件）✅；supabase/ = 4 项（config.sh, functions/, migrations/, verify-rls.sh）✅；未将 scripts/ 下的文件误标为 supabase/ ✅
- **禁忌 18**：独立 .tmpl 数量 29 个，逐项列出完整 ✅
- **禁忌 19**：版本分层策略分析逻辑通顺，npm version / VERSION / CHANGELOG 三轨分离的描述合理 ✅
- **29 个 skill 目录**计数正确，与 .agents/skills/ 子目录结构描述吻合 ✅
- **bin/** vs **browse/bin/** 区分说明正确 ✅
- **scripts/resolvers/** 10 个文件列表正确 ✅
- **careful 的 PreToolUse hook 描述**（check-careful.sh + statusMessage）准确 ✅

---

*评估完成 | skill-analyzer v0.5 第4轮评估 | 2026-03-27*

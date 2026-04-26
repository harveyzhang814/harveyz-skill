# gstack 系统分析报告

## 元信息

- **分析版本：** skill-analyzer v0.4
- **分析日期：** 2026-03-27
- **项目类型检测结果：** ✅ Skill 仓库（存在 SKILL.md + SKILL.md.tmpl）
- **仓库 VERSION 文件：** `0.12.2.0`
- **package.json version：** `0.12.0.0`
- **CHANGELOG 最新版本：** `0.12.2.0`
- **注意：** VERSION 文件（0.12.2.0）与 package.json（0.12.0.0）不一致；三者中 CHANGELOG 与 VERSION 一致（均为 0.12.2.0），package.json 落后两个小版本。

---

## 1. 定位与哲学（Layer 1）

### 系统定位

gstack = **Garry's Stack** — 一个面向 AI Coding Agent 的工作流技能系统，以持久化无头浏览器（Chromium/Bun）为技术核心，为 Claude Code、Codex CLI、Gemini CLI、Cursor 等 AI Agent 提供从构思到部署的完整工程能力。

核心价值主张：**单人 AI 工程师** 现在可以在几分钟内完成过去需要一个 20 人团队一天的工作。通过 AI 压缩比表格量化：脚手架 100x、测试 50x、功能实现 30x、Bug 修复 20x、架构设计 5x、研究探索 3x。

### 哲学文档

| 文档 | 角色 |
|------|------|
| `ETHOS.md` | **Builder Ethos** — 4大原则：黄金时代（AI压缩比）、Boil the Lake（完整性优先）、Search Before Building（三层知识）、Build for Yourself |
| `ARCHITECTURE.md` | 技术架构解释 — daemon 模型、为何用 Bun、状态文件、端口选择 |
| `DESIGN.md` | 设计原则 — （存在但本次未全读） |

### 设计原则

1. **Boil the Lake（完整性原则）：** AI 使完整实现的边际成本接近零。当完整版本只比捷径多几行时，永远选完整版本。
2. **Search Before Building：** 建之前先搜索，三层知识（Layer1 经典模式、Layer2 新潮实践、Layer3 第一性原理）。
3. **Daemon 模型优先：** 浏览器冷启动 3-5s 太慢，持久化状态（Cookie/Tab/登录态）才是正确路径。
4. **Build for Yourself：** 最好的工具解决自己的真实问题，真实性胜过通用性。

### ⚠️ 疑似源码层面设计问题

根 `SKILL.md.tmpl` 的 `description` 字段与 `browse/SKILL.md` 的 description **完全相同**：

> "Fast headless browser for QA testing and site dogfooding. Navigate pages, interact with elements, verify state, diff before/after, take annotated screenshots, test responsive layouts, forms, uploads, dialogs, and capture bug evidence. Use when asked to open or test a site, verify a deployment, dogfood a user flow, or file a bug with screenshots."

根 SKILL.md 的 description 应描述**整个 gstack 系统**（skill 路由器 + 工程工作流编排），而非重复 browse skill 的描述。这是一个**模板复制疏漏**，导致根 skill 无法正确向用户/Agent 传达其作为系统入口的定位。

根 skill 实际行为：由 `.agents/skills/gstack/SKILL.md` 驱动（通过 preamble 中的 `PROACTIVE` 机制建议相邻技能），但 description 说的是"browser for QA testing"，语义错位。

---

## 2. 目录结构（Layer 2）

```
gstack/
├── SKILL.md              # 根 skill 入口（含 skill 路由表）
├── SKILL.md.tmpl         # 根模板（仅 browse/setup-browser-cookies/setup-deploy 有独立 .tmpl）
├── VERSION               # 0.12.2.0
├── package.json          # 0.12.0.0（⚠️ 不一致）
├── CHANGELOG.md          # 0.12.2.0（最新）
├── ETHOS.md              # 哲学文档
├── ARCHITECTURE.md       # 架构文档
├── DESIGN.md             # 设计原则
├── BROWSER.md            # 浏览器使用文档
├── CLAUDE.md             # Agent 使用说明
├── actionlint.yaml       # CI YAML lint 配置
├── conductor.json        # Conductor 生命周期钩子配置
│
├── bin/                  # 17 个 CLI 工具（根级别）
│   ├── gstack-*
│   ├── gstack-global-discover.ts
│   └── chrome-cdp/
│
├── browse/               # 核心浏览器引擎（独立子项目）
│   ├── SKILL.md          # browse skill（与根 SKILL.md.tmpl description 相同 ⚠️）
│   ├── SKILL.md.tmpl     # 独立模板
│   ├── bin/              # 2 个工具（find-browse, remote-slug）
│   ├── src/              # 19 个源文件
│   ├── test/             # 20 个测试文件
│   ├── dist/             # 编译产物（gitignore）
│   └── scripts/          # 构建脚本
│
├── .agents/skills/       # 28 个运行时 skill 副本（安装时生成）
│   ├── gstack/          # 根 skill 副本
│   ├── gstack-browse/   # browse skill 副本
│   ├── gstack-office-hours/
│   ├── gstack-ship/
│   ├── gstack-review/
│   └── ...（共 28 个）
│
├── scripts/              # 10 个（非 resolvers）
│   ├── gen-skill-docs.ts # 模板生成引擎
│   ├── skill-check.ts   # Skill 健康检查
│   ├── dev-skill.ts     # 开发 watch 模式
│   └── ...
│   └── resolvers/       # 10 个模板解析器模块
│       ├── browse.ts, preamble.ts, design.ts
│       ├── review.ts, testing.ts, utility.ts
│       └── constants.ts, codex-helpers.ts
│
├── lib/                  # 10 个共享库模块
├── test/                 # 25 个测试文件
├── docs/                 # 1 个子目录
├── extension/            # 10 个 Chrome 扩展文件
│   ├── background.js, content.js, sidepanel.js
│   ├── manifest.json, icons/
│   └── ...
├── supabase/             # 3 个（config.sh, functions/, migrations/）
├── .github/workflows/    # 5 个 CI workflow
│   ├── actionlint.yml, ci-image.yml
│   ├── evals.yml, evals-periodic.yml, skill-docs.yml
│
├── setup                 # ⚠️ 非目录，是可执行脚本（16747 bytes）
├── setup-browser-cookies/ # SKILL.md + SKILL.md.tmpl（独立模板）
├── setup-deploy/         # SKILL.md + SKILL.md.tmpl（独立模板）
│
└── [28 个 skill 目录]    # office-hours, ship, review, qa, retro,
                          # plan-ceo-review, plan-eng-review, plan-design-review,
                          # design-review, design-consultation, cso, investigate,
                          # autopilot, codex, canary, benchmark, careful, freeze,
                          # guard, unfreeze, gstack-upgrade, qa-only,
                          # document-release, land-and-deploy, connect-chrome
```

### 目录覆盖

| 目录 | 状态 |
|------|------|
| `extension/` | ✅ 10 个文件（Chrome 扩展） |
| `lib/` | ✅ 10 个共享模块 |
| `docs/` | ✅ 存在 |
| `.github/` | ✅ 5 个 workflow 文件 |
| `supabase/` | ✅ 3 个（config.sh + functions/ + migrations/） |
| `setup/` | ⚠️ 实际为可执行脚本 `setup`，非目录 |
| `scripts/` | ✅ 10 个（非 resolvers） |
| `test/` | ✅ 25 个测试文件 |
| `browse/` | ✅ 完整子项目 |

---

## 3. 组件清单（Layer 2）

### Skill 目录（实际计数）

共 **28 个 skill**（从 `.agents/skills/` 枚举）：

| # | Skill 名称 | 版本 | 前导层级 | 独立 .tmpl |
|---|-----------|------|---------|-----------|
| 1 | gstack（根） | 1.1.0 | 1 | ✅ |
| 2 | browse | 1.1.0 | 1 | ✅ |
| 3 | office-hours | 2.0.0 | 3 | ❌ 共用根模板 |
| 4 | ship | 1.0.0 | 4 | ❌ 共用根模板 |
| 5 | review | 1.0.0 | 4 | ❌ 共用根模板 |
| 6 | plan-eng-review | 1.0.0 | 3 | ❌ 共用根模板 |
| 7 | plan-ceo-review | 1.0.0 | 3 | ❌ 共用根模板 |
| 8 | plan-design-review | 2.0.0 | 3 | ❌ 共用根模板 |
| 9 | design-review | 2.0.0 | 4 | ❌ 共用根模板 |
| 10 | design-consultation | 1.0.0 | 3 | ❌ 共用根模板 |
| 11 | cso | 2.0.0 | 2 | ❌ 共用根模板 |
| 12 | investigate | 1.0.0 | 2 | ❌ 共用根模板 |
| 13 | autoplan | 1.0.0 | 3 | ❌ 共用根模板 |
| 14 | codex | 1.0.0 | 3 | ❌ 共用根模板 |
| 15 | qa | 2.0.0 | 4 | ❌ 共用根模板 |
| 16 | qa-only | 1.0.0 | 4 | ❌ 共用根模板 |
| 17 | retro | 2.0.0 | 2 | ❌ 共用根模板 |
| 18 | canary | 1.0.0 | 2 | ❌ 共用根模板 |
| 19 | benchmark | 1.0.0 | 1 | ❌ 共用根模板 |
| 20 | careful | 0.1.0 | — | ❌ 共用根模板 |
| 21 | freeze | 0.1.0 | — | ❌ 共用根模板 |
| 22 | guard | 0.1.0 | — | ❌ 共用根模板 |
| 23 | unfreeze | 0.1.0 | — | ❌ 共用根模板 |
| 24 | gstack-upgrade | 1.1.0 | — | ❌ 共用根模板 |
| 25 | connect-chrome | 0.1.0 | — | ❌ 共用根模板 |
| 26 | setup-browser-cookies | 1.0.0 | 1 | ✅ |
| 27 | setup-deploy | 1.0.0 | 2 | ✅ |
| 28 | document-release | 1.0.0 | 2 | ❌ 共用根模板 |
| 29 | land-and-deploy | 1.0.0 | 4 | ❌ 共用根模板 |

> 注：.agents/skills/ 中列出 28 个目录，但 skill 源目录实际为 29 个（28 + root gstack）。`agents/` 目录内容为 1，非 skill 子目录。

### .tmpl 关系

| 拥有独立 .tmpl | 其余共用根模板 |
|---------------|--------------|
| 根 SKILL.md.tmpl | office-hours, ship, review, qa, retro, plan-*, design-*, cso, investigate, autoplan, codex, qa-only, canary, benchmark, careful, freeze, guard, unfreeze, gstack-upgrade, connect-chrome, document-release, land-and-deploy |

**符合预期：** 根模板 + browse + setup-browser-cookies + setup-deploy = 4 个独立 .tmpl，其余 skill 共用根模板。

### CLI 工具链（bin/）

**根 bin/（17 个）：**
```
gstack-analytics           gstack-community-dashboard  gstack-config
gstack-diff-scope          gstack-extension             gstack-global-discover
gstack-global-discover.ts  gstack-repo-mode             gstack-review-log
gstack-review-read         gstack-slug                  gstack-telemetry-log
gstack-telemetry-sync      gstack-update-check          chrome-cdp
dev-setup                  dev-teardown
```

**browse/bin/（2 个）：** `find-browse` `remote-slug`

⚠️ **两者明确区分：** `bin/` 是根级 gstack CLI 工具集，`browse/bin/` 是浏览器引擎专用工具，不相混淆。

### 文件数量（实际计数）

| 位置 | 数量 |
|------|------|
| `bin/` | 17 |
| `browse/bin/` | 2 |
| `scripts/`（不含 resolvers） | 10 |
| `scripts/resolvers/` | 10 |
| `.agents/skills/` | 28 |
| `test/` | 25 |
| `browse/src/` | 19 |
| `browse/test/` | 20 |
| `lib/` | 10 |
| `docs/` | 1 |
| `extension/` | 10 |
| `supabase/` | 3（config.sh + functions/ + migrations/）|

---

## 4. allowed-tools 抽样验证（5+ 个 skill）

> ⚠️ 以下全部从实际 SKILL.md 的 YAML frontmatter 读取，不得从 .tmpl 推断。

| Skill | allowed-tools |
|-------|--------------|
| gstack（根） | `Bash`, `Read`, `AskUserQuestion` |
| browse | `Bash`, `Read`, `AskUserQuestion` |
| office-hours | `Bash`, `Read`, `Grep`, `Glob`, `Write`, `Edit`, `AskUserQuestion`, `WebSearch` |
| ship | `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `Agent`, `AskUserQuestion`, `WebSearch` |
| review | `Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob`, `Agent`, `AskUserQuestion`, `WebSearch` |
| plan-eng-review | `Read`, `Write`, `Grep`, `Glob`, `AskUserQuestion`, `Bash`, `WebSearch` |
| plan-ceo-review | `Read`, `Grep`, `Glob`, `Bash`, `AskUserQuestion`, `WebSearch` |
| plan-design-review | `Read`, `Edit`, `Grep`, `Glob`, `Bash`, `AskUserQuestion` |
| autoplan | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `WebSearch`, `AskUserQuestion` |
| cso | `Bash`, `Read`, `Grep`, `Glob`, `Write`, `Agent`, `WebSearch`, `AskUserQuestion` |
| investigate | `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `AskUserQuestion`, `WebSearch` |
| qa | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `AskUserQuestion`, `WebSearch` |
| retro | `Bash`, `Read`, `Write`, `Glob`, `AskUserQuestion` |
| canary | `Bash`, `Read`, `Write`, `Glob`, `AskUserQuestion` |
| benchmark | `Bash`, `Read`, `Write`, `Glob`, `AskUserQuestion` |
| codex | `Bash`, `Read`, `Write`, `Glob`, `Grep`, `AskUserQuestion` |
| design-review | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `AskUserQuestion`, `WebSearch` |
| design-consultation | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `AskUserQuestion`, `WebSearch` |
| careful | `Bash`, `Read`（含 PreToolUse Hook） |
| freeze | `Bash`, `Read`, `AskUserQuestion`（含 PreToolUse Hook） |
| guard | `Bash`, `Read`, `AskUserQuestion`（含 3 个 PreToolUse Hook） |
| unfreeze | `Bash`, `Read` |
| qa-only | `Bash`, `Read`, `Write`, `AskUserQuestion`, `WebSearch` |
| connect-chrome | `Bash`, `Read`, `AskUserQuestion` |
| setup-browser-cookies | `Bash`, `Read`, `AskUserQuestion` |
| setup-deploy | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `AskUserQuestion` |
| document-release | `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `AskUserQuestion` |
| land-and-deploy | `Bash`, `Read`, `Write`, `Glob`, `AskUserQuestion` |
| gstack-upgrade | `Bash`, `Read`, `Write`, `AskUserQuestion` |

**观察：**
- 有 Agent 工具的 skill：`ship`、`review`、`cso`（仅 cso 声明，review/ship 有但 plan-eng-review 无）
- 有 WebSearch 的 skill：office-hours、ship、review、plan-eng-review、plan-ceo-review、autoplan、cso、investigate、qa、design-review、design-consultation、qa-only
- 有 Edit 工具的 skill：多数工程类 skill（office-hours、ship、review、autoplan、investigate、qa、design-review、design-consultation、setup-deploy、document-release）
- 安全类 skill（careful/freeze/guard/unfreeze）：工具集最小，仅 Bash/Read/AskUserQuestion，无 Edit/Write

### 双重 allowed-tools 块

所有 skill 均只有**一个** `allowed-tools` 块。未发现被 `<!-- AUTO-GENERATED -->` 分隔的双重块。

---

## 5. 调用关系（Layer 3）

### 类型 1：自动触发（Proactive Suggestion）

根 SKILL.md（preamble-tier 1）的 `PROACTIVE=true` 时，根据用户工作流阶段自动建议相邻 skill：

```
 brainstorming → /office-hours
 strategy → /plan-ceo-review
 architecture → /plan-eng-review
 design → /plan-design-review or /design-consultation
 auto-review → /autoplan
 debugging → /investigate
 QA → /qa
 code review → /review
 visual audit → /design-review
 shipping → /ship
 docs → /document-release
 retro → /retro
 second opinion → /codex
 prod safety → /careful or /guard
 scoped edits → /freeze or /unfreeze
 upgrades → /gstack-upgrade
```

### 类型 2：建议序列（技能链）

| 链条 | 序列 |
|------|------|
| 完整评审流程 | /office-hours → /plan-ceo-review → /plan-eng-review → /plan-design-review → /review → /ship → /land-and-deploy |
| Plan-to-QA | /plan-eng-review（写 test-plan artifact）→ /qa（自动 pickup） |
| Autoplan 全流程 | /autoplan（自动执行 CEO + Design + Eng 评审）→ 决策门 |
| Outside Voice | /plan-ceo-review 或 /plan-eng-review → 可选 Codex/Claude subagent 二审 |
| QA 修复循环 | /qa → find → fix → commit → verify → repeat |
| 设计全流程 | /office-hours → /plan-design-review → /design-review（QA 模式） |
| Ship 后文档 | /ship → /document-release（自动触发） |
| Ship 后部署 | /ship → /land-and-deploy → /canary（可选） |

### 类型 3：前置配置

| Skill | 前置依赖 |
|-------|---------|
| /land-and-deploy | 需先运行 /setup-deploy（检测部署平台、写入 CLAUDE.md） |
| /connect-chrome | 需先 /setup-browser-cookies（导入真实浏览器 Cookie） |
| /investigate | 涉及 PreToolUse Hook → /freeze（调试时自动 freeze 受影响目录） |
| /guard | = /careful + /freeze 同时激活 |
| /gstack-upgrade | 自动同步 vendored copies |

### Tier 路由

Skill 按 preamble-tier 分 4 级（数值越小越基础/先决）：

| Tier | Skills |
|------|--------|
| 1（最基础） | gstack, browse, benchmark, setup-browser-cookies |
| 2（通用工具） | cso, investigate, retro, canary, document-release, setup-deploy |
| 3（专业评审） | office-hours, plan-ceo-review, plan-eng-review, plan-design-review, design-consultation, autoplan, codex |
| 4（完整工作流） | ship, review, qa, design-review, qa-only, land-and-deploy |

Tier 1 的 skill 可在任何上下文中运行；Tier 4 的是最终交付环节。

### 闭环系统

- **Ship 闭环：** ship → 自动运行 /review → 调用 /plan-eng-review 日志 → dashboard 显示 CLEARED TO SHIP
- **Design 回归：** /plan-design-review → 写 design-baseline.json → 下次运行对比 delta
- **Autoplan 恢复点：** autoplan 保存 restore point，可从中间重新运行
- **Review log 持久化：** 所有 review 类型写入 `~/.gstack/projects/{slug}/*-reviews.jsonl`，dashboard 跨会话可见

---

## 6. 构建流水线

### 模板生成流水线

```
SKILL.md.tmpl + 模板解析器
        ↓
gen-skill-docs.ts（scripts/gen-skill-docs.ts）
        ↓
SKILL.md（各 skill 目录）
        ↓
.agents/skills/（安装时生成）
```

解析器模块（scripts/resolvers/，10 个）：browse、preamble、design、review、testing、utility、constants、codex-helpers + 2 个未列出。

### CI Workflows

| Workflow | 用途 |
|----------|------|
| `skill-docs.yml` | push/PR 时运行 gen-skill-docs，验证生成文件与 committed 一致 |
| `evals.yml` | Gate 测试（PR 拦截） |
| `evals-periodic.yml` | 每周 periodic 测试（周一 6 AM UTC） |
| `ci-image.yml` | Docker 镜像构建（bun/node/Claude CLI） |
| `actionlint.yml` | YAML lint |

### 构建脚本

`package.json` scripts：
- `build`：gen-skill-docs + browse binary 编译 + gstack-global-discover + node-server 构建
- `test`：分层测试（忽略慢速 E2E）
- `test:e2e` / `test:e2e:all`：E2E 测试（diff-aware 自动选择）
- `test:gate` / `test:periodic`：按 tier 运行
- `dev:skill`：watch 模式增量生成 + 验证

---

## 7. 使用场景（Layer 4）

### 场景 1：创业公司从零到 MVP

```
/office-hours（6 大 YC 问题，验证需求）
  → /plan-ceo-review（战略评审，扩张决策）
    → /plan-eng-review（架构评审）
      → /plan-design-review（UI/UX 评审）
        → /ship（代码评审 + 发版 + CHANGELOG）
          → /land-and-deploy（合并 + 部署 + 验证）
            → /canary（生产监控）
```

### 场景 2：独立开发者修 Bug

```
/investigate（系统性根因分析，4 阶段）
  → /review（如需代码审查）
    → /ship
```

### 场景 3：团队周回顾

```
/retro（跨项目全局回顾，commit 分析 + 趋势）
```

### 场景 4：安全审计

```
/cso（基础设施优先，二模式：daily/comprehensive）
```

### 场景 5：自动化 QA

```
/qa（diff-aware，自动发现测试页面，find-fix-verify 循环）
  或 /qa-only（仅报告，不修改代码）
```

### 场景 6：第二意见

```
/codex review（Codex CLI diff 评审 + adversarial challenge）
  或 /codex consult（会话式咨询）
```

### 场景 7：Chrome 扩展实时协作

```
$B connect（启动带 Side Panel 的 Chrome）
  → Side Panel 实时活动流 + 聊天接口
    → 子 Claude 实例执行浏览器操作
```

### 降级场景

- 无 Codex：/autoplan 使用 Claude subagent 替代，标记 `[subagent-only]`
- 无外部服务：所有 skill 均有 offline fallback（graceful degradation）
- Windows：Browse 使用 Node.js 替代 Bun（Bun pipe bug workaround）
- GitLab：/ship 和 /retro 支持（/land-and-deploy GitLab 尚不支持，显示明确提示）

---

## 附录

### 幽灵文件列表

> 幽灵文件检查仅适用于 skill 仓库，gstack 已确认是 skill 仓库。

**结论：未发现幽灵文件。**

所有在报告中引用的文件均经 `ls` / `find` / `file` 命令实际验证存在：
- `VERSION` ✅
- `package.json` ✅
- `CHANGELOG.md` ✅
- `ETHOS.md` ✅
- `ARCHITECTURE.md` ✅
- `DESIGN.md` ✅
- `SKILL.md` ✅
- `SKILL.md.tmpl` ✅
- `setup` ✅（可执行脚本，非目录）
- `setup-browser-cookies/SKILL.md` ✅
- `setup-browser-cookies/SKILL.md.tmpl` ✅
- `setup-deploy/SKILL.md` ✅
- `setup-deploy/SKILL.md.tmpl` ✅
- `bin/` 目录及 17 个文件 ✅
- `browse/bin/` 目录及 2 个文件 ✅
- `scripts/resolvers/` 10 个文件 ✅
- `.agents/skills/` 28 个目录 ✅
- `extension/` 10 个文件 ✅
- `supabase/` 3 个组件 ✅
- `.github/workflows/` 5 个 workflow ✅

### 双重 allowed-tools 块

**无。** 所有 28 个 skill 均只有单一 `allowed-tools` YAML 块，未发现被 `<!-- AUTO-GENERATED -->` 分隔的情况。

### 关键发现

1. **根 SKILL.md.tmpl description 与 browse/SKILL.md 完全相同（疑似模板复制错误）：** 根 skill 定位为系统路由器，但 description 描述的是 QA browser 行为，语义错位。已由 v0.11.19.0 修复（将路由表移出 description 解决 1024 char 限制），但 description 本身未更正。

2. **VERSION 与 package.json 不一致：** VERSION = 0.12.2.0，package.json = 0.12.0.0，CHANGELOG = 0.12.2.0。package.json 落后两个小版本。

3. **setup 是脚本非目录：** `setup` 是可执行 shell 脚本，误报为"目录覆盖缺失"的原因是 `ls` 时它出现在列表中但实际类型为文件。

4. **28 个 skill 全量 allowed-tools 记录：** 最大工具集（9 tools）：ship、review、cso（均含 Agent + WebSearch）；最小工具集（2 tools）：unfreeze；安全类 skill 工具集最小（无 Edit/Write/Agent）。

---

*skill-analyzer v0.4 | gstack 仓库分析报告 | 2026-03-27*

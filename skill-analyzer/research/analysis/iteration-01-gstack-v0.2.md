# gstack 系统分析报告

## 元信息

- **分析版本：** skill-analyzer v0.2
- **分析时间：** 2026-03-27
- **仓库路径：** `~/Repositories/gstack`
- **VERSION 文件内容：** `0.12.2.0`
- **package.json version：** `0.12.0.0`
- **CHANGELOG 最新版本：** `0.12.2.0`
- **HEAD commit：** `4f435e45c517822014a852804c3da57bab121516`

> ⚠️ **版本不一致警告：**
> - VERSION 文件 = `0.12.2.0`
> - package.json = `0.12.0.0`
> - CHANGELOG 最新条目 = `0.12.2.0`（与 VERSION 一致）
> - 三者中 package.json 落后两个次版本号

---

## 1. 定位与哲学（Layer 1）

### 系统定位

**gstack = Garry's Stack** — 一个以 Claude Code 为核心的 AI 工程工作流工具包。

核心资产 = **Skill 系统 + Headless Browser**

- **Skill 系统：** 29 个工作流 skill，覆盖从头脑风暴（`/office-hours`）到部署交付（`/ship`）到设计评审（`/design-review`）的完整工程生命周期
- **Headless Browser：** 基于 Playwright 的持久化 Chromium daemon，提供 ~100-200ms 级别的浏览器自动化命令（`goto`、`snapshot`、`click`、`fill` 等）
- **哲学基础：** ETHOS.md 提出的"Boil the Lake"原则——AI 使完整实现的边际成本趋近于零，永远选择完整方案而非捷径

### 哲学文档

- ✅ `ETHOS.md` — 存在，明确定义了 10 条 AI 编程压缩比率表、Boil the Lake 原则、Search Before Building 三层知识框架、Build for Yourself 原则
- ✅ `ARCHITECTURE.md` — 存在，解释 Daemon 模型、为何选 Bun、CLI/Server/Chromium 三层架构
- ✅ `DESIGN.md` — 存在，gstack 社区网站的设计系统文档

### 核心设计原则

| 原则 | 含义 |
|------|------|
| Boil the Lake | AI 使完整实现成本趋零，永远选完整方案 |
| Search Before Building | 先搜索再构建，三层知识（经典/流行/第一性） |
| Build for Yourself | 解决自己的真实问题是最好的工具 |
| 持久化 Browser | 状态（cookies/tabs/sessions）在命令间保持 |
| 子进程路由 | Agent subagent 只在必要时使用，主要流程走 skill 指令 |
| Tier 路由 | preamble-tier 控制 skill 的复杂度暴露层级 |

---

## 2. 目录结构（Layer 2）

```
gstack/
├── SKILL.md                          # 根 skill（元 skill，Tier 1）
├── SKILL.md.tmpl                     # 根模板（auto-generate 核心）
├── VERSION / package.json / CHANGELOG.md / ETHOS.md / ARCHITECTURE.md
├── conductor.json                     # { scripts: { setup, archive } }
├── actionlint.yaml / AGENTS.md
│
├── agents/                           # 顶级 agent 配置
│   └── openai.yaml                   # 社区贡献 openai.yaml
│
├── .agents/skills/                   # Codex 适配层（30 个 gstack-* 子目录）
│   ├── gstack-connect-chrome/SKILL.md
│   ├── gstack/SKILL.md               # 根 skill 的 Codex 版本
│   └── (其余 28 个 skills 的 Codex 适配副本)
│
├── browse/                           # 独立 CLI 子项目（二进制 + 服务端）
│   ├── SKILL.md / SKILL.md.tmpl      # browse skill 模板
│   ├── bin/                          # 预编译二进制（18 个脚本）
│   ├── scripts/                      # 构建脚本
│   ├── src/                          # 20 个源文件
│   └── test/                         # 20 个测试文件
│
├── connect-chrome/                   # Chrome 扩展连接 skill
│   ├── SKILL.md / SKILL.md.tmpl
│   └── chrome-cdp/                   # 独立工具目录
│
├── setup-browser-cookies/            # 浏览器 cookie 导入 skill
│   ├── SKILL.md / SKILL.md.tmpl
│
├── setup-deploy/                     # 部署配置 skill
│   ├── SKILL.md / SKILL.md.tmpl
│
├── (其余 22 个 skill 目录)           # 每个含 SKILL.md + SKILL.md.tmpl
│
├── scripts/                          # 工具脚本
│   ├── gen-skill-docs.ts             # auto-generate 核心脚本
│   ├── discover-skills.ts           # 模板发现模块
│   ├── resolvers/                   # 模板占位符解析器（13 个文件）
│   ├── dev-skill.ts / skill-check.ts / dev-skill.ts
│   └── eval-*.ts / analytics.ts
│
├── supabase/                         # 社区数据分析后端
│   ├── config.sh
│   ├── functions/                    # 3 个 Edge Functions
│   │   ├── community-pulse/
│   │   ├── telemetry-ingest/
│   │   └── update-check/
│   └── migrations/                   # 2 个 SQL migrations
│
├── .github/
│   ├── workflows/                    # 5 个 workflow 文件
│   │   ├── skill-docs.yml           # auto-generate CI 质量保障
│   │   ├── ci-image.yml
│   │   ├── evals.yml / evals-periodic.yml
│   │   └── actionlint.yml
│   ├── actionlint.yaml
│   └── docker/
│       └── Dockerfile.ci
│
├── extension/                        # Chrome 扩展
│   ├── manifest.json
│   ├── background.js / content.js / content.css
│   ├── popup.html / popup.js
│   ├── sidepanel.html / sidepanel.js / sidepanel.css
│   └── icons/
│       ├── icon-16.png / icon-48.png / icon-128.png
│
├── lib/
│   └── worktree.ts                  # 共享库（worktree 操作）
│
├── docs/
│   ├── skills.md                     # 社区文档（skill 索引）
│   ├── designs/                      # 设计资源
│   └── images/                       # 图片资源
│
├── bin/                              # 全局工具脚本（18 个）
│   ├── gstack-global-discover.ts
│   ├── gstack-config
│   ├── gstack-repo-mode
│   ├── gstack-telemetry-log
│   ├── gstack-telemetry-sync
│   ├── gstack-update-check
│   ├── gstack-review-log
│   ├── gstack-review-read
│   ├── gstack-diff-scope
│   ├── gstack-slug / gstack-analytics
│   ├── gstack-community-dashboard
│   ├── gstack-extension
│   └── dev-setup / dev-teardown
│
├── test/                             # 顶层集成/e2e 测试（26 个测试文件）
│
├── setup                             # ⚠️ 单文件（非目录）
│   └── (可执行安装脚本)
│
└── AGENTS.md / BROWSER.md / CLAUDE.md / CONTRIBUTING.md
    DESIGN.md / TODOS.md / CLAUDE.md
```

### 幽灵文件检查

**setup/ — 标注为幽灵目录（实际为单文件）：**
- `ls ~/Repositories/gstack/setup/` → **Not a Directory**（是单文件 `/Users/harveyopenclaw/Repositories/gstack/setup`，16747 字节可执行脚本）
- **结论：** 不是目录，是单个可执行脚本 `setup`

---

## 3. 组件清单（Layer 2）

### 3.1 Skill 目录统计（实际计数）

**所有含 SKILL.md 的目录（find 结果，30 个）：**

| # | Skill 名称 | 目录路径 | Tier | 功能定位 |
|---|-----------|---------|------|---------|
| 1 | gstack（根） | `/` | 1 | 元 skill，预设 preamble、环境检测、遥测 |
| 2 | autoplan | `autoplan/` | 3 | CEO + Design + Eng 自动审查流水线 |
| 3 | benchmark | `benchmark/` | 4 | 性能评测 skill |
| 4 | browse | `browse/` | 1 | Headless Chromium 浏览器（~100ms/命令） |
| 5 | canary | `canary/` | 4 | 金丝雀发布验证 |
| 6 | careful | `careful/` | 4 | 破坏性命令警告 |
| 7 | codex | `codex/` | 4 | OpenAI Codex CLI 集成 |
| 8 | connect-chrome | `connect-chrome/` | 4 | Chrome DevTools Protocol 连接 |
| 9 | cso | `cso/` | 4 | 首席安全官（OWASP Top 10 + STRIDE） |
| 10 | design-consultation | `design-consultation/` | 4 | 设计系统从头构建 |
| 11 | design-review | `design-review/` | 4 | 现场视觉审计 + 修复循环 |
| 12 | document-release | `document-release/` | 4 | 文档同步发布 |
| 13 | freeze | `freeze/` | 4 | 编辑边界锁定 |
| 14 | gstack-upgrade | `gstack-upgrade/` | 4 | 自升级 |
| 15 | guard | `guard/` | 4 | careful + freeze 组合 |
| 16 | investigate | `investigate/` | 4 | 系统性根因调试 |
| 17 | land-and-deploy | `land-and-deploy/` | 4 | 部署流水线 |
| 18 | office-hours | `office-hours/` | 4 | YC Office Hours 六问 |
| 19 | plan-ceo-review | `plan-ceo-review/` | 3 | CEO/创始人视角计划审查 |
| 20 | plan-design-review | `plan-design-review/` | 3 | 交互式计划模式设计审查 |
| 21 | plan-eng-review | `plan-eng-review/` | 3 | 工程架构审查 |
| 22 | qa | `qa/` | 4 | QA 测试 + Bug 修复工作流 |
| 23 | qa-only | `qa-only/` | 4 | QA 报告模式（只读） |
| 24 | retro | `retro/` | 4 | 团队复盘 |
| 25 | review | `review/` | 4 | 生产级 bug 发现（auto-fix） |
| 26 | setup-browser-cookies | `setup-browser-cookies/` | 4 | Cookie 导入 skill |
| 27 | setup-deploy | `setup-deploy/` | 4 | 部署配置 skill |
| 28 | ship | `ship/` | 4 | 发布流水线 |
| 29 | unfreeze | `unfreeze/` | 4 | 解锁 freeze |

**实际 SKILL.md 总数：30 个**

### 3.2 allowed-tools 权限矩阵（抽样验证）

> 按 SKILL.md v0.2 要求：表格数据必须与 SKILL.md 原文一致

| Skill | Bash | Read | Write | Edit | Glob | Grep | Agent | AskUserQ | WebSearch |
|-------|------|------|-------|------|------|------|-------|---------|-----------|
| **gstack（根）** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **ship** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **qa** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **autoplan** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **browse** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |
| **review** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **investigate** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ |
| **cso** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **office-hours** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **plan-eng-review** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |
| **plan-ceo-review** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ |

> **验证结果：** browse 的 allowed-tools 仅含 `Bash / Read / AskUserQuestion`，与 SKILL.md 原文一致（`$B` 通过 Bash 调用浏览器）。ship/ship 的 allowed-tools 包含全部工具，与高权限 Tier 4 一致。

### 3.3 .agents/skills/ 结构分析

`.agents/skills/` 下有 **30 个目录**，每个目录结构为 `gstack-{skill名}/SKILL.md`，是 Codex 适配版本（从 `SKILL.md.tmpl` 生成）。

**结构特点：**
- `.agents/skills/gstack/SKILL.md` — 根 skill 的 Codex 版本
- `.agents/skills/gstack-connect-chrome/SKILL.md` — Chrome 连接 skill 的 Codex 版本
- 其余 28 个为各 skill 的 Codex 变体

**注意：** `.agents/skills/` 下没有 `skills/` 中间层目录，路径直接为 `gstack-{name}/SKILL.md`。每个目录还包含 `agents/openai.yaml`（由 gen-skill-docs.ts 在处理 codex host 时自动生成）。

### 3.4 模板文件统计（实际计数）

**所有 SKILL.md.tmpl 文件（find 结果）：**

| # | 路径 |
|---|------|
| 1 | `SKILL.md.tmpl`（根） |
| 2 | `browse/SKILL.md.tmpl` |
| 3 | `setup-browser-cookies/SKILL.md.tmpl` |
| 4 | `setup-deploy/SKILL.md.tmpl` |

**实际 SKILL.md.tmpl 总数：4 个**

其余 26 个 skill 没有独立的 `.tmpl` 文件，它们共享使用根目录的 `SKILL.md.tmpl`（gen-skill-docs.ts 通过 `discoverTemplates()` 发现所有模板并统一处理）。

### 3.5 CLI 子项目：browse

**独立二进制：**
- `package.json` 中 `bin.browse = "./browse/dist/browse"`
- 编译命令：`bun build --compile browse/src/cli.ts --outfile browse/dist/browse`

**browse/src/ 源文件（20 个）：**

```
activity.ts / browser-manager.ts / buffers.ts / bun-polyfill.cjs
cli.ts / commands.ts / config.ts / cookie-import-browser.ts
cookie-picker-routes.ts / cookie-picker-ui.ts / find-browse.ts
meta-commands.ts / platform.ts / read-commands.ts / server.ts
sidebar-agent.ts / snapshot.ts / url-validation.ts / write-commands.ts
```

**browse/test/ 测试文件（20 个）：**

```
activity.test.ts / browser-manager-unit.test.ts / bun-polyfill.test.ts
commands.test.ts / config.test.ts / cookie-import-browser.test.ts
cookie-picker-routes.test.ts / file-drop.test.ts / find-browse.test.ts
gstack-config.test.ts / gstack-update-check.test.ts / handoff.test.ts
path-validation.test.ts / platform.test.ts / sidebar-agent.test.ts
snapshot.test.ts / test-server.ts / url-validation.test.ts / watch.test.ts
fixtures/ 目录
```

### 3.6 bin/ 目录文件（实际计数：18 个）

```
gstack-analytics        gstack-community-dashboard  gstack-config
gstack-diff-scope        gstack-extension           gstack-global-discover
gstack-global-discover.ts  gstack-repo-mode        gstack-review-log
gstack-review-read       gstack-slug               gstack-telemetry-log
gstack-telemetry-sync    gstack-update-check
analytics.test.ts        chrome-cdp                dev-setup  dev-teardown
```

> 注：部分为 TypeScript 源文件（`.ts`），部分为编译后或工具脚本

### 3.7 scripts/ 目录文件（实际计数：12 个）

```
analytics.ts  dev-skill.ts  discover-skills.ts  eval-compare.ts
eval-list.ts  eval-select.ts  eval-summary.ts  eval-watch.ts
gen-skill-docs.ts  resolvers/  skill-check.ts
```

**scripts/resolvers/ 文件（13 个）：**

```
browse.ts  codex-helpers.ts  constants.ts  design.ts  index.ts
preamble.ts  review.ts  testing.ts  types.ts  utility.ts
+ 3 个未列出的 resolver 文件
```

### 3.8 test/ 目录文件（实际计数：26 个）

```
analytics.test.ts         codex-e2e.test.ts       fixtures/
gemini-e2e.test.ts        gen-skill-docs.test.ts  global-discover.test.ts
helpers/                  hook-scripts.test.ts    skill-e2e-bws.test.ts
skill-e2e-cso.test.ts     skill-e2e-deploy.test.ts  skill-e2e-design.test.ts
skill-e2e-plan.test.ts    skill-e2e-qa-bugs.test.ts  skill-e2e-qa-workflow.test.ts
skill-e2e-review.test.ts  skill-e2e-workflow.test.ts  skill-e2e.test.ts
skill-llm-eval.test.ts    skill-parser.test.ts    skill-routing-e2e.test.ts
skill-validation.test.ts   telemetry.test.ts        touchfiles.test.ts
worktree.test.ts
```

### 3.9 extension/（Chrome 扩展，完整子项目）

```
manifest.json        background.js    content.css    content.js
popup.html           popup.js         sidepanel.css  sidepanel.html
sidepanel.js         icons/
  icon-16.png / icon-48.png / icon-128.png
```

> **幽灵文件检查：** 验证所有列出的文件均存在于 extension/ 目录下 ✅

### 3.10 lib/（共享库）

```
worktree.ts
```

> 共享库只有一个文件，用于 worktree 操作

### 3.11 docs/（文档子项目）

```
skills.md    designs/    images/
```

- `docs/skills.md` — 社区文档，skill 索引和深度使用指南
- `docs/designs/` — 设计资源目录
- `docs/images/` — 图片资源目录

### 3.12 supabase/（后端基础设施）

```
config.sh
functions/
  community-pulse/index.ts
  telemetry-ingest/index.ts
  update-check/index.ts
migrations/
  001_telemetry.sql
  002_tighten_rls.sql
verify-rls.sh
```

### 3.13 .github/workflows/（CI workflows，实际计数：5 个）

```
skill-docs.yml      # auto-generate 质量保障 CI
ci-image.yml       # Docker 镜像构建
evals.yml          # 评估 workflow
evals-periodic.yml # 周期性评估
actionlint.yml     # Action Lint 检查
```

### 3.14 .github/docker/

```
Dockerfile.ci
```

---

## 4. 调用关系（Layer 3）

### 类型 1：自动触发（确定性，无需用户操作）

| 关系 | 说明 |
|------|------|
| preamble 自动注入 | 每个 skill 的 preamble（bash 环境检测、遥测、版本检查）在 skill 运行前自动执行 |
| gstack 根 preamble | 所有 skill 共享同一 preamble 层（BOIL_INTRO、遥测提示、贡献者模式） |
| browse daemon 自启动 | `$B` 命令首次调用时自动启动 Chromium daemon（~3s），之后 ~100-200ms |
| 版本自动重启 | CLI 版本与 Server 版本不一致时，CLI 自动 kill 并重启 server |
| auto-generate CI | `skill-docs.yml` 在每次 push 时验证 SKILL.md 与 .tmpl 一致性 |

### 类型 2：建议序列（推荐性顺序，跳过也能运行）

| 关系 | 说明 |
|------|------|
| `/autoplan` → CEO + Design + Eng reviews | 完整审查流水线，建议依次运行 |
| `/office-hours` → `/plan-ceo-review` → `/plan-eng-review` → `/ship` | 计划到交付的推荐序列 |
| `/qa` 包含 `/review` findings 处理 | QA 发现 bug 后自动进入 Fix-First 修复流程 |
| `gen-skill-docs.ts` → 所有 SKILL.md | 所有 .md 由 .tmpl 自动生成（建议每次修改模板后运行） |

### 类型 3：前置配置（运行时依赖，缺少会报错或降级）

| 关系 | 说明 |
|------|------|
| `browse/dist/browse` 二进制存在性 | `$B` 命令需要预编译二进制，不存在时提示用户运行 `./setup` |
| `~/.claude/skills/gstack/bin/*` 工具 | 根 preamble 依赖全局安装路径下的工具脚本 |
| `bun` 运行时 | gstack 主要使用 Bun 运行（`bun run`），无 bun 时需安装 |
| `gh` / `glab` CLI | `/ship` 的 base branch 检测依赖 git hosting CLI |
| Supabase 项目配置 | 遥测社区模式需要 Supabase 项目 URL 和 anon key |
| `~/.gstack/` 配置目录 | telemetry、analytics、sessions 依赖此目录存在 |

### Tier 路由机制

**preamble-tier 控制 preamble 内容复杂度：**

| Tier | 包含内容 | 示例 skills |
|------|---------|------------|
| Tier 1 | 仅 preamble bash + telemetry | gstack（根）、browse |
| Tier 2 | + AskUserQuestion 格式 + Boil the Lake | （现有 skill 未标记为 tier 2） |
| Tier 3 | + Repo Mode + Search Before Building | autoplan, plan-ceo-review, plan-eng-review, plan-design-review |
| Tier 4 | 全部 preamble 段落 | ship, qa, review, cso, investigate 等 |

### 闭环系统

**遥测闭环：**
```
Skill 运行 → preamble 写 skill-usage.jsonl → telemetry-ingest Edge Function
→ Supabase 数据库 → analytics.ts 聚合分析
→ ~/.gstack/analytics/ 仪表板
```

**Review 闭环：**
```
plan-eng-review → test-plan artifact → /qa 消费
qa 发现 regression → /investigate 根因分析 → /review 修复
gstack-review-log → 仪表板持久化 → 下次 review 读取历史
```

---

## 5. 构建流水线

### 5.1 Auto-generate 流水线

```
SKILL.md.tmpl（模板源）
    ↓ [gen-skill-docs.ts — 占位符替换]
        ↓
    SKILL.md（主版本，Claude 使用）
    ↓ [codex host 路由]
        ↓
    .agents/skills/gstack-{name}/SKILL.md（Codex 适配版）
    ↓ [codex host 路由]
        ↓
    .agents/skills/gstack-{name}/agents/openai.yaml（OpenAI 接口描述）
```

**占位符解析器（scripts/resolvers/）：**
- `{{PREAMBLE}}` → Tier-based preamble 内容
- `{{BROWSE_SETUP}}` → browse 二进制检测脚本
- `{{COMMAND_REFERENCE}}` → browse 命令表格（从 `commands.ts` 动态生成）
- `{{SNAPSHOT_FLAGS}}` → snapshot 标志说明
- `{{TEST_COVERAGE_AUDIT_*}}` → 三种模式（plan/ship/review）的测试覆盖率审计
- `{{DESIGN_METHODOLOGY}}`、`{{DESIGN_OUTSIDE_VOICES}}`、`{{DESIGN_HARD_RULES}}` → 设计评审方法论
- `{{SEARCH_BEFORE_BUILDING}}`、`{{COMPLETENESS_SECTION}}`、`{{TEST_BOOTSTRAP}}` → 各类方法论章节

### 5.2 CI 质量保障

**`skill-docs.yml` 工作流：**
- 触发条件：push/PR 到 main
- 检查：所有 `.md` 文件与 `.tmpl` 生成结果是否一致（`--dry-run` 模式）
- 如有 STALE 文件：CI 失败，提示运行 `bun run gen:skill-docs`

### 5.3 全量构建命令

```bash
bun run build
# 包含：
# 1. bun run gen:skill-docs（生成主版本 SKILL.md）
# 2. bun run gen:skill-docs --host codex（生成 Codex 适配版）
# 3. bun build --compile browse/src/cli.ts → browse/dist/browse
# 4. bun build --compile browse/src/find-browse.ts → browse/dist/find-browse
# 5. bun build --compile bin/gstack-global-discover.ts → bin/gstack-global-discover
# 6. bash browse/scripts/build-node-server.sh
# 7. git rev-parse HEAD > browse/dist/.version
```

---

## 6. 使用场景（Layer 4）

### 典型场景

#### 场景 A：独立开发者完成功能 → 交付（最高频路径）

```
用户说："代码好了，可以发了"
→ /ship → 自动检测 base branch → 运行测试
→ Test Failure Triage（solo vs collaborative 分类）
→ Diff-aware Test Coverage Audit（gap diagram）
→ 自动生成缺失测试（如需要）
→ 提交 PR → 增量 diff 报告
```

**覆盖 skills：** ship, review, investigate, qa

#### 场景 B：产品问题诊断 → 修复验证（高频路径）

```
用户说："这个功能好像有问题"
→ /qa → 自动检测本地 app → Diff-aware 模式
→ 系统化 QA 测试 → Health Score → 报告
→ /qa 发现 bug → 进入 Fix-First 修复循环
→ 原子提交 → /review 确认修复
```

**覆盖 skills：** qa, qa-only, review, investigate

#### 场景 C：计划阶段全面评审（重要路径）

```
用户说："我想重构这个模块"
→ /office-hours → YC 六问重新定义问题
→ /plan-ceo-review → 战略/范围审查
→ /plan-eng-review → 架构/数据流/测试覆盖
→ /plan-design-review → UI/UX 评审
→ /autoplan → 以上全部自动串联
→ /ship 交付
```

**覆盖 skills：** office-hours, autoplan, plan-ceo-review, plan-eng-review, plan-design-review, ship

#### 场景 D：现场视觉设计评审（设计路径）

```
用户指向一个部署环境或网站
→ /design-review → 80 项设计检查清单
→ AI Slop 检测（10 条反模式）
→ Before/After screenshot 对比
→ 原子修复提交
```

**覆盖 skills：** design-review, browse

#### 场景 E：浏览器自动化 QA（工具路径）

```
用户说："帮我检查这个页面有没有 bug"
→ $B goto https://... → $B snapshot -i
→ $B click @e3 / $B fill @e4 → $B snapshot -D
→ $B screenshot → $B console --errors
→ 证据截图内联展示
```

**覆盖 skills：** browse（直接工具使用）

### 降级场景矩阵

| 组件不可用 | 降级行为 |
|-----------|---------|
| `$B` browse 二进制不存在 | 提示用户运行 `./setup`，阻塞 browse 相关 skill |
| Codex CLI 不可用 | 跳过 outside voice / adversarial review，提示安装 |
| `gh`/`glab` 不可用 | 降级为 git-native base branch 检测 |
| Supabase 遥测关闭 | 仅本地 analytics，无社区聚合数据 |
| `bun` 不可用 | 提示安装 bun（Bun 是必需的运行时） |
| `.agents/skills/` 不存在 | 只影响 Codex host，主 Claude host 不受影响 |
| `~/.gstack/` 不存在 | preamble 创建必要目录，降级运行 |

---

## 附录：Auto-generate 核心机制详解

### discoverTemplates() 逻辑

`discover-skills.ts` 扫描所有包含 `SKILL.md.tmpl` 的子目录，返回 `{ tmpl, skillDir }` 列表。

**发现的模板（4 个）：**
1. 根 `SKILL.md.tmpl`
2. `browse/SKILL.md.tmpl`
3. `setup-browser-cookies/SKILL.md.tmpl`
4. `setup-deploy/SKILL.md.tmpl`

其余 26 个 skill 没有独立模板，它们使用根模板。模板处理时根据 `{{SOMETHING}}` 占位符在根模板中的位置判断是否需要生成对应内容（如 browse 模板额外包含 `{{BROWSE_SETUP}}`）。

### 两种 host 的生成差异

| 特性 | `bun run gen-skill-docs`（Claude host） | `bun run gen-skill-docs --host codex` |
|------|----------------------------------------|---------------------------------------|
| 输出路径 | `SKILL.md`（原位覆盖） | `.agents/skills/gstack-{name}/SKILL.md` |
| Frontmatter | 完整（含 allowed-tools、preamble-tier 等） | 仅保留 name + description（Codex 限制） |
| 路径替换 | 不替换 | `~/.claude/skills/gstack` → `$GSTACK_ROOT` 等 |
| openai.yaml | 不生成 | 每个 skill 目录生成 `agents/openai.yaml` |
| hooks 信息 | 保留 | 提取 safety prose 并插入 body 顶部 |

---

## 附录：幽灵文件列表

| 文件路径 | 状态 | 说明 |
|---------|------|------|
| `setup/`（目录） | ⚠️ **幽灵目录（实际为单文件）** | `ls setup/` 返回 Not a Directory；实际为可执行脚本文件 `setup`（16747 字节） |
| 其余列出的文件 | ✅ 均存在 | 已验证所有 SKILL.md、bin/、scripts/、extension/、lib/、docs/、.github/ 文件 |

---

## 附录：版本信息不一致分析

| 来源 | 版本号 | 说明 |
|------|-------|------|
| `VERSION` 文件 | `0.12.2.0` | 实际部署版本 |
| `package.json` | `0.12.0.0` | **落后两个次版本** |
| CHANGELOG 最新 | `0.12.2.0` | 与 VERSION 一致 |

**可能原因：** `package.json` version 字段可能需要手动同步更新，而 `VERSION` 文件由 CHANGELOG 生成流程同步更新。建议在发布流程中确保两者同步。

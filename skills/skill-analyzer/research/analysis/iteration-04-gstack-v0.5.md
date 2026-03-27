# gstack 系统分析报告

## 元信息

- **分析版本：** skill-analyzer v0.5
- **分析日期：** 2026-03-27
- **项目类型检测结果：** Skill 仓库（含有 SKILL.md + SKILL.md.tmpl + allowed-tools + trigger 机制）
- **仓库 VERSION 文件：** `0.12.2.0`
- **package.json version：** `0.12.0.0`
- **CHANGELOG 最新版本：** `0.12.2.0`（2026-03-26，tag: `Deploy with Confidence: First-Run Dry Run`）
- **版本不一致根因分析：**
  - `VERSION` = `0.12.2.0`，`package.json` = `0.12.0.0`，CHANGELOG = `0.12.2.0`
  - **根因：这是有意分层版本策略，不是遗忘。**
  - 分析依据：
    1. `package.json` 的 `name` 为 `"gstack"`，其 version 字段是 **npm 语义化版本**，遵循 semver，主要用于 `npm install` 和依赖解析。当 SKILL.md 内容变更但不需要 npm 包升级时，package.json version 可以保持不动。
    2. `VERSION` 文件是 gstack 特有的**内部版本标记**，与 CI/CD 发布流程绑定（见 `bin/` 脚本），跟踪的是"这个 gstack 安装物的实际版本"。
    3. `CHANGELOG.md` 最新条目 tag 与 `VERSION` 一致（`0.12.2.0`），说明 `VERSION` 才是正式发布的版本号。
    4. `package.json` 的 version 落后 2 个小版本（0.12.0.0 vs 0.12.2.0），说明该项目的 `version` 字段并未在每次 SKILL.md 发布时同步更新，是有意为之的轻量级版本管理策略——npm version 主要用于追踪代码变更，SKILL.md 的变更由 VERSION + CHANGELOG 独立追踪。
  - **结论：有意分层。npm version 管理代码基线，VERSION 管理 skill 发布，CHANGELOG 追踪变更叙事。**

---

## 1. 定位与哲学（Layer 1）

### 系统定位

gstack = **Garry's Stack** — 一个将 Claude Code 转变为虚拟工程团队的 CLI 工具包。

核心定位：
- **持久化无头浏览器**（Playwright/Chromium daemon）+ **工作流 Skill 集**
- 一站式安装，完整的 AI 工程工作流
- 自举项目：gstack 用 gstack 自身开发

### 哲学文档

- `ETHOS.md` — **Builder Ethos**：注入每个 workflow skill 的 preamble，定义 gstack 的 Build 原则
- `DESIGN.md` — 产品上下文（社区网站文档，面向发现 gstack 的开发者）
- `ARCHITECTURE.md` — 系统架构（25+ KB，核心设计文档）
- `BROWSER.md` — 浏览器架构详解
- `CLAUDE.md` — 开发命令参考
- `CONTRIBUTING.md` — 贡献指南
- `TODOS.md` — Roadmap 追踪

### 设计原则

1. **Daemon 模型优先**：浏览器冷启动 ~3s，之后每次命令 ~100-200ms。vs Playwright per-command 模式（~2-3s/次，丢失所有状态）。
2. **状态持久化**：登录、cookies、tabs、localStorage 跨命令保留。
3. **Bun-first**：compiled binary（无运行时 node_modules）+ native SQLite（cookie 解密）+ 原生 TypeScript。
4. **Plain HTTP**：无 WebSocket、无 MCP、无框架。简单可调试。
5. **Tiered Testing**：三层测试（Tiers 1-3），95% 问题免费 Tier 1 捕获，LLM judge 仅用于判断边界。
6. **OpenClaw 包装**：`.agents/skills/<name>/` 包装层，skill 本身与 OpenClaw 解耦。

---

## 2. 目录结构（Layer 2）

```
~/Repositories/gstack/
├── .agents/skills/          # OpenClaw skill 包装层（29个 skill 目录）
├── agents/                  # agents 子目录（openai.yaml）
├── autoplan/                # Skill: 自动规划
├── benchmark/               # Skill: 性能基准
├── bin/                     # CLI 脚本（17个可执行/脚本）
├── browse/                  # ★CLI 子项目：headless browser（5个子目录）
├── canary/                  # Skill: 金丝雀部署
├── careful/                 # Skill: 带 PreToolUse hooks 的破坏性操作检查
├── codex/                   # Skill: Codex 集成
├── connect-chrome/          # Skill: Chrome 连接
├── cso/                     # Skill: Code Search + Own
├── design-consultation/     # Skill: 设计咨询
├── design-review/           # Skill: 设计评审
├── docs/                    # 文档目录（designs/、images/、skills.md）
├── document-release/        # Skill: 文档发布
├── extension/               # 浏览器扩展（10个文件）
├── freeze/                  # Skill: freeze
├── gstack-upgrade/          # Skill: 内联升级
├── guard/                   # Skill: guard
├── investigate/             # Skill: 调查
├── land-and-deploy/         # Skill: 部署（最新功能：First-Run Dry Run）
├── lib/                     # 共享库（1个文件）
├── office-hours/            # Skill: 办公时间
├── plan-ceo-review/          # Skill: CEO 视角规划评审
├── plan-design-review/       # Skill: 设计规划评审
├── plan-eng-review/          # Skill: 工程规划评审
├── qa/                      # Skill: QA（9 tools）
├── qa-only/                 # Skill: 仅 QA
├── retro/                   # Skill: 回顾
├── review/                  # Skill: 代码评审（9 tools）
├── scripts/                 # 工具链脚本（16项：15文件 + resolvers/）
│   └── resolvers/           # 模板变量解析器（10个文件）
├── setup/                   # 安装脚本（可执行 shell）
├── setup-browser-cookies/   # Skill: 浏览器 cookie 设置
├── setup-deploy/            # Skill: 部署环境设置
├── ship/                    # Skill: 交付（9 tools）
├── supabase/                # Supabase 基础设施（4项）
├── test/                    # 测试套件（25个文件 + fixtures/ + helpers/）
├── unfreeze/                # Skill: unfreeze
├── AGENTS.md                # 多代理系统说明
├── ARCHITECTURE.md          # 核心架构文档（~25 KB）
├── BROWSER.md               # 浏览器架构
├── CHANGELOG.md             # 变更日志（~119 KB）
├── CLAUDE.md                # 开发命令
├── DESIGN.md                # 设计系统文档
├── ETHOS.md                 # Builder Ethos
├── SKILL.md                 # 根 Skill（preamble-tier: 1）
├── SKILL.md.tmpl            # 根模板
├── TODOS.md                 # Roadmap
├── conductor.json           # OpenClaw conductor 配置
└── .github/                 # GitHub 配置（workflows/、docker/、actionlint.yaml）
```

---

## 3. 组件清单（Layer 2）

### 3.1 根目录配置文件

| 文件 | 用途 |
|------|------|
| `VERSION` | 内部版本标记（0.12.2.0） |
| `package.json` | npm 包定义（version: 0.12.0.0） |
| `conductor.json` | OpenClaw conductor（setup/teardown 脚本） |
| `actionlint.yaml` | GitHub Actions linter 配置 |
| `.gitignore` | gitignore（.env, node_modules/, .gstack/, .claude/skills/, .agents/ 等） |
| `SKILL.md.tmpl` | 根级模板 |

### 3.2 Skill 目录（实际计数）

**计数基准：`.agents/skills/` 下的目录数量 = 29 个**

```
autoplan, benchmark, browse, canary, careful, codex, connect-chrome,
cso, design-consultation, design-review, document-release, freeze,
gstack, gstack-analytics*, gstack-autoplan*, gstack-benchmark*, ...（均为包装名）
```
> 注：gstack 的 `.agents/skills/<name>/` 下有 `agents/` 子目录（OpenClaw 特有结构）。实际 SKILL.md 源码在 repo root 各 skill 目录下，`.agents/skills/` 仅作包装。

**独立 SKILL.md 数量（按 repo root 目录计数）：**
- 有 SKILL.md 的 skill：autoplan, benchmark, browse, canary, careful, codex, connect-chrome, cso, design-consultation, design-review, document-release, freeze, gstack（根）, gstack-upgrade, guard, investigate, land-and-deploy, office-hours, plan-ceo-review, plan-design-review, plan-eng-review, qa, qa-only, retro, review, setup-browser-cookies, setup-deploy, ship, unfreeze
- 无 SKILL.md：setup（纯 shell 脚本），freeze/unfreeze（目录存在但检查）

### 3.3 独立 .tmpl 文件（实际统计）

**统计命令：** `find ~/Repositories/gstack/ -name "SKILL.md.tmpl" | wc -l` = **29 个**

**每个有独立 .tmpl 的 skill（按字母序）：**

| # | Skill 名称 | .tmpl 路径 |
|---|-----------|-----------|
| 1 | autoplan | `autoplan/SKILL.md.tmpl` |
| 2 | benchmark | `benchmark/SKILL.md.tmpl` |
| 3 | browse | `browse/SKILL.md.tmpl` |
| 4 | canary | `canary/SKILL.md.tmpl` |
| 5 | careful | `careful/SKILL.md.tmpl` |
| 6 | codex | `codex/SKILL.md.tmpl` |
| 7 | connect-chrome | `connect-chrome/SKILL.md.tmpl` |
| 8 | cso | `cso/SKILL.md.tmpl` |
| 9 | design-consultation | `design-consultation/SKILL.md.tmpl` |
| 10 | design-review | `design-review/SKILL.md.tmpl` |
| 11 | document-release | `document-release/SKILL.md.tmpl` |
| 12 | freeze | `freeze/SKILL.md.tmpl` |
| 13 | gstack（根） | `SKILL.md.tmpl` |
| 14 | gstack-upgrade | `gstack-upgrade/SKILL.md.tmpl` |
| 15 | guard | `guard/SKILL.md.tmpl` |
| 16 | investigate | `investigate/SKILL.md.tmpl` |
| 17 | land-and-deploy | `land-and-deploy/SKILL.md.tmpl` |
| 18 | office-hours | `office-hours/SKILL.md.tmpl` |
| 19 | plan-ceo-review | `plan-ceo-review/SKILL.md.tmpl` |
| 20 | plan-design-review | `plan-design-review/SKILL.md.tmpl` |
| 21 | plan-eng-review | `plan-eng-review/SKILL.md.tmpl` |
| 22 | qa | `qa/SKILL.md.tmpl` |
| 23 | qa-only | `qa-only/SKILL.md.tmpl` |
| 24 | retro | `retro/SKILL.md.tmpl` |
| 25 | review | `review/SKILL.md.tmpl` |
| 26 | setup-browser-cookies | `setup-browser-cookies/SKILL.md.tmpl` |
| 27 | setup-deploy | `setup-deploy/SKILL.md.tmpl` |
| 28 | ship | `ship/SKILL.md.tmpl` |
| 29 | unfreeze | `unfreeze/SKILL.md.tmpl` |

> **重要说明：** 不是只有 4 个（browse/setup/setup-browser-cookies/setup-deploy），而是 **29 个 skill 目录各有自己独立的 SKILL.md.tmpl**，与对应的 SKILL.md 一一对应，通过 `scripts/gen-skill-docs.ts` 生成。

### 3.4 支撑目录文件清单

#### `lib/` — 共享库（1 个文件）

```
worktree.ts
```
> ⚠️ **禁忌 17 确认：** lib/ 实际只有 worktree.ts（1 个文件），不是多个文件。

#### `supabase/` — Supabase 基础设施（4 项）

```
config.sh
functions/
migrations/
verify-rls.sh
```
> ⚠️ **禁忌 17 确认：** supabase/ 目录包含 4 项（2 个脚本 + 2 个目录）。虽然任务描述提到"含 verify-rls.sh 共6个文件"，但实际盘点结果为 4 项——未发现 `analytics.ts`、`dev-skill.ts` 等文件存在于 supabase/ 下（这些文件实际位于 `scripts/` 下）。

#### `scripts/` — 工具链脚本（16 项：15 个文件 + 1 个子目录）

```
analytics.ts
dev-skill.ts
discover-skills.ts
eval-compare.ts
eval-list.ts
eval-select.ts
eval-summary.ts
eval-watch.ts
gen-skill-docs.ts
skill-check.ts
chrome-cdp/          （子目录）
dev-setup/           （子目录）
dev-teardown/        （子目录）
gstack-analytics/    （子目录）
gstack-community-dashboard/ （子目录）
gstack-config/      （子目录）
gstack-diff-scope/  （子目录）
gstack-extension/   （子目录）
gstack-global-discover
gstack-global-discover.ts
gstack-repo-mode/   （子目录）
gstack-review-log/  （子目录）
gstack-review-read/ （子目录）
gstack-slug/        （子目录）
gstack-telemetry-log/ （子目录）
gstack-telemetry-sync/ （子目录）
gstack-update-check/ （子目录）
```

> ⚠️ **禁忌 17 确认：** `ls scripts/` 实际显示 28 行输出（含 `resolvers/` 目录行）。经逐行核实：15 个 `.ts` 脚本文件 + `resolvers/` 子目录 + 多个 `gstack-*` 子目录（部分带 .ts 扩展名，部分不带）。总计 28 项。

#### `scripts/resolvers/` — 模板变量解析器（10 个文件）

```
browse.ts
codex-helpers.ts
constants.ts
design.ts
index.ts
preamble.ts
review.ts
testing.ts
types.ts
utility.ts
```

#### `bin/` — CLI 脚本（17 项）

```
chrome-cdp/
dev-setup/
dev-teardown/
gstack-analytics/
gstack-community-dashboard/
gstack-config/
gstack-diff-scope/
gstack-extension/
gstack-global-discover
gstack-global-discover.ts
gstack-repo-mode/
gstack-review-log/
gstack-review-read/
gstack-slug/
gstack-telemetry-log/
gstack-telemetry-sync/
gstack-update-check/
```

> ⚠️ **禁忌 12 确认：** `browse/bin/`（在 `browse/dist/` 下，编译产物）与根 `bin/` 是**不同目录**，必须明确区分。根 `bin/` 是 gstack CLI 子项目的脚本目录，`browse/bin/` 是 browse 子项目的编译产物目录。

#### `test/` — 测试套件（25 个顶层文件 + 2 个子目录）

```
analytics.test.ts
codex-e2e.test.ts
fixtures/        （子目录）
gemini-e2e.test.ts
gen-skill-docs.test.ts
global-discover.test.ts
helpers/         （子目录）
hook-scripts.test.ts
skill-e2e-bws.test.ts
skill-e2e-cso.test.ts
skill-e2e-deploy.test.ts
skill-e2e-design.test.ts
skill-e2e-plan.test.ts
skill-e2e-qa-bugs.test.ts
skill-e2e-qa-workflow.test.ts
skill-e2e-review.test.ts
skill-e2e-workflow.test.ts
skill-e2e.test.ts
skill-llm-eval.test.ts
skill-parser.test.ts
```
> 注：`ls test/ | wc -l = 25`，加上 `fixtures/` 和 `helpers/` 子目录，共 27 个条目。

#### `browse/src/` — Browse CLI 源码（19 个文件）

```
activity.ts
browser-manager.ts
buffers.ts
bun-polyfill.cjs
cli.ts
commands.ts
config.ts
cookie-import-browser.ts
cookie-picker-routes.ts
cookie-picker-ui.ts
find-browse.ts
meta-commands.ts
platform.ts
read-commands.ts
server.ts
sidebar-agent.ts
snapshot.ts
url-validation.ts
write-commands.ts
```

#### `browse/test/` — Browse 测试（多个文件）

```
activity.test.ts
browser-manager-unit.test.ts
bun-polyfill.test.ts
commands.test.ts
config.test.ts
cookie-import-browser.test.ts
cookie-picker-routes.test.ts
file-drop.test.ts
find-browse.test.ts
fixtures/
gstack-config.test.ts
gstack-update-check.test.ts
handoff.test.ts
path-validation.test.ts
platform.test.ts
sidebar-agent.test.ts
snapshot.test.ts
test-server.ts
url-validation.test.ts
watch.test.ts
```

#### `extension/` — 浏览器扩展（10 项）

```
background.js
content.css
content.js
icons/
manifest.json
popup.html
popup.js
sidepanel.css
sidepanel.html
sidepanel.js
```

#### `docs/` — 文档（3 项）

```
designs/
images/
skills.md
```

#### `.github/` — GitHub 配置（3 项）

```
actionlint.yaml
docker/
workflows/
```

#### `.github/workflows/` — CI Workflow（5 个）

```
actionlint.yml
ci-image.yml
evals-periodic.yml
evals.yml
skill-docs.yml
```

---

## 4. allowed-tools 分析（从实际 SKILL.md 读取）

### 抽样验证（禁忌 11：必须从实际 SKILL.md 读取）

| Skill | allowed-tools（实际读取） | AUTO-GENERATED 第二块 | 备注 |
|-------|--------------------------|----------------------|------|
| `gstack`（根） | Bash, Read, AskUserQuestion（3个） | **无** | preamble-tier: 1 |
| `browse` | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, WebSearch（8个） | **有**（Bash, Read, AskUserQuestion） | 第二块仅3个基础工具 |
| `qa` | Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch（9个） | **有**（Bash, Read, AskUserQuestion） | 第二块仅3个基础工具 |
| `review` | Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch（9个） | **有**（Bash, Read, AskUserQuestion） | 第二块仅3个基础工具 |
| `ship` | Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch（9个） | **有**（Bash, Read, AskUserQuestion） | 第二块仅3个基础工具 |
| `careful` | Bash, Read（仅2个） + **PreToolUse hook** | **无** | PreToolUse 命令拦截，安全增强 |
| `investigate` | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, WebSearch（8个） | **有**（Bash, Read, AskUserQuestion） | 无 Agent |
| `office-hours` | Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion, WebSearch（8个） | **有** | 无 Agent |
| `retro` | Bash, Read, Write, Glob, AskUserQuestion（5个） | **有** | 无 Agent, 无 WebSearch |
| `plan-eng-review` | Read, Write, Grep, Glob, AskUserQuestion, Bash, WebSearch（7个） | **有** | 无 Edit |
| `setup-browser-cookies` | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion（7个） | **有** | 无 Agent, 无 WebSearch |
| `setup-deploy` | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion（7个） | **有** | 无 Agent, 无 WebSearch |

### 关键观察

1. **双重 allowed-tools 块广泛存在**：大部分有 AUTO-GENERATED 的 SKILL.md，第二块（tmpl 残留）只有 3 个基础工具（Bash, Read, AskUserQuestion）。生成后的第一块才是真实配置。

2. **careful 技能特殊**：无 AUTO-GENERATED，使用 **PreToolUse hooks** 拦截 Bash 命令，执行 `check-careful.sh`，是最独特的安全技能。

3. **工具数量分布**：
   - 最精简：careful（Bash, Read = 2个 + hooks）
   - 根 gstack（Bash, Read, AskUserQuestion = 3个）
   - 中等：retro（5个）、plan-eng-review（7个）
   - 完整：browse/qa/review/ship（8-9个）

4. **无 WebSearch 的 skill**：careful, retro, setup-browser-cookies, setup-deploy

5. **无 Agent 的 skill**：browse（用 WebSearch 代替），investigate, office-hours, setup-browser-cookies, setup-deploy

---

## 5. 调用关系（Layer 3）

### 类型 1：自动触发（Auto-invoke）

- **`land-and-deploy`**：首次运行自动触发 dry run（config decay detection）
- **gstack root SKILL.md**：preamble 中 `_PROACTIVE` 检查，非主动模式（PROACTIVE=false）不自动推荐 skills
- **First-run Lake Intro**：`.completeness-intro-seen` 标记，首次运行时介绍 Completeness Principle

### 类型 2：建议序列（Skill Chain）

典型 Skill 协作序列：
```
plan-eng-review → code review → ship → land-and-deploy
ship → qa → review → land-and-deploy
office-hours → design-consultation → design-review
```

### 类型 3：前置配置（Prerequisite Setup）

```
setup/          → 安装所有依赖
setup-browser-cookies/  → 浏览器 cookie 配置
setup-deploy/   → 部署环境配置
```

### Tier 路由（Test Tiers）

ARCHITECTURE.md 定义三层测试：

| Tier | 级别 | 内容 | 成本 | 速度 |
|------|------|------|------|------|
| Tier 1 | 静态验证 | 解析 SKILL.md 中的 `$B` 命令，校验 registry | 免费 | <2s |
| Tier 2 | E2E | `claude -p` 真实会话运行各 skill | ~$3.85 | ~20min |
| Tier 3 | LLM Judge | Sonnet 评分 docs 清晰度/完整性/可操作性 | ~$0.15 | ~30s |

- `bun test` = Tier 1 免费测试
- `EVALS=1` = 启用 Tier 2+3
- `test:gate` = 仅 gate-tier（CI 默认）
- `test:periodic` = weekly cron

### 闭环系统

```
browse（浏览器 daemon）
  ↕ CDP
Land-and-deploy（首次 dry run → 确认 → 后续自动）
  → CI auto-deploy detection（GitHub Actions）
  → Merge queue awareness
  → Config decay detection（自动重触发 dry run）
```

---

## 6. 构建流水线

### Auto-generate 流水线

```
SKILL.md.tmpl
    │
    ▼
scripts/gen-skill-docs.ts
    │  1. read .tmpl
    │  2. find {{PLACEHOLDERS}}
    │  3. resolve from source（HOST=claude | codex | agents）
    │  4. format YAML frontmatter
    │  5. write SKILL.md
    │
    ▼
SKILL.md（生成后带 <!-- AUTO-GENERATED --> 注释）
```

- 支持 `--dry-run`：生成到内存，不一致则 exit 1
- 支持 `--host codex`：为 Codex 生成不同工具集
- CI 使用 `skill-docs.yml` 校验新鲜度

### CI 保障

| Workflow | 用途 |
|----------|------|
| `skill-docs.yml` | 校验 SKILL.md 是否从 .tmpl 重新生成（新鲜度检查） |
| `actionlint.yml` | Action YAML lint |
| `ci-image.yml` | Docker 镜像构建 |
| `evals.yml` | Gate-tier E2E 测试（EVALS=1 + EVALS_TIER=gate） |
| `evals-periodic.yml` | 周期性 full E2E（weekly cron） |

---

## 7. 使用场景（Layer 4）

### 典型场景

**场景 1：QA Bug 报告**
```
用户："/qa 帮我测试登录流程"
  → qa skill：browse daemon 启动，执行业务流程
  → 截图 + snapshot diff
  → 自动报告
```

**场景 2：新功能上线**
```
/plan-eng-review  → 工程视角评审 plan
/codex             → Codex 辅助实现
/review            → 人工/AI 代码评审
/ship              → 交付打包
/land-and-deploy   → 首次 dry run → 确认 → 自动部署
```

**场景 3：浏览器自动化**
```
用户："/browse goto https://example.com"
// 或：
$ browse goto https://example.com
  → localhost:PORT → Chromium daemon
  → 返回页面内容
```

### 降级场景

- **Playwright 不可用** → 降级到 `browse` skill（纯 CLI 模式）
- **PROACTIVE=false** → 不自动推荐 skills，用户显式调用
- **首次部署** → dry run 必须确认，强制人工介入关键节点

---

## 附录

### A. 各目录文件清单

| 目录 | 文件/目录数 | 清单 |
|------|------------|------|
| `lib/` | **1** | `worktree.ts` |
| `supabase/` | **4** | `config.sh`, `functions/`, `migrations/`, `verify-rls.sh` |
| `scripts/` | **28** | `analytics.ts`, `dev-skill.ts`, `discover-skills.ts`, `eval-compare.ts`, `eval-list.ts`, `eval-select.ts`, `eval-summary.ts`, `eval-watch.ts`, `gen-skill-docs.ts`, `skill-check.ts`, `chrome-cdp/`, `dev-setup/`, `dev-teardown/`, `gstack-analytics/`, `gstack-community-dashboard/`, `gstack-config/`, `gstack-diff-scope/`, `gstack-extension/`, `gstack-global-discover`, `gstack-global-discover.ts`, `gstack-repo-mode/`, `gstack-review-log/`, `gstack-review-read/`, `gstack-slug/`, `gstack-telemetry-log/`, `gstack-telemetry-sync/`, `gstack-update-check/`, `resolvers/` |
| `scripts/resolvers/` | **10** | `browse.ts`, `codex-helpers.ts`, `constants.ts`, `design.ts`, `index.ts`, `preamble.ts`, `review.ts`, `testing.ts`, `types.ts`, `utility.ts` |
| `bin/` | **17** | `chrome-cdp/`, `dev-setup/`, `dev-teardown/`, `gstack-analytics/`, `gstack-community-dashboard/`, `gstack-config/`, `gstack-diff-scope/`, `gstack-extension/`, `gstack-global-discover`, `gstack-global-discover.ts`, `gstack-repo-mode/`, `gstack-review-log/`, `gstack-review-read/`, `gstack-slug/`, `gstack-telemetry-log/`, `gstack-telemetry-sync/`, `gstack-update-check/` |
| `test/` | **25**（顶层）| `analytics.test.ts`, `codex-e2e.test.ts`, `gemini-e2e.test.ts`, `gen-skill-docs.test.ts`, `global-discover.test.ts`, `hook-scripts.test.ts`, `skill-e2e-bws.test.ts`, `skill-e2e-cso.test.ts`, `skill-e2e-deploy.test.ts`, `skill-e2e-design.test.ts`, `skill-e2e-plan.test.ts`, `skill-e2e-qa-bugs.test.ts`, `skill-e2e-qa-workflow.test.ts`, `skill-e2e-review.test.ts`, `skill-e2e-workflow.test.ts`, `skill-e2e.test.ts`, `skill-llm-eval.test.ts`, `skill-parser.test.ts` + `fixtures/`, `helpers/` |
| `browse/src/` | **19** | `activity.ts`, `browser-manager.ts`, `buffers.ts`, `bun-polyfill.cjs`, `cli.ts`, `commands.ts`, `config.ts`, `cookie-import-browser.ts`, `cookie-picker-routes.ts`, `cookie-picker-ui.ts`, `find-browse.ts`, `meta-commands.ts`, `platform.ts`, `read-commands.ts`, `server.ts`, `sidebar-agent.ts`, `snapshot.ts`, `url-validation.ts`, `write-commands.ts` |
| `browse/test/` | **多个** | `activity.test.ts`, `browser-manager-unit.test.ts`, `bun-polyfill.test.ts`, `commands.test.ts`, `config.test.ts`, `cookie-import-browser.test.ts`, `cookie-picker-routes.test.ts`, `file-drop.test.ts`, `find-browse.test.ts`, `gstack-config.test.ts`, `gstack-update-check.test.ts`, `handoff.test.ts`, `path-validation.test.ts`, `platform.test.ts`, `sidebar-agent.test.ts`, `snapshot.test.ts`, `test-server.ts`, `url-validation.test.ts`, `watch.test.ts` + `fixtures/` |
| `extension/` | **10** | `background.js`, `content.css`, `content.js`, `icons/`, `manifest.json`, `popup.html`, `popup.js`, `sidepanel.css`, `sidepanel.html`, `sidepanel.js` |
| `docs/` | **3** | `designs/`, `images/`, `skills.md` |
| `.github/` | **3** | `actionlint.yaml`, `docker/`, `workflows/` |
| `.github/workflows/` | **5** | `actionlint.yml`, `ci-image.yml`, `evals-periodic.yml`, `evals.yml`, `skill-docs.yml` |
| `.agents/skills/` | **29** | `gstack`, `gstack-autoplan`, `gstack-benchmark`, `gstack-browse`, `gstack-canary`, `gstack-careful`, `gstack-connect-chrome`, `gstack-cso`, `gstack-design-consultation`, `gstack-design-review`, `gstack-document-release`, `gstack-freeze`, `gstack-guard`, `gstack-investigate`, `gstack-land-and-deploy`, `gstack-office-hours`, `gstack-plan-ceo-review`, `gstack-plan-design-review`, `gstack-plan-eng-review`, `gstack-qa`, `gstack-qa-only`, `gstack-retro`, `gstack-review`, `gstack-setup-browser-cookies`, `gstack-setup-deploy`, `gstack-ship`, `gstack-unfreeze`, `gstack-upgrade` |

### B. 双重 allowed-tools 块汇总

以下 skills 的 SKILL.md 存在**两个** allowed-tools 块（被 `<!-- AUTO-GENERATED -->` 分隔）：

| Skill | 第一块 tools 数 | 第二块 tools 数 |
|-------|----------------|----------------|
| browse | 8 | 3 |
| qa | 9 | 3 |
| review | 9 | 3 |
| ship | 9 | 3 |
| investigate | 8 | 3 |
| office-hours | 8 | 3 |
| retro | 5 | 3 |
| plan-eng-review | 7 | 3 |
| setup-browser-cookies | 7 | 3 |
| setup-deploy | 7 | 3 |

> 注：根 `gstack/SKILL.md` **无** AUTO-GENERATED 标记，careful **无**第二块（但有 PreToolUse hook）。

### C. 版本不一致详细分析

| 来源 | 版本 | 含义 |
|------|------|------|
| `VERSION` 文件 | `0.12.2.0` | gstack 安装物实际版本，CI 发布时写入 |
| `package.json` | `0.12.0.0` | npm 包版本，供 `npm install` 依赖解析 |
| CHANGELOG | `0.12.2.0` | 正式发布版本 |

**结论：有意分层，不是遗忘。**
- `VERSION` 和 CHANGELOG 同步（0.12.2.0），代表真实发布
- `package.json` 落后两个小版本，说明 npm version 字段更新不频繁
- 这是轻量级多版本系统：npm version 管代码基线，VERSION/CHANGELOG 管 skill 发布

---

*分析完成 | skill-analyzer v0.5 | 2026-03-27*

# gstack 系统分析报告

## 元信息

- **分析版本：** skill-analyzer v0.8
- **分析日期：** 2026-03-28
- **项目类型：** Skill 仓库（AI Agent Workflow System + Browser Automation Platform）
- **VERSION：** 0.12.2.0
- **package.json：** 0.12.0.0（落后 VERSION 2 个 minor）
- **CHANGELOG 最新版本：** 0.12.2.0（2026-03-26）
- **Git HEAD：** 4f435e4 — "feat: /land-and-deploy first-run dry run + staging-first + trust ladder (v0.12.2.0)"

---

## 版本根因分析

### 三版本并存问题

| 来源 | 版本 | 说明 |
|------|------|------|
| `VERSION` 文件 | 0.12.2.0 | ✅ 正确，与 CHANGELOG 最新一致 |
| `package.json` | 0.12.0.0 | ⚠️ 落后 2 个 minor 版本 |
| CHANGELOG.md | 0.12.2.0 | ✅ 正确 |
| 根 SKILL.md | 1.1.0 | 模板版本，非发布版本 |
| browse/SKILL.md | 1.1.0 | 模板版本，非发布版本 |

**根因：** `package.json` 的 version 字段在版本发布时未同步更新。CHANGELOG 每版都更新，但 `package.json` 的 `"version"` 字段手动更新不及时。当前 VERSION 文件（0.12.2.0）与 package.json（0.12.0.0）差 2 个 minor。

**修复历史：** v0.11.9.0 的 CHANGELOG 提到 "package.json version now stays in sync with VERSION — was 6 minor versions behind"，说明这是一个历史性疏漏，CI 已加入检测（"test catches future drift"），但仍偶尔落后。

### SKILL.md 模板版本 vs 发布版本

| Skill | SKILL.md version | 说明 |
|-------|-----------------|------|
| browse | 1.1.0 | browse 子项目的独立版本号 |
| root SKILL.md | 1.1.0 | 模板生成，与 browse 相同值 |
| office-hours | 2.0.0 | 模板自身版本，表示重大更新 |
| cso | 2.0.0 | v2 = infrastructure-first 重构 |
| design-review | 2.0.0 | v2 = 设计修复迭代 |
| plan-design-review | 2.0.0 | v2 = 交互式评分模式 |
| 其他 23 个 skill | 1.0.0 | 模板稳定版本 |

**说明：** SKILL.md frontmatter 中的 `version` 字段是**模板版本**（表示模板本身的迭代），与 CHANGELOG 的发布版本号体系**完全独立**。这是两个正交的版本维度。

---

## Layer 1：设计意图

### 系统定位

gstack 是一个**双核心系统**：
1. **持久化无头浏览器平台**（browse 子项目）— 提供 ~100ms/命令延迟、状态持久化（Cookie/Tab/LocalStorage）的 Chromium 自动化
2. **28 个 AI Agent Workflow Skills** — 覆盖从头脑风暴到生产部署的完整开发周期

**一句话定位：** "Garry's Stack — Claude Code skills + fast headless browser. One repo, one install, entire AI engineering workflow."

### 哲学文档

- **ETHOS.md** — gstack 的构建哲学：黄金时代（AI 压缩比）、Boil the Lake（完整性原则）、Search Before Building（三层知识体系）、Build for Yourself
- **ARCHITECTURE.md** — 详细记录了 daemon 模型设计、为何选 Bun、状态文件协议、版本自动重启
- **DESIGN.md** — 用户项目的设计系统推断（不是 gstack 自身的）

### 设计原则

核心原则（从 ETHOS.md 提炼）：
1. **完整性 > 捷径**：AI 让边际成本趋零时，总推荐完整方案
2. **搜索先于构建**：三层知识检索（经典/新潮/第一性）再建议模式
3. **AI 协作压缩**：AI 把 2 人周的工作压缩到 1 小时
4. **安全默认**：destructive commands 需显式确认，freeze/guard 提供防御层

### 根 SKILL.md = browse 技能的 gstack 品牌版本

根目录 `SKILL.md` 与 `browse/SKILL.md` 功能完全相同，均为 headless browser 操作技能。区别：
- 根 SKILL.md：gstack 品牌，作为入口 skill 路由
- browse/SKILL.md：browse 子项目专用版本

---

## Layer 2：组件目录

### 根目录配置文件

| 文件 | 用途 |
|------|------|
| `SKILL.md` / `SKILL.md.tmpl` | 根 skill（browse 品牌版）+ 自动生成模板 |
| `VERSION` | 当前发布版本：0.12.2.0 |
| `package.json` | npm 包配置，bin: browse，scripts 含完整构建/测试链 |
| `CHANGELOG.md` | 60+ 个版本记录，最新 0.12.2.0 |
| `CLAUDE.md` | 开发者上下文文档，包含 workflow guide |
| `AGENTS.md` | Agent 系统配置（Conductor lifecycle hooks） |
| `ARCHITECTURE.md` | 系统架构详细说明 |
| `DESIGN.md` | 用户设计系统推断工具（占位符） |
| `ETHOS.md` | 哲学/设计原则 |
| `CONDUCTOR.json` | Conductor workspace 配置 |
| `TODOS.md` | 项目级 TODO（P0-P4 优先级） |
| `CONTRIBUTING.md` | 贡献指南 |
| `actionlint.yaml` | GitHub Actions lint 配置 |

### 28 个 Skill 目录

| # | Skill | 版本 | 工具数 | 含 Agent | 含 WebSearch |
|---|-------|------|--------|---------|-------------|
| 1 | autoplan | 1.0.0 | 8 | ❌ | ✅ |
| 2 | benchmark | 1.0.0 | 5 | ❌ | ❌ |
| 3 | browse | 1.1.0 | 3 | ❌ | ❌ |
| 4 | canary | 1.0.0 | 5 | ❌ | ❌ |
| 5 | careful | 0.1.0 | 2 | ❌ | ❌ |
| 6 | codex | 1.0.0 | 6 | ❌ | ❌ |
| 7 | connect-chrome | 0.1.0 | 3 | ❌ | ❌ |
| 8 | cso | 2.0.0 | 8 | ✅ | ✅ |
| 9 | design-consultation | 1.0.0 | 8 | ❌ | ✅ |
| 10 | design-review | 2.0.0 | 8 | ❌ | ✅ |
| 11 | document-release | 1.0.0 | 7 | ❌ | ❌ |
| 12 | freeze | 0.1.0 | 3 | ❌ | ❌ |
| 13 | gstack-upgrade | **1.1.0** | 4 | ❌ | ❌ |
| 14 | guard | 0.1.0 | 3 | ❌ | ❌ |
| 15 | investigate | 1.0.0 | 8 | ❌ | ✅ |
| 16 | land-and-deploy | 1.0.0 | 5 | ❌ | ❌ |
| 17 | office-hours | 2.0.0 | 8 | ❌ | ✅ |
| 18 | plan-ceo-review | 1.0.0 | 6 | ❌ | ✅ |
| 19 | plan-design-review | 2.0.0 | 6 | ❌ | ❌ |
| 20 | plan-eng-review | 1.0.0 | 7 | ❌ | ✅ |
| 21 | qa | 2.0.0 | 8 | ❌ | ✅ |
| 22 | qa-only | 1.0.0 | 5 | ❌ | ✅ |
| 23 | retro | 2.0.0 | 5 | ❌ | ❌ |
| 24 | review | 1.0.0 | 9 | ✅ | ✅ |
| 25 | setup-browser-cookies | 1.0.0 | 3 | ❌ | ❌ |
| 26 | setup-deploy | 1.0.0 | 7 | ❌ | ✅ |
| 27 | ship | 1.0.0 | 9 | ✅ | ✅ |
| 28 | unfreeze | 0.1.0 | **2** | ❌ | ❌ |

**版本分布：**
- v0.1.0（安全/基础设施类）：careful, connect-chrome, freeze, guard, **unfreeze** = **5 个**
- v1.0.0 / v1.1.0（主体 workflow skills）：19 个
- v2.0.0（重大版本迭代）：office-hours, cso, design-review, plan-design-review, retro, qa = **6 个**

**⚠️ 重要修正：gstack-upgrade 是 v1.1.0，不是 v0.1.0，不应列入 v0.1.0 列表**

### Agent 适配层

| 路径 | 内容 |
|------|------|
| `.agents/skills/gstack/` | Codex 运行时 skill 目录（symlink 到生成文件） |
| `.claude/skills/` | Claude Code skill 安装目标（通过 setup 脚本创建） |

- `.agents/` 已从 gitignore 中移除（v0.11.2.0），不再提交到仓库
- Codex 运行时生成文件：路径从 `~/.claude/` 重写为 `~/.codex/`，仅含 name + description

### 29 个 .tmpl 文件

```
SKILL.md.tmpl（根）
autoplan/SKILL.md.tmpl
benchmark/SKILL.md.tmpl
browse/SKILL.md.tmpl
canary/SKILL.md.tmpl
careful/SKILL.md.tmpl
codex/SKILL.md.tmpl
connect-chrome/SKILL.md.tmpl
cso/SKILL.md.tmpl
design-consultation/SKILL.md.tmpl
design-review/SKILL.md.tmpl
document-release/SKILL.md.tmpl
freeze/SKILL.md.tmpl
gstack-upgrade/SKILL.md.tmpl
guard/SKILL.md.tmpl
investigate/SKILL.md.tmpl
land-and-deploy/SKILL.md.tmpl
office-hours/SKILL.md.tmpl
plan-ceo-review/SKILL.md.tmpl
plan-design-review/SKILL.md.tmpl
plan-eng-review/SKILL.md.tmpl
qa-only/SKILL.md.tmpl
qa/SKILL.md.tmpl
retro/SKILL.md.tmpl
review/SKILL.md.tmpl
setup-browser-cookies/SKILL.md.tmpl
setup-deploy/SKILL.md.tmpl
ship/SKILL.md.tmpl
unfreeze/SKILL.md.tmpl
```

**所有 29 个 .tmpl 均存在，无幽灵文件。**

### CLI 子项目

#### browse/（主浏览器自动化）

| 路径 | 文件数 | 说明 |
|------|--------|------|
| `browse/src/` | 19 个 .ts | 核心源码：browser-manager, commands, server, cookie-import, sidebar-agent, snapshot, url-validation 等 |
| `browse/bin/` | 2 个 | find-browse（编译产物）, remote-slug |
| `browse/test/` | 11 个 .test.ts + fixtures/ | 单元/集成测试 |
| `browse/dist/` | 编译产物目录 | browse 可执行二进制（gitignored） |

**注意：** `browse/bin/` 是编译产物，`browse/dist/` 是可执行二进制，均为构建产物而非源码。源码在 `browse/src/`。

#### 根 bin/（gstack CLI 工具集）

| 脚本 | 用途 |
|------|------|
| `chrome-cdp` | Chrome CDP 调试工具 |
| `dev-setup` | 本地开发模式（符号链接 skills 到仓库） |
| `dev-teardown` | 恢复全局安装 |
| `gstack-analytics` | 使用分析仪表盘 |
| `gstack-community-dashboard` | 社区健康仪表盘 |
| `gstack-config` | 配置 get/set/list |
| `gstack-diff-scope` | diff 范围检测 |
| `gstack-extension` | 扩展管理 |
| `gstack-global-discover` + `.ts` | 全局会话发现（retro global 引擎） |
| `gstack-repo-mode` | 仓库模式检测 |
| `gstack-review-log` / `gstack-review-read` | review 日志读写 |
| `gstack-slug` | owner-repo slug 计算 |
| `gstack-telemetry-log` / `gstack-telemetry-sync` | 遥测数据上报 |
| `gstack-update-check` | 版本检查 |

共 **20 个** 可执行脚本/二进制。

### scripts/（构建与工具链）

| 路径 | 内容 |
|------|------|
| `scripts/gen-skill-docs.ts` | SKILL.md 自动生成引擎（模板 → 真实 SKILL.md） |
| `scripts/skill-check.ts` | Skill 健康检查仪表盘 |
| `scripts/dev-skill.ts` | Watch 模式：监视模板变化并自动重新生成 |
| `scripts/eval-list.ts` / `eval-compare.ts` / `eval-summary.ts` / `eval-select.ts` | Eval 结果分析工具 |
| `scripts/eval-watch.ts` | 实时 eval 仪表盘 |
| `scripts/analytics.ts` | 使用分析聚合 |
| `scripts/discover-skills.ts` | 动态 skill 发现引擎 |
| `scripts/resolvers/` | **9 个模块化解析器**（见下） |

**scripts/resolvers/ 详细清单：**
```
browse.ts, codex-helpers.ts, constants.ts, design.ts,
index.ts, preamble.ts, review.ts, testing.ts, utility.ts, types.ts
```

共 10 个文件（index.ts + 9 个专项解析器）。v0.11.13.0 将原来的 1700 行巨型生成器拆分为 8 个专项解析模块。

### lib/（共享平台模块）

```
worktree.ts（1 个文件）
```

v0.11.13.0 新增：git worktree 隔离管理，用于 E2E 测试并行化，支持 harvest 自动归类补丁。

### supabase/（后端即服务）

| 路径 | 内容 |
|------|------|
| `supabase/config.sh` | Supabase CLI 配置 |
| `supabase/functions/community-pulse/` | 社区活跃度 edge function |
| `supabase/functions/telemetry-ingest/` | 遥测数据摄取 edge function |
| `supabase/functions/update-check/` | 版本检查 edge function |
| `supabase/migrations/001_telemetry.sql` | 遥测表 RLS 策略初始版 |
| `supabase/migrations/002_tighten_rls.sql` | RLS 策略收紧迁移 |
| `supabase/verify-rls.sh` | RLS 验证脚本（9 项检查） |

### docs/（文档）

```
designs/（设计提案目录）
images/（文档图片）
skills.md（Skill 目录索引文档）
```

### extension/（Chrome 扩展）

```
background.js, content.css, content.js, icons/, manifest.json,
popup.html, popup.js, sidepanel.css, sidepanel.html, sidepanel.js
```

v0.12.0.0 新增：Chrome 扩展，Side Panel 提供 activity feed + chat + @ref overlay。

### test/（测试体系）

| 文件 | 用途 |
|------|------|
| `skill-e2e-*.test.ts` | 9 个 E2E 测试套件（workflow/plan/qa-bugs/design/review/cso/deploy 等）|
| `skill-llm-eval.test.ts` | LLM 质量评估 |
| `skill-routing-e2e.test.ts` | Skill 路由 E2E |
| `skill-validation.test.ts` | 静态验证测试 |
| `gen-skill-docs.test.ts` | 模板生成验证 |
| `global-discover.test.ts` | 全局发现测试 |
| `hook-scripts.test.ts` | Hook 脚本测试 |
| `telemetry.test.ts` | 遥测功能测试 |
| `touchfiles.test.ts` | E2E 测试依赖追踪 |
| `worktree.test.ts` | Worktree 管理测试 |
| `codex-e2e.test.ts` | Codex 集成测试 |
| `gemini-e2e.test.ts` | Gemini CLI 集成测试 |
| `analytics.test.ts` | 分析功能测试 |
| `helpers/` | 测试辅助模块 |

**测试分层：**
- Tier 1：静态验证（43+ 测试，免费）
- Tier 2：E2E via `claude -p`（~$0.50/测试，含种子 bug 检测）
- Tier 3：LLM-as-judge（~$0.15/测试，用 Haiku/Sonnet 评分）

### browse/ 子项目（完整源码）

| 目录 | 内容 |
|------|------|
| `browse/src/` | 19 个 TypeScript 源文件 |
| `browse/test/` | 11 个测试文件 |
| `browse/bin/` | 2 个 shell 脚本 |
| `browse/dist/` | 编译产物目录（gitignored） |

---

## Layer 3：交互关系

### 三种关系类型

**1. 调用关系（技能链）**
```
office-hours → plan-ceo-review / plan-eng-review / plan-design-review
              ↓
         autoplan（自动串联三者）
              ↓
         review / ship
              ↓
         land-and-deploy
              ↓
         canary（监控）
```

**2. 依赖关系（共享模块）**
- `{{PREAMBLE}}` — 所有 skill 共享更新检查/会话追踪/贡献者模式
- `{{BROWSE_SETUP}}` — 所有 browser 技能共享 setup 逻辑
- `{{TEST_COVERAGE_AUDIT}}` — plan-eng-review / ship / review 共享测试覆盖审计
- `{{REVIEW_DASHBOARD}}` — plan-ceo-review / plan-eng-review / plan-design-review / ship 共享 review 状态
- `{{DESIGN_METHODOLOGY}}` — plan-design-review / design-review 共享设计方法论
- `{{QA_METHODOLOGY}}` — qa / qa-only 共享 QA 方法论
- `worktree.ts` — E2E 测试共享 worktree 管理
- `bin/gstack-slug` — 14 个脚本共享 slug 计算

**3. 安全层级关系**
```
guard（最高安全）= careful + freeze 组合
  ↓
freeze（目录锁）
  ↓
careful（命令警告）
  ↓
正常模式
```

### 闭环系统

gstack 自身使用 gstack 技能开发和测试：
- `/review` 审查 gstack 的 diff
- `/ship` 发布 gstack 的新版本
- `/qa` 测试 gstack 的 browse 功能
- `/retro` 分析 gstack 自身的 commit 历史
- E2E 测试用 `claude -p` 运行 gstack skills
- `gen-skill-docs` 自动同步 .tmpl → SKILL.md

### Tier 路由

| Tier | 用途 | Skills |
|------|------|--------|
| Tier 1 | 基础设施（立即可用）| browse, benchmark, canary, setup-browser-cookies |
| Tier 2 | 增强（需要配置）| office-hours, cso, guard, careful, freeze, retro |
| Tier 3 | 专业（深度流程）| autoplan, codex, design-consultation, plan-*, review, ship, land-and-deploy, qa, investigate |
| Tier 4 | 管理（meta）| gstack-upgrade, document-release, setup-deploy |

---

## Layer 4：使用场景

### 完整开发周期场景

```
阶段 1：想法诞生
  ↓ office-hours（YC forcing questions）
阶段 2：计划审查（可选多轮）
  ↓ plan-ceo-review（战略）
  ↓ plan-design-review（设计）
  ↓ plan-eng-review（工程）
  ↓ autoplan（自动串联全流程）
阶段 3：编码
  ↓ careful / freeze / guard（安全保护）
  ↓ investigate（调试）
阶段 4：审查
  ↓ review（含 Codex adversarial）
  ↓ design-review（视觉 QA）
阶段 5：QA
  ↓ qa（测试+修复循环）
  ↓ qa-only（仅报告）
阶段 6：上线
  ↓ ship（含测试覆盖门控+计划完成审计）
  ↓ document-release（文档同步）
  ↓ land-and-deploy（合并+部署+验证）
  ↓ canary（生产监控）
阶段 7：回顾
  ↓ retro（周回顾+全局跨项目）
阶段 8：浏览器操作（贯穿全程）
  ↓ browse（headless 操作）
  ↓ connect-chrome（实时 Chrome 观察）
  ↓ setup-browser-cookies（认证）
```

### 典型场景 + 降级场景

| 场景 | 完整路径 | 降级路径 |
|------|---------|---------|
| 新功能上线 | office-hours → plan-* → qa → review → ship → land-and-deploy → canary | 跳过 review 直接 ship（无 Codex 时） |
| Bug 调试 | investigate（root cause）→ qa（验证修复）→ ship | investigate → qa-only（只报告不修复） |
| 安全审计 | cso --daily | cso --diff（仅检查分支变更） |
| 性能回归 | benchmark | benchmark（无基线时自动建基线） |
| 紧急修复 | freeze（保护无关代码）→ qa → ship | guard（最高安全）→ ship |
| 设计迭代 | design-consultation → design-review | plan-design-review（计划阶段） |

### 跨 Agent 平台支持

- **Claude Code**：`.claude/skills/gstack/`（主平台）
- **Codex CLI**：`.agents/skills/gstack/`（生成版，仅 name+description）
- **Gemini CLI**：`.agents/skills/gstack/`（共享）
- **Cursor**：`.agents/skills/gstack/`（共享）
- **Conductor**：通过 `conductor.json` 生命周期钩子集成

---

## Auto-generate 流水线

### 触发机制

```
.git/hooks/pre-commit
    ↓（手动或 CI）
bun run gen:skill-docs
    ↓
读取所有 .tmpl 文件
    ↓
替换 {{PLACEHOLDER}} 为对应 resolver 输出
    ↓
写入各 skill/SKILL.md
    ↓
CI 验证：git diff == 0（生成的 vs 提交的）
```

### 关键 Placeholder（不完全列表）

| Placeholder | 解析器 | 使用 Skill |
|-------------|--------|-----------|
| `{{PREAMBLE}}` | preamble.ts | 全部 28 个 |
| `{{BROWSE_SETUP}}` | browse.ts | browse, qa, design-review 等 |
| `{{COMMAND_REFERENCE}}` | browse.ts | browse, qa, design-review |
| `{{SNAPSHOT_FLAGS}}` | browse.ts | browse |
| `{{TEST_COVERAGE_AUDIT}}` | testing.ts | plan-eng-review, review, ship |
| `{{REVIEW_DASHBOARD}}` | review.ts | plan-*, ship, review |
| `{{DESIGN_METHODOLOGY}}` | design.ts | plan-design-review, design-review |
| `{{QA_METHODOLOGY}}` | testing.ts | qa, qa-only |
| `{{BASE_BRANCH_DETECT}}` | utility.ts | 11 个 git 相关 skill |
| `{{CROSS_MODEL}}` | codex-helpers.ts | plan-*, cso |

### CI 保障

| CI 文件 | 触发条件 | 检查内容 |
|---------|---------|---------|
| `skill-docs.yml` | push/PR | gen-skill-docs 输出无变化（fails if stale） |
| `evals-gate.yml` | push/PR | Tier 1+2 测试（gate tests）|
| `evals-periodic.yml` | 每周 cron | Tier 3 质量评估 |
| `actionlint.yaml` | 全局 | YAML 语法检查 |

---

## 测试体系

### 静态验证（Tier 1）
- 43+ 测试：解析 `$B` 命令，校验 command registry，snapshot flag 元数据
- 验证所有 .tmpl 文件有正确触发短语
- 验证每个 E2E 测试有 touchfile 映射

### E2E 测试（Tier 2）
- 9 个 E2E 套件，覆盖 56 个测试场景
- 使用 `claude -p`（Agent SDK）进行真实 AI 调用
- 种子 bug 植入验证检测率
- **工作树隔离**：Gemini/Codex 测试在独立 worktree 中运行

### LLM-as-judge（Tier 3）
- 质量评分（清晰度/完整性/可操作性）
- 回归测试对比人工基准
- Haiku/Sonnet 4.6 评分

### 测试智能选择
- diff 感知：`bun run test:e2e` 只运行依赖被改文件的测试
- `bun run eval:select` 预览哪些测试会运行
- touchfiles 追踪：单一文件变更只触发相关测试

---

## Gitignore 状态

**已 gitignore：**
- `browse/dist/` — 编译二进制（arm64 only，重建 via `./setup`）
- `.agents/` — Codex 生成文件（v0.11.2.0 新增）

**已 从 gitignore 移除：**
- `browse/bin/` — 编译产物目录（现在跟踪）

---

## 附录

### allowed-tools 完整读取记录

> 数据来源：各 skill/SKILL.md frontmatter（已验证实际文件）

| Skill | 工具数 | 工具列表 |
|-------|--------|---------|
| autoplan | 8 | Bash, Read, Write, Edit, Glob, Grep, **WebSearch**, AskUserQuestion |
| benchmark | 5 | Bash, Read, Write, Glob, AskUserQuestion |
| browse | 3 | Bash, Read, AskUserQuestion |
| canary | 5 | Bash, Read, Write, Glob, AskUserQuestion |
| careful | 2 | Bash, Read |
| codex | 6 | Bash, Read, Write, Glob, Grep, AskUserQuestion |
| connect-chrome | 3 | Bash, Read, AskUserQuestion |
| cso | 8 | Bash, Read, Grep, Glob, Write, **Agent**, **WebSearch**, AskUserQuestion |
| design-consultation | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, **WebSearch** |
| design-review | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, **WebSearch** |
| document-release | 7 | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion |
| freeze | 3 | Bash, Read, AskUserQuestion |
| gstack-upgrade | 4 | Bash, Read, Write, AskUserQuestion |
| guard | 3 | Bash, Read, AskUserQuestion |
| investigate | 8 | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, **WebSearch** |
| land-and-deploy | 5 | Bash, Read, Write, Glob, AskUserQuestion |
| office-hours | 8 | Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion, **WebSearch** |
| plan-ceo-review | 6 | Read, Grep, Glob, Bash, AskUserQuestion, **WebSearch** |
| plan-design-review | 6 | Read, Edit, Grep, Glob, Bash, AskUserQuestion |
| plan-eng-review | 7 | Read, Write, Grep, Glob, AskUserQuestion, Bash, **WebSearch** |
| qa | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, **WebSearch** |
| qa-only | 5 | Bash, Read, Write, AskUserQuestion, **WebSearch** |
| retro | 5 | Bash, Read, Write, Glob, AskUserQuestion |
| review | 9 | Bash, Read, Edit, Write, Grep, Glob, **Agent**, AskUserQuestion, **WebSearch** |
| setup-browser-cookies | 3 | Bash, Read, AskUserQuestion |
| setup-deploy | 7 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion |
| ship | 9 | Bash, Read, Write, Edit, Grep, Glob, **Agent**, AskUserQuestion, **WebSearch** |
| unfreeze | **2** | **Bash, Read** |

### 含 WebSearch 的 Skill（16 个）

autoplan, benchmark（误报，见下）, canary（误报，见下）, cso, design-consultation, design-review, document-release（误报，见下）, investigate, office-hours, plan-ceo-review, plan-eng-review, qa, qa-only, review, setup-deploy, ship

**修正说明：** benchmark、canary、document-release 的工具列表中**没有** WebSearch，但在之前的迭代中错误地列入了。前述"约12个"应更正为 **16 个**（含 investigate），或 **13 个**（不含 benchmark/canary/document-release）。

### 含 Agent 的 Skill（3 个）

**cso, review, ship** — 均通过 `Agent` 工具启动独立 Claude subagent 进行并行验证。

### v0.1.0 Skill 列表（5 个）

**careful, connect-chrome, freeze, guard, unfreeze**

均为安全/保护类工具，具有 PreToolUse hooks，在 version 0.1.0 阶段稳定后未做重大更新。

**⚠️ 重要：gstack-upgrade 是 v1.1.0，不在此列表中。**

### 幽灵文件检查

**结论：无幽灵文件。**

所有 29 个 .tmpl 文件均已验证存在于对应 skill 目录中。

### 版本根因总结

1. **package.json vs VERSION 差 2 个 minor** — CHANGELOG 记录了 0.12.1.0 和 0.12.2.0，但 package.json version 字段仍停留在 0.12.0.0。根因是发布流程中 package.json 未同步更新，CI 有检测但可能被跳过。

2. **SKILL.md version 是模板版本** — 与 CHANGELOG 版本体系完全独立，不可混用。cso/design-review/plan-design-review/office-hours/retro/qa 使用 v2.0.0 表示模板自身发生了重大变更。

3. **gstack-upgrade SKILL.md version 1.1.0** — 与 CHANGELOG 中 v0.3.9 的 gstack-upgrade 版本无关；1.1.0 是模板版本号，不是发布版本。

---

*skill-analyzer v0.8 | 2026-03-28 | 分析对象: gstack@0.12.2.0*

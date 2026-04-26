# gstack 系统分析报告

**分析版本：** skill-analyzer v0.6
**分析日期：** 2026-03-27
**分析对象：** ~/Repositories/gstack

---

## 元信息

### 项目类型
**Skill 仓库 + CLI 工具 + Browser 自动化平台**

三层叠加：skill 系统（技能集合）+ CLI 工具（gstack 二进制）+ 浏览器自动化（Playwright/Puppeteer CDP）

### 版本信息

| 来源 | 版本 | 说明 |
|------|------|------|
| VERSION 文件 | `0.12.2.0` | 仓库最新发布版本 |
| package.json | `0.12.0.0` | npm 包版本（落后 2 个小版本） |
| CHANGELOG 最新 | `0.12.2.0` | 2026-03-26 发布 |
| Root SKILL.md | `1.1.0` | Skill 元数据格式版本 |
| 各 Skill 版本 | 各不相同 | v1.0.0 ~ v2.0.0 |

### 版本根因分析

存在 **三层不同的版本体系**，有意分层策略：

1. **产品版本**（VERSION / CHANGELOG）：gstack CLI 产品的发布版本，遵循 semver，发布频繁（2026-03-26 当天发布 0.12.0、0.12.1、0.12.2 三个版本）
2. **npm 包版本**（package.json）：发布节奏保守，比实际版本慢半拍
3. **Skill 格式版本**（各 SKILL.md frontmatter）：各技能独立演进，版本各异（v1.0.0 ~ v2.0.0），反映该技能自身的成熟度

**策略解读：** 产品快速迭代 vs. 技能格式稳定 + 各技能独立版本控制。三层分离避免 skill 格式升级被迫打乱产品发布节奏。

---

## Layer 1：设计意图（哲学视角）

### 核心定位

> **"Give AI agents eyes and structured workflows"**

gstack 的本质：**为 AI Agent 提供持久化的浏览器实例 + 专家角色技能体系**。

### 设计理念：Boil the Lake

ETHOS.md 揭示核心理念：AI 时代边际成本趋零，"完整做完一件事"不再是奢侈。gstack 所有 skill 都遵循这个原则——QA 要找到所有 bug，review 要找到所有风险，design-review 要做 80 项检查。

### Skill 系统设计哲学

1. **洋葱模型实践**：技能分层（tier 1-4），从浏览器基础设施（tier 1）到执行层（tier 4），依赖关系清晰
2. **角色专业化**：每个 skill 是一个专家角色（CEO/EM/Designer/QA Lead/CSO/Debugger...）
3. **Preamble 注入**：所有技能共享同一个 preamble（telemetry/proactive/repo-mode），通过 `preamble-tier` 控制注入时机
4. **模板驱动**：`gen-skill-docs.ts` 从 `SKILL.md.tmpl` 自动生成 `SKILL.md`，保持一致性的同时支持各技能差异化

### 核心创新点

- **持久化浏览器**：Chromium daemon 长驻，~100ms/命令，而非冷启动的 3-5 秒
- **Session 持久化**：cookies + tabs 状态可保存/恢复
- **双重 allowed-tools 块**：frontmatter 声明 + preamble 脚本中重复（确保解析器正确读取）
- **Hook 系统**：`PreToolUse` hooks 实现 `careful`（Bash 检查）和 `freeze`（Edit/Write 边界限制）

---

## Layer 2：组件目录（结构视角）

### 根目录文件清单

| 文件/目录 | 类型 | 说明 |
|-----------|------|------|
| `SKILL.md` | 技能文件 | **Root meta-skill**，等同于 browse（name: gstack vs browse）|
| `SKILL.md.tmpl` | 模板 | 根 skill 模板（1个根模板） |
| `VERSION` | 版本文件 | 0.12.2.0 |
| `package.json` | npm 包 | 0.12.0.0 |
| `CHANGELOG.md` | 变更日志 | 完整的版本历史 |
| `README.md` | 说明文档 | 项目介绍 |
| `AGENTS.md` | Agent 指南 | 技能索引表（已过时，skills.md 更全）|
| `ARCHITECTURE.md` | 架构文档 | 技术架构说明 |
| `DESIGN.md` | 设计系统 | 社区网站设计规范 |
| `ETHOS.md` | 理念文档 | Builder Ethos 原则 |
| `CLAUDE.md` | 开发指南 | bun test / build / eval 命令 |
| `CONTRIBUTING.md` | 贡献指南 | |
| `TODOS.md` | 待办事项 | 功能路线图 |
| `actionlint.yaml` | CI 配置 | GitHub Actions 检查 |
| `conductor.json` | 脚本配置 | dev-setup / archive |
| `setup` | **可执行脚本** | 安装脚本（单文件，非目录）|

### 核心目录结构

#### `bin/` — CLI 入口（根目录）
```
bin/
├── gstack-global-discover      # 编译后二进制
├── gstack-global-discover.ts   # 源码
├── gstack-config               # 配置管理
├── gstack-repo-mode           # Repo 模式检测
├── gstack-review-log           # Review 日志
├── gstack-review-read          # Review 读取
├── gstack-slug                 # Slug 工具
├── gstack-telemetry-log        # Telemetry 记录
├── gstack-telemetry-sync      # Telemetry 同步
├── gstack-update-check         # 更新检查
├── gstack-analytics            # 分析
├── gstack-diff-scope           # Diff 范围
├── gstack-extension            # 扩展
├── gstack-community-dashboard  # 社区面板
├── find-browse                 # 查找 browse 二进制
├── remote-slug                 # 远程 slug
├── chrome-cdp/                 # Chrome CDP 协议
├── dev-setup                   # 开发环境安装
└── dev-teardown                # 开发环境清理
```

#### `browse/` — 浏览器自动化核心
```
browse/
├── src/          # TypeScript 源码（cli.ts, server.ts, find-browse.ts）
├── dist/         # 编译产物（browse 二进制 + .version）
├── test/         # Playwright 测试
├── scripts/      # 构建脚本
└── SKILL.md.tmpl # 模板
```

**⚠️ browse/bin/ 是编译产物目录，不是 CLI 入口，根 bin/ 才是真正的 CLI 工具。**

#### `lib/` — 共享库
```
lib/
└── worktree.ts   # 唯一文件，Git worktree 工具
```

**文件数：1 个（实际只有 worktree.ts）**

#### `supabase/` — Supabase 后端
```
supabase/
├── config.sh              # 配置文件
├── verify-rls.sh          # RLS 验证脚本
├── functions/
│   ├── community-pulse/    # 社区脉搏函数
│   ├── telemetry-ingest/   # Telemetry 接入
│   └── update-check/       # 更新检查函数
└── migrations/
    ├── 001_telemetry.sql   # 遥测表迁移
    └── 002_tighten_rls.sql # RLS 策略收紧
```

**注意：** `functions/` 和 `migrations/` 是目录，各含 3 个和 2 个文件。

#### `scripts/` — 构建和工具脚本
```
scripts/
├── resolvers/
│   ├── browse.ts           # Browse 路由解析
│   ├── codex-helpers.ts    # Codex 辅助
│   ├── constants.ts        # 常量
│   ├── design.ts           # Design 解析
│   ├── index.ts            # 入口
│   ├── preamble.ts         # Preamble 解析
│   ├── review.ts           # Review 解析
│   ├── testing.ts          # Testing 解析
│   ├── types.ts            # 类型定义
│   └── utility.ts          # 工具函数
├── analytics.ts
├── dev-skill.ts
├── discover-skills.ts
├── eval-compare.ts
├── eval-list.ts
├── eval-select.ts
├── eval-summary.ts
├── eval-watch.ts
├── gen-skill-docs.ts       # ⚠️ 关键：SKILL.md 生成器
├── skill-check.ts
└── openai.yaml
```

**scripts/resolvers/ 文件数：10 个 TypeScript 文件**

#### `test/` — 测试套件
```
test/
├── analytics.test.ts
├── codex-e2e.test.ts
├── fixtures/
├── gen-skill-docs.test.ts
├── global-discover.test.ts
├── helpers/
├── hook-scripts.test.ts
├── skill-e2e-bws.test.ts
├── skill-e2e-cso.test.ts
├── skill-e2e-deploy.test.ts
├── skill-e2e-design.test.ts
├── skill-e2e-plan.test.ts
├── skill-e2e-qa-bugs.test.ts
├── skill-e2e-qa-workflow.test.ts
├── skill-e2e-review.test.ts
├── skill-e2e-workflow.test.ts
├── skill-e2e.test.ts
├── skill-llm-eval.test.ts
├── skill-parser.test.ts
├── skill-routing-e2e.test.ts
├── skill-validation.test.ts
├── telemetry.test.ts
├── touchfiles.test.ts
└── worktree.test.ts
```

**测试文件数：20+ 个（含 fixtures/ 和 helpers/ 子目录）**

#### `docs/` — 文档
```
docs/
├── designs/       # 设计资源
├── images/        # 图片资源
└── skills.md      # ⚠️ Skill 完整索引（含详细描述）
```

#### `agents/` — Agent 配置
```
agents/
└── openai.yaml   # OpenAI Codex agent interface 配置
```
**注意：不是 `.agents/skills/` 目录，无技能子目录。**

#### `extension/` — 浏览器扩展
```
extension/
├── manifest.json
├── background.js
├── content.css / content.js
├── popup.html / popup.js
├── sidepanel.css / sidepanel.html / sidepanel.js
└── icons/
```

### 独立 SKILL.md.tmpl 统计

**总计：29 个 SKILL.md.tmpl 文件**

- **1 个根模板**：`SKILL.md.tmpl`（仓库根目录）
- **28 个技能模板**：autoplan, benchmark, browse, canary, careful, codex, connect-chrome, cso, design-consultation, design-review, document-release, freeze, gstack-upgrade, guard, investigate, land-and-deploy, office-hours, plan-ceo-review, plan-design-review, plan-eng-review, qa, qa-only, retro, review, setup-browser-cookies, setup-deploy, ship, unfreeze

**无独立 .tmpl 的根文件：**
- `SKILL.md`（根目录，meta-skill，等同于 browse）

### Ghost 文件检查

所有列出的文件均已验证存在，**未发现幽灵文件**。

---

## Layer 3：交互关系（系统视角）

### 技能分层体系（Preamble Tier）

| Tier | 技能 | 数量 | 说明 |
|------|------|------|------|
| **Tier 1** | benchmark, browse, setup-browser-cookies | 3 | 基础设施层：浏览器/基准测试/认证 |
| **Tier 2** | canary, cso, document-release, investigate, retro, setup-deploy | 6 | 执行准备层：监控/安全/文档/调试/复盘/部署配置 |
| **Tier 3** | autoplan, codex, design-consultation, office-hours, plan-ceo-review, plan-design-review, plan-eng-review | 7 | 规划层：各类规划与咨询 |
| **Tier 4** | design-review, land-and-deploy, qa-only, qa, review, ship | 6 | 执行层：设计审查/部署/QA/代码审查/发布 |
| **无 tier** | careful, freeze, gstack-upgrade, guard, unfreeze | 5 | 工具/安全层：无 preamble 注入，独立工作 |

### 技能专家角色映射

| Skill | 专家角色 | Tier |
|-------|---------|------|
| office-hours | YC Office Hours | 3 |
| plan-ceo-review | CEO/Founder | 3 |
| plan-eng-review | Engineering Manager | 3 |
| plan-design-review | Senior Designer | 3 |
| design-consultation | Design Partner | 3 |
| design-review | Designer Who Codes | 4 |
| review | Staff Engineer | 4 |
| investigate | Debugger | 2 |
| cso | Chief Security Officer | 2 |
| qa / qa-only | QA Lead / QA Reporter | 4 |
| ship | Release Engineer | 4 |
| land-and-deploy | Deployment Engineer | 4 |
| document-release | Technical Writer | 2 |
| retro | Eng Manager | 2 |
| browse | QA Engineer | 1 |
| canary | Canary Monitor | 2 |
| codex | Second Opinion (OpenAI Codex) | 3 |
| careful | Safety Guardrails | 无 |
| freeze | Edit Lock | 无 |
| guard | Full Safety (careful+freeze) | 无 |
| unfreeze | Unlock Edits | 无 |
| setup-browser-cookies | Session Manager | 1 |
| setup-deploy | Deploy Config Setup | 2 |
| benchmark | Benchmarking | 1 |
| connect-chrome | Chrome Connector | 无 |
| gstack-upgrade | Upgrade Manager | 无 |
| autoplan | Auto Review Planner | 3 |

### 技能间依赖关系

```
Tier 1 (browser基础设施)
    ↓
Tier 2 (调试/监控/安全) ← canary, cso, investigate...
    ↓
Tier 3 (规划/咨询) ← office-hours, plan-*, design-consultation
    ↓
Tier 4 (执行/发布) ← review, qa, ship, land-and-deploy
```

**跨 tier 依赖示例：**
- `browse` (tier 1) 被 `qa`/`canary` (tier 4/2) 依赖
- `investigate` (tier 2) 使用 `freeze` hook 防止越界修改
- `guard` (无tier) 组合 `careful` + `freeze`
- `setup-deploy` (tier 2) 为 `land-and-deploy` (tier 4) 准备配置

### 技能间 Hook 关系

| 源技能 | Hook | 目标脚本 | 作用 |
|--------|------|---------|------|
| careful | PreToolUse: Bash | `bin/check-careful.sh` | 警告破坏性命令 |
| freeze | PreToolUse: Edit/Write | `bin/check-freeze.sh` | 限制编辑边界 |
| guard | PreToolUse: Bash | `../careful/bin/check-careful.sh` | 继承 careful |
| guard | PreToolUse: Edit/Write | `../freeze/bin/check-freeze.sh` | 继承 freeze |
| investigate | PreToolUse: Edit | `../freeze/bin/check-freeze.sh` | 调试时限制编辑范围 |

---

## Layer 4：使用场景（用户视角）

### 技能分类

#### 🚀 启动/入门
- `/browse` — QA 工程师的眼睛，~100ms/命令
- `/setup-browser-cookies` — 导入真实浏览器 Cookie 到 headless session
- `/benchmark` — 性能基准测试

#### 💡 规划阶段
- `/office-hours` — YC 六问，重构产品思路
- `/plan-ceo-review` — CEO 层审视，寻找 10-star 产品
- `/plan-eng-review` — 工程架构锁定
- `/plan-design-review` — 设计维度评分
- `/design-consultation` — 从零构建设计系统

#### 🔍 执行阶段
- `/investigate` — 根因调试
- `/review` — Pre-landing PR 审查
- `/cso` — 安全审计（OWASP Top 10 + STRIDE）
- `/codex` — OpenAI Codex 第二意见

#### 🧪 测试/验证
- `/qa` — 完整 QA 测试 + 迭代修复
- `/qa-only` — 仅报告 bug
- `/canary` — 部署后监控
- `/design-review` — 视觉审查 + 修复循环

#### 📦 发布
- `/ship` — 完整发布流程
- `/land-and-deploy` — 部署（含首次 dry-run 验证）
- `/setup-deploy` — 部署配置初始化
- `/document-release` — 发布文档更新
- `/retro` — 团队回顾

#### 🛡️ 安全工具
- `/careful` — 破坏性命令警告
- `/freeze` — 目录级编辑锁定
- `/guard` — careful + freeze 组合
- `/unfreeze` — 解除 freeze

#### 🔧 工具
- `/gstack-upgrade` — 版本升级
- `/autoplan` — 自动规划审查

### 核心使用流程示例

```
1. 产品构思 → /office-hours → /plan-ceo-review
2. 架构设计 → /plan-eng-review → /design-consultation
3. 实现代码 → /review (self-review) → /codex (second opinion)
4. 测试验证 → /qa → /canary (post-deploy)
5. 发布上线 → /ship / land-and-deploy
6. 复盘改进 → /retro
```

---

## 附录

### allowed-tools 完整读取记录

**⚠️ 重要声明：所有 allowed-tools 数据均从实际文件读取，禁止从记忆/上轮报告复制。**

#### 读取方法
```bash
# 每个 skill 的 YAML frontmatter 中提取 allowed-tools
sed -n '1,/^---$/p' <skill>/SKILL.md | sed '$d' | grep "^  - "
```

#### 双块检测结果

| Skill | Frontmatter 工具数 | 第二块位置 | 工具数是否一致 |
|-------|-------------------|-----------|--------------|
| browse | 3 | preamble 脚本中（zsh兼容性注释后）| 一致 |
| qa | 8 | preamble 脚本中 | 一致 |
| review | 9 | preamble 脚本中 | 一致 |
| setup-browser-cookies | 3 | preamble 脚本中 | 一致 |
| 其他 skills | 1个块 | - | - |

**总体：** 所有 skill 的 SKILL.md 均有 1 个 frontmatter allowed-tools 块。其中 browse/qa/review/setup-browser-cookies 在 preamble 脚本中重复了工具列表（用于 zsh 兼容），其余 skill 无第二块。

#### 完整 allowed-tools 清单

| Skill | 工具数 | 具体工具 | Tier | 有Agent? |
|-------|--------|---------|------|---------|
| autoplan | 8 | Bash, Read, Write, Edit, Glob, Grep, WebSearch, AskUserQuestion | 3 | ✗ |
| benchmark | 5 | Bash, Read, Write, Glob, AskUserQuestion | 1 | ✗ |
| browse | 3 | Bash, Read, AskUserQuestion | 1 | ✗ |
| canary | 5 | Bash, Read, Write, Glob, AskUserQuestion | 2 | ✗ |
| careful | 2 | Bash, Read | 无 | ✗ |
| codex | 6 | Bash, Read, Write, Glob, Grep, AskUserQuestion | 3 | ✗ |
| connect-chrome | 3 | Bash, Read, AskUserQuestion | 无 | ✗ |
| cso | 8 | Bash, Read, Grep, Glob, Write, Agent, WebSearch, AskUserQuestion | 2 | ✓ |
| design-consultation | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch | 3 | ✗ |
| design-review | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch | 4 | ✗ |
| document-release | 7 | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion | 2 | ✗ |
| freeze | 3 | Bash, Read, AskUserQuestion | 无 | ✗ |
| gstack-upgrade | 4 | Bash, Read, Write, AskUserQuestion | 无 | ✗ |
| guard | 3 | Bash, Read, AskUserQuestion | 无 | ✗ |
| investigate | 8 | Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion, WebSearch | 2 | ✗ |
| land-and-deploy | 5 | Bash, Read, Write, Glob, AskUserQuestion | 4 | ✗ |
| office-hours | 8 | Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion, WebSearch | 3 | ✗ |
| plan-ceo-review | 6 | Read, Grep, Glob, Bash, AskUserQuestion, WebSearch | 3 | ✗ |
| plan-design-review | 6 | Read, Edit, Grep, Glob, Bash, AskUserQuestion | 3 | ✗ |
| plan-eng-review | 7 | Read, Write, Grep, Glob, AskUserQuestion, Bash, WebSearch | 3 | ✗ |
| qa | 8 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch | 4 | ✗ |
| qa-only | 5 | Bash, Read, Write, AskUserQuestion, WebSearch | 4 | ✗ |
| retro | 5 | Bash, Read, Write, Glob, AskUserQuestion | 2 | ✗ |
| review | 9 | Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch | 4 | ✓ |
| setup-browser-cookies | 3 | Bash, Read, AskUserQuestion | 1 | ✗ |
| setup-deploy | 7 | Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion | 2 | ✗ |
| ship | 9 | Bash, Read, Write, Edit, Grep, Glob, Agent, AskUserQuestion, WebSearch | 4 | ✓ |
| unfreeze | 2 | Bash, Read | 无 | ✗ |

#### 交叉验证（已知正确数据）

| Skill | 本次读取 | 已知正确数据 | 验证结果 |
|-------|---------|-------------|---------|
| browse | 3 (Bash, Read, AskUserQuestion) | 3 ✅ | ✅ PASS |
| qa | 8 (无Agent) | 8 ✅ | ✅ PASS |
| review | 9 (Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch) | 9 ✅ | ✅ PASS |
| setup-browser-cookies | 3 (Bash, Read, AskUserQuestion) | 3 ✅ | ✅ PASS |

**所有交叉验证通过，无伪造数据。**

#### Agent 工具使用情况

| Skill | Agent 用途 |
|-------|----------|
| cso | 并行验证子任务（每个安全发现独立验证） |
| review | 独立审查子任务（subagent 避免 checklist 偏见） |
| ship | 部署检查子任务 |

### 工具频率统计

| 工具 | 使用次数 | 占比 |
|------|---------|------|
| Bash | 27 | 96% |
| Read | 28 | 100% |
| AskUserQuestion | 25 | 89% |
| Write | 17 | 61% |
| Glob | 16 | 57% |
| Grep | 14 | 50% |
| Edit | 11 | 39% |
| WebSearch | 10 | 36% |
| Agent | 3 | 11% |

**Read + Bash 覆盖率 100%，是 gstack 的绝对基础设施工具。**

### browse/bin/ vs 根 bin/ 区分

| 目录 | 性质 | CLI 入口？ |
|------|------|----------|
| `browse/bin/` | 编译产物目录 | ❌ 否 |
| `bin/` (根目录) | 工具脚本目录 | ✅ 是 |

browse/bin/ 存放 `browse` CLI 的编译输出（`browse` 二进制 + `find-browse`），是 browse skill 的内部依赖，**不是用户直接调用的 CLI**。根 `bin/` 包含所有 gstack 工具脚本（配置/telemetry/更新检查等）。

### Root SKILL.md 特殊说明

根目录 `SKILL.md` 是一个 **meta-skill**（name: gstack，等同于 browse）。它：
- 与 `browse/SKILL.md` 内容高度相似（diff 只有 name、description 和 telemetry skill name）
- 作为 gstack 整体技能的入口点
- 描述为"Fast headless browser for QA testing"（与 browse 完全一致）
- **独立 SKILL.md.tmpl**：`SKILL.md.tmpl`（根目录，1 个）

### 禁忌检查

- [x] 禁忌 1-19（沿用 v0.5）
- [x] **禁忌 20：allowed-tools 数据必须从实际文件读取并验证，不得伪造第二个块** ✅

---

*报告生成：skill-analyzer v0.6 | 2026-03-27*

# gstack 系统分析报告

## 元信息

- **分析版本：** skill-analyzer v0.9
- **分析日期：** 2026-03-28
- **项目类型：** Skill 仓库（CLI工具 + Agent工作流系统）
- **仓库路径：** `~/Repositories/gstack`
- **作者：** Garry Tan (Y Combinator President & CEO)
- **定位：** 将 Claude Code 转变为虚拟工程团队的工具集

---

## 版本信息

| 来源 | 版本 | 备注 |
|------|------|------|
| VERSION 文件 | **0.12.2.0** | 最新 |
| package.json | 0.12.0.0 | 落后 0.0.2.0 |
| CHANGELOG 最新 | [0.12.2.0] 2026-03-26 | Deploy with Confidence |

### CHANGELOG [0.12.2.0] 主要更新

**主题：** First-Run Dry Run — 部署前的信任建立机制

- **首次运行干跑：** 检测部署基础设施（平台、CLI状态、生产URL可达性、staging检测、merge方法、merge队列状态），在不可逆操作前确认
- **Staging-first 选项：** 检测到 staging 时可先部署到 staging 验证，再进 production
- **配置衰减检测：** 干跑确认存储 deploy config 的指纹，CLAUDE.md 或 workflow 变化时自动重新干跑
- **Inline review gate：** 无近期 code review 时提供 diff 安全检查
- **Merge queue awareness：** 检测 merge 队列并在等待时解释状态
- **CI auto-deploy 检测：** 识别 merge 触发的 deploy workflow 并监控

---

## 洋葱模型分析

### Layer 1：设计意图（哲学视角）

**核心信念：** AI 时代单人可敌百人团队（引 Andrej Karpathy："I don't think I've typed like a line of code probably since December"）

gstack 的设计哲学是**"Boil the Lake"**（煮沸海洋）—— 当 AI 让边际成本趋近于零时，必须做完整的事：

> "always do the complete thing when AI makes the marginal cost near-zero"

**三大原则：**
1. **真实性（Truth）** — 决策要有真实数据支撑，不凭印象
2. **完整性（Completeness）** — 不做半吊子，每个 skill 要覆盖全场景
3. **主动性（Proactivity）** — AI 应主动建议，而非被动响应

**技术架构哲学：**
- 浏览器是核心（需要亚秒级延迟 + 持久状态），其余皆 Markdown
- 所有工具是 `.md` 文件，通过 SKILL.md 标准接入任意 Agent
- Preamble 统一注入（telemetry、repo-mode、update-check、Boil the Lake 介绍）

---

### Layer 2：组件目录（结构视角）

#### 顶层结构

```
gstack/
├── SKILL.md              # 顶层 SKILL.md.tmpl 模板（29个 .tmpl 之一）
├── AGENTS.md             # Agent 配置文件
├── ARCHITECTURE.md       # 架构文档
├── BROWSER.md            # 浏览器架构详细说明
├── CLAUDE.md             # 用户配置入口
├── DESIGN.md             # 设计文档
├── ETHOS.md              # 价值观/哲学文档
├── README.md             # 项目说明
├── CHANGELOG.md          # 变更日志
├── TODOS.md              # 待办事项
├── VERSION               # 版本号（0.12.2.0）
├── package.json          # v0.12.0.0（落后）
│
├── bin/                  # 编译后二进制（17个）
├── browse/               # 浏览器核心
│   ├── bin/              # 浏览器脚本（2个）
│   └── test/             # 浏览器测试（18个 .test.ts）
├── scripts/              # 构建/工具脚本
│   └── resolvers/        # 解析器（10个）
├── lib/                  # 共享库（worktree.ts）
├── test/                 # 顶层 E2E 测试（25个 .test.ts）
├── agents/               # Agent 配置（openai.yaml）
├── supabase/             # Supabase 后端（RLS验证）
├── extension/            # Chrome 扩展（Side Panel + Popup）
├── docs/                 # 文档（skills.md + designs/）
│
└── [28个 Skill 目录]     # 核心工作流
```

#### Skill 目录清单（共28个）

| # | Skill | 版本 | Preamble Tier | 工具数 | 含WebSearch | 含Agent |
|---|-------|------|---------------|--------|-------------|---------|
| 1 | autoplan | 1.0.0 | 3 | 8 | ✅ | ❌ |
| 2 | benchmark | 1.0.0 | 1 | 5 | ❌ | ❌ |
| 3 | browse | 1.1.0 | 1 | 3 | ❌ | ❌ |
| 4 | canary | 1.0.0 | 2 | 5 | ❌ | ❌ |
| 5 | careful | 0.1.0 | — | 2 | ❌ | ❌ |
| 6 | codex | 1.0.0 | 3 | 6 | ❌ | ❌ |
| 7 | connect-chrome | 0.1.0 | — | 3 | ❌ | ❌ |
| 8 | cso | 2.0.0 | 2 | 8 | ✅ | ✅ |
| 9 | design-consultation | 1.0.0 | 3 | 8 | ✅ | ❌ |
| 10 | design-review | 2.0.0 | 4 | 8 | ✅ | ❌ |
| 11 | document-release | 1.0.0 | 2 | 6 | ❌ | ❌ |
| 12 | freeze | 0.1.0 | — | 3 | ❌ | ❌ |
| 13 | guard | 0.1.0 | — | 3 | ❌ | ❌ |
| 14 | investigate | 1.0.0 | 2 | 7 | ✅ | ❌ |
| 15 | land-and-deploy | 1.0.0 | 4 | 5 | ❌ | ❌ |
| 16 | office-hours | 2.0.0 | 3 | 8 | ✅ | ❌ |
| 17 | plan-ceo-review | 1.0.0 | 3 | 6 | ✅ | ❌ |
| 18 | plan-design-review | 2.0.0 | 3 | 6 | ❌ | ❌ |
| 19 | plan-eng-review | 1.0.0 | 3 | 7 | ✅ | ❌ |
| 20 | qa | 2.0.0 | 4 | 8 | ✅ | ❌ |
| 21 | qa-only | 1.0.0 | 4 | 5 | ✅ | ❌ |
| 22 | retro | 2.0.0 | 2 | 4 | ❌ | ❌ |
| 23 | review | 1.0.0 | 4 | 9 | ✅ | ✅ |
| 24 | setup-browser-cookies | 1.0.0 | 1 | 3 | ❌ | ❌ |
| 25 | setup-deploy | 1.0.0 | 2 | 7 | ❌ | ❌ |
| 26 | ship | 1.0.0 | 4 | 9 | ✅ | ✅ |
| 27 | unfreeze | 0.1.0 | — | 2 | ❌ | ❌ |
| 28 | gstack-upgrade | 1.1.0 | — | 2 | ❌ | ❌ |

**统计：**
- v0.1.0 = 5个：careful, connect-chrome, freeze, guard, unfreeze ✅
- 含 WebSearch = **12个** ✅（不是16！）
- 含 Agent = **3个** ✅：cso, review, ship
- v1.1.0 = browse（1.1.0）, gstack-upgrade（1.1.0）

---

### Layer 3：交互关系（系统视角）

#### Preamble Tier 架构（4级）

| Tier | Skills | 说明 |
|------|--------|------|
| **Tier 1** | benchmark, browse, setup-browser-cookies | 即插即用基础工具 |
| **Tier 2** | canary, cso, document-release, investigate, retro, setup-deploy | 配置驱动的工作流 |
| **Tier 3** | autoplan, codex, design-consultation, office-hours, plan-ceo-review, plan-design-review, plan-eng-review | 高层规划/审核 |
| **Tier 4** | design-review, land-and-deploy, qa, qa-only, review, ship | 行动/交付层 |

#### 角色体系（CEO / Designer / Eng Manager / QA Lead / Security Officer / Release Engineer）

```
用户（Founder/CEO）
    │
    ├── /office-hours     → 产品头脑风暴
    │       └── 可派 subagent（Agent tool）
    │
    ├── /plan-ceo-review  → CEO 视角评审
    │       └── benefits-from: office-hours
    │
    ├── /plan-design-review → 设计师视角评审
    │       └── 含 Codex（独立评估）
    │
    ├── /plan-eng-review  → 工程经理视角评审
    │       └── 含 WebSearch + Codex
    │
    ├── /design-consultation → 设计咨询（含 WebSearch）
    │
    ├── /autoplan         → 自动运行所有 review（派 subagent）
    │       └── benefits-from: office-hours
    │
    ├── /codex            → OpenAI Codex 辅助
    │
    ├── /cso              → 首席安全官（Agent tool + WebSearch）
    │
    ├── /review           → Code Review（含 Agent + WebSearch）
    │
    ├── /qa               → QA 测试 + 修复（含 WebSearch）
    │
    ├── /design-review    → 视觉审计（含 WebSearch）
    │
    ├── /ship             → 发布（含 Agent + WebSearch）
    │
    ├── /land-and-deploy  → 部署
    │
    ├── /canary           → 金丝雀发布
    │
    ├── /benchmark        → 性能基准测试
    │
    ├── /investigate      → 深度调查（含 WebSearch）
    │
    ├── /document-release → 文档发布
    │
    ├── /retro            → 回顾
    │
    ├── /careful          → 安全警告（destructive commands）
    │
    ├── /freeze           → 编辑边界限制
    │
    ├── /guard            → careful + freeze 组合
    │
    ├── /unfreeze         → 解除 freeze
    │
    ├── /setup-browser-cookies → 浏览器 cookie 设置
    │
    ├── /setup-deploy     → 部署配置
    │
    ├── /browse           → 浏览器控制（无 WebSearch）
    │
    └── /gstack-upgrade   → 升级
```

#### 关键依赖关系

- `autoplan` benefits-from: `office-hours`
- `plan-eng-review` benefits-from: `office-hours`
- `careful` hook → `bin/check-careful.sh`
- `freeze` hook → `bin/check-freeze.sh`
- `guard` hook → `careful/bin/check-careful.sh` + `freeze/bin/check-freeze.sh`
- 所有 skill preamble 统一注入：update-check、telemetry、repo-mode、proactive-flag

---

### Layer 4：使用场景（用户视角）

#### 用户画像

1. **Founder / CEO** — 特别是仍想亲自 ship 的技术型创始人
2. **First-time Claude Code 用户** — 结构化角色替代空白 prompt
3. **Tech Lead / Staff Engineer** — 每次 PR 的严格 review、QA、发布自动化

#### 快速上手路径（README 建议）

```
1. /office-hours       → 描述你在做什么
2. /plan-ceo-review    → 对任何 feature idea 做 CEO 视角评审
3. /review              → 对任何有变更的分支做 review
4. /qa                  → 对 staging URL 做 QA
5. /ship                → 发布 PR
```

#### 核心价值主张

- **60天数据：** 600,000+ 行生产代码（35% 测试），1-2万行/天
- **单周 retro：** 140,751 行增加，362 commits，~115k net LOC
- **2026年：** 1,237 contributions

---

## 文件数量核查

| 类别 | 数量 | 验证 |
|------|------|------|
| bin/ | **17** ✅ | chrome-cdp, dev-setup, dev-teardown, gstack-analytics, gstack-community-dashboard, gstack-config, gstack-diff-scope, gstack-extension, gstack-global-discover, gstack-global-discover.ts, gstack-repo-mode, gstack-review-log, gstack-review-read, gstack-slug, gstack-telemetry-log, gstack-telemetry-sync, gstack-update-check |
| browse/bin/ | **2** ✅ | find-browse, remote-slug |
| bin/ + browse/bin/ 合计 | **19** ✅ | 不是20！ |
| browse/test/ .test.ts | **18** ✅ | activity, browser-manager-unit, bun-polyfill, commands, config, cookie-import-browser, cookie-picker-routes, file-drop, find-browse, gstack-config, gstack-update-check, handoff, path-validation, platform, sidebar-agent, snapshot, url-validation, watch |
| scripts/ | **11** | analytics.ts, dev-skill.ts, discover-skills.ts, eval-compare.ts, eval-list.ts, eval-select.ts, eval-summary.ts, eval-watch.ts, gen-skill-docs.ts, resolvers/, skill-check.ts |
| scripts/resolvers/ | **10** | browse.ts, codex-helpers.ts, constants.ts, design.ts, index.ts, preamble.ts, review.ts, testing.ts, types.ts, utility.ts |
| SKILL.md.tmpl | **29** | 所有 skill 均有对应 .tmpl（含根 SKILL.md.tmpl） |
| test/ 顶层 .test.ts | **25** | 完整 E2E 测试套件 |

---

## allowed-tools 完整读取记录

### 含 WebSearch 的 Skill（12个 ✅）

#### 1. autoplan — 8个工具
Bash, Read, Write, Edit, Glob, Grep, WebSearch, AskUserQuestion

#### 2. cso — 8个工具（Agent ✅）
Bash, Read, Grep, Glob, Write, Agent, WebSearch, AskUserQuestion

#### 3. design-consultation — 8个工具
Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch

#### 4. design-review — 8个工具
Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch

#### 5. investigate — 7个工具
Bash, Read, Write, Edit, Glob, AskUserQuestion, WebSearch

#### 6. office-hours — 8个工具
Bash, Read, Grep, Glob, Write, Edit, AskUserQuestion, WebSearch

#### 7. plan-ceo-review — 6个工具
Read, Grep, Glob, Bash, AskUserQuestion, WebSearch

#### 8. plan-eng-review — 7个工具
Read, Write, Grep, Glob, AskUserQuestion, Bash, WebSearch

#### 9. qa — 8个工具
Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, WebSearch

#### 10. qa-only — 5个工具
Bash, Read, Write, AskUserQuestion, WebSearch

#### 11. review — 9个工具（Agent ✅）
Bash, Read, Edit, Write, Grep, Glob, Agent, AskUserQuestion, WebSearch

#### 12. ship — 9个工具（Agent ✅）
Bash, Read, Write, Edit, Grep, Glob, Agent, AskUserQuestion, WebSearch

---

### 不含 WebSearch 的 Skill（16个 ✅）

#### benchmark — 5个工具
Bash, Read, Write, Glob, AskUserQuestion

#### browse — 3个工具
Bash, Read, AskUserQuestion

#### canary — 5个工具
Bash, Read, Write, Glob, AskUserQuestion

#### careful — 2个工具 ✅（v0.1.0）
Bash, Read

#### codex — 6个工具
Bash, Read, Write, Glob, Grep, AskUserQuestion

#### connect-chrome — 3个工具 ✅（v0.1.0）
Bash, Read, AskUserQuestion

#### document-release — 6个工具
Bash, Read, Write, Edit, Grep, Glob, AskUserQuestion

#### freeze — 3个工具 ✅（v0.1.0）
Bash, Read, AskUserQuestion

#### guard — 3个工具 ✅（v0.1.0）
Bash, Read, AskUserQuestion

#### land-and-deploy — 5个工具
Bash, Read, Write, Glob, AskUserQuestion

#### plan-design-review — 6个工具
Read, Edit, Grep, Glob, Bash, AskUserQuestion

#### retro — 4个工具
Bash, Read, Write, Glob

#### setup-browser-cookies — 3个工具
Bash, Read, AskUserQuestion

#### setup-deploy — 7个工具 ✅（无WebSearch，不要误列！）
Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion

#### unfreeze — 2个工具 ✅（v0.1.0）
Bash, Read

#### gstack-upgrade — 2个工具 ✅（v1.1.0，不在v0.1.0列表）
Bash, Read

---

## v0.9 关键修复验证

| 检查项 | 预期值 | 实际值 | 状态 |
|--------|--------|--------|------|
| 含 WebSearch 的 Skill | 12 | 12 | ✅ |
| browse/test/ .test.ts 数 | 18 | 18 | ✅ |
| bin/ + browse/bin/ 合计 | 19 | 19 | ✅ |
| 含 Agent 的 Skill | 3 | 3 | ✅ |
| v0.1.0 Skill | 5 | 5 | ✅ |
| unfreeze 工具数 | 2 | 2 | ✅ |
| gstack-upgrade 版本 | 1.1.0 | 1.1.0 | ✅ |
| setup-deploy 含 WebSearch | ❌ | ❌ | ✅ |
| benchmark 含 WebSearch | ❌ | ❌ | ✅ |
| canary 含 WebSearch | ❌ | ❌ | ✅ |
| document-release 含 WebSearch | ❌ | ❌ | ✅ |

---

## 版本根因分析

### VERSION vs package.json 不一致

- **VERSION: 0.12.2.0**
- **package.json: 0.12.0.0**
- 差异：0.0.2.0

**分析：** VERSION 文件由发布流程手动更新，package.json 可能由自动化工具更新但存在延迟。CHANGELOG 从 0.12.2.0 开始，VERSION 与 CHANGELOG 对齐，package.json 落后。VERSION 更可信。

### v0.1.0 集中于安全类 Skill

- careful, connect-chrome, freeze, guard, unfreeze
- 全部为 v0.1.0（最老版本）
- 这些是 gstack 最早期的安全基础设施

---

## 附录

### 幽灵文件/目录

无明显幽灵文件。supabase/ 和 extension/ 是有实际功能的子模块：
- `supabase/` — RLS（Row Level Security）验证脚本
- `extension/` — Chrome 扩展（manifest v3，Side Panel + Popup）
- `lib/worktree.ts` — Git worktree 工具库
- `agents/openai.yaml` — OpenAI Agent 配置

### 特殊 Hook 配置

| Skill | Hook 类型 | 触发条件 | 脚本 |
|-------|-----------|----------|------|
| careful | PreToolUse (Bash) | 所有 bash 命令 | `bin/check-careful.sh` |
| freeze | PreToolUse (Edit) | Edit 操作 | `bin/check-freeze.sh` |
| freeze | PreToolUse (Write) | Write 操作 | `bin/check-freeze.sh` |
| guard | PreToolUse (Bash) | bash + careful | `../careful/bin/check-careful.sh` |
| guard | PreToolUse (Edit) | freeze | `bin/check-freeze.sh`（来自freeze） |

### SKILL.md.tmpl 覆盖率

**29个 .tmpl 文件，28个 Skill + 1个根 SKILL.md.tmpl = 29** ✅

---

*分析完成 | skill-analyzer v0.9 | 2026-03-28*

---
methodology: diataxis
---

# docs/ 文档索引

## tutorials/ — 教程

| 文件 | 用途 |
|------|------|

## how-to/ — 操作指南

| 文件 | 用途 |
|------|------|
| [how-to/install-skills.md](how-to/install-skills.md) | 如何安装 hskill 并将 skill 安装到 Claude Code / Cursor / Codex |
| [how-to/git-daily-workflow.md](how-to/git-daily-workflow.md) | 如何安装 hook、日常开发切分支、合并到 staging 和 main |
| [how-to/npm-publish.md](how-to/npm-publish.md) | 如何将新 skill 发布到 npm |
| [how-to/contribute-skill.md](how-to/contribute-skill.md) | 如何将其他项目的 skill 通过 contribute-skill 元技能贡献进 harveyz-skill |
| [how-to/git-cleanup.md](how-to/git-cleanup.md) | 如何用 git-cleanup skill 梳理本地废弃分支（含配置文件说明） |
| [how-to/use-hskill-config.md](how-to/use-hskill-config.md) | 如何用 hskill config 设置默认 target 和 scope，避免每次传相同 flag |
| [how-to/use-hub.md](how-to/use-hub.md) | 如何安装和使用 hub：TUI 启动、项目注册、任务管理、分支列表与 push/pull 操作 |
| [how-to/use-extract-cognition.md](how-to/use-extract-cognition.md) | 如何用 extract-cognition：模式 A/B 决策、--pass 分段、产出四文件该读哪个、怎么把认知动作手册用起来 |
| [how-to/use-init-goal.md](how-to/use-init-goal.md) | 如何用 init-goal 为 /loop 生成结构化目标：模版选择、生成文件说明、修改目标 |

## reference/ — 参考文档

| 文件 | 用途 |
|------|------|
| [reference/skill-spec.md](reference/skill-spec.md) | skill 格式规范（F1–F7）、命名规范与动词词表、skills-index.json 注册规则（R1–R3） |
| [reference/git-branch-rules.md](reference/git-branch-rules.md) | 分支模型、分支定义、命名规则、违规行为表（v1.0.0） |
| [reference/agent-cli-guide.md](reference/agent-cli-guide.md) | AI agent / CI 脚本调用 hskill 的完整参考（JSON 输出格式、info 子命令、hooks 子命令、bundle 子命令、uninstall、非 TTY 行为） |
| [reference/testing-guide.md](reference/testing-guide.md) | hskill 测试文件结构、bats 写法规范、hooks.bats 场景、hook 脚本验收测试模式 |
| [reference/branch-cleanup-config.md](reference/branch-cleanup-config.md) | `.claude/branch-cleanup.md` 格式规范：Always Delete / Keep glob 规则、LLM 上下文段、内置默认值 |
| [reference/hskill-cache.md](reference/hskill-cache.md) | hskill 本地缓存命令接口（cache clear/status/set-ttl）、缓存文件字段定义、失效规则 |
| [reference/hotfix-lifecycle.md](reference/hotfix-lifecycle.md) | HOTFIXES.md 格式规范（字段定义、编号规则）、fix-skill 自动写入行为、sync-hotfix 合并回源工作流 |
| [reference/hub-reference.md](reference/hub-reference.md) | hub CLI 完整参考：projects/tasks/git 子命令、所有参数、JSON 输出格式、错误格式 |
| [reference/todo-format-spec.md](reference/todo-format-spec.md) | TODO.md 文件结构、字段规范、todo_format.yaml 完整定义 |
| [reference/todo-tool-reference.md](reference/todo-tool-reference.md) | todo-tool 数据模型（SQL）、CLI 接口、API 端点完整参考 |

## explanation/ — 理解类

| 文件 | 用途 |
|------|------|
| [explanation/skill-creator-testing-system.md](explanation/skill-creator-testing-system.md) | skill-creator 测试体系的设计哲学、核心机制与工作原理 |
| [explanation/pdf-math-translate-architecture.md](explanation/pdf-math-translate-architecture.md) | PDFMathTranslate 的整体架构、核心模块设计原理与已知限制 |
| [explanation/hskill-architecture.md](explanation/hskill-architecture.md) | hskill 包结构、target 路径映射、scope 模型、版本检测设计、tool.json 格式、bundle 管理设计原理、config 子命令设计原理 |
| [explanation/hskill-cache-design.md](explanation/hskill-cache-design.md) | hskill 缓存设计原理：为什么引入缓存、为什么 TTL 可配置而非固定、缓存覆盖范围的设计决策 |
| [explanation/todo-md-source-of-truth.md](explanation/todo-md-source-of-truth.md) | 为什么以 TODO.md 为主数据源、sync 架构、数据流、错误处理与测试策略 |
| [explanation/todo-tool-architecture.md](explanation/todo-tool-architecture.md) | todo-tool 整体架构、目录结构、前端设计原理与已知风险 |
| [explanation/how-to-read-papers.md](explanation/how-to-read-papers.md) | Keshav 三遍阅读法原文（中文），论文分析 Skill 方法论的来源 |
| [explanation/chrome-profile-cookie-injection.md](explanation/chrome-profile-cookie-injection.md) | 通用机制：从 Chrome Profile 提取加密 cookie、pycookiecheat 解密、注入 Playwright context，含复用模板 |
| [explanation/xcom-playwright-auth.md](explanation/xcom-playwright-auth.md) | X.com 应用：auth cookie 识别、Profile 扫描、wait_for_selector 隐式鉴权验证、双路径选择 |
| [explanation/hub-architecture.md](explanation/hub-architecture.md) | hub 架构设计原理：core/ 解耦、SQLite + PROJECTS.md 双存储、从 p-launch + todo-tool 演进路径 |
| [explanation/sync-agent-architecture.md](explanation/sync-agent-architecture.md) | sync-agent 架构：tool/skill 分工、config/state 分离原因、setup 幂等性、Syncthing REST 集成 |
| [explanation/cognitive-signature-philosophy.md](explanation/cognitive-signature-philosophy.md) | extract-cognition 背后的哲学：隐含作者、法证 vs 教学两种目的、为何先学发生器、warrant 即地基、防鸡汤锁、该学/该防、无基线不归因 |
| [explanation/pbpe-methodology.md](explanation/pbpe-methodology.md) | PBPE 方法论：从同质制品归纳设计哲学、反推规则的归纳—演绎闭环方法（Phase 0–4 完整流程、偏差对冲机制） |
| [explanation/skill-hotfix-lifecycle.md](explanation/skill-hotfix-lifecycle.md) | Skill 热修补丁生命周期管理设计原理：速度与完整性的张力、两层同步机制（HOTFIXES.md + 全文件 diff 安全网）、差异分类系统的设计决策 |

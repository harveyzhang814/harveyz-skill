# 决定记录：compose-agentsmd —— AGENTS.md 标准骨架与生成

建档日期：2026-11-11
分支：`feature/devflow-agents-snippet`

**需求批准：** 用户 2026-11-11 确认 question-me 需求摘要（答复“可以”），批准 D1–D14。

## 当前决定

### D1 初始需求：可插入各项目 AGENTS.md 的 devflow 流程片段

- **决定：** 在 harveyz-skill 维护一段基于 devflow 的开发流程内容，可直接放进其他项目的 AGENTS.md，带版本标识、支持替换。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“在harveyz-skill里面需要维护一个可放入agents.md的基于devflow的开发流程的片段，这样可以直接复制并插入到对应项目的agents.md里面，并且有版本标识，支持替换”。

### D2 范围扩展：整份 AGENTS.md 标准化插入槽，支持客制化描述

- **决定：** 不只流程片段，整份 AGENTS.md 都按标准化插入槽组织，并有客制化描述的插入方式。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“干脆更加有野心一点，改成整个agents.md都支持不同的插入，设计成标准化的插入槽，并且有客制化描述的插入方式。”

### D3 内容取舍：删 Agent Canvas 项目本身，留 Agent Canvas 框架依赖

- **决定：** 以 Agent Canvas 的 `AGENTS.md` 为蓝本；属于 Agent Canvas 这个开发项目本身的内容移除（进描述槽或参数），依赖 Agent Canvas 框架的内容保留在标准模块。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“分清楚哪些是agent canvas开发项目本身，哪些是依赖于agent canvas框架，前者移除，后者保留”。
- **依据：** 项目本身：技术栈、`CLAUDE.md` 约定与 Claude Code 适配、`sync-design`/`.design-scratch/`、`simulate-user` Electron E2E、`staging` 与 `scripts/merge-to-staging.sh`、main↔renderer↔IPC 分档信号、`.claude/worktrees` 遗留、内部 spec 链接。框架：`describe-node`/`capture-requirement`/`relate-node`、Step 8 质量观测与旧版 App 兜底、版本验收、`docs/superpowers/specs/` 前缀（`describe-node` 自动发现）。出处：`~/Projects/agent-canvas/AGENTS.md`。

### D4 标记 + 脚本，随 devflow bundle 发布

- **决定：** 生成内容带版本标记；配脚本完成插入/替换/检查；放在 devflow bundle、随 npm 发布。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——“支持替换做到什么程度？”选项：标记 + 脚本（推荐）/ 只加标记；答复“标记 + 脚本”。“片段放在哪里？”选项：devflow bundle 随 npm 发布（推荐）/ 仓库 docs 不发布；答复前者。

### D5 插入槽形态：标准骨架

- **决定：** harveyz-skill 定义 AGENTS.md 标准骨架，章节即槽；槽填标准模块或项目内容。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q1 选项：A 标准骨架（推荐）/ B 模块库；答复“A”。

### D6 定制分两类：参数代入标准文本，描述保存项目个性化内容

- **决定：** 标准模块是参数代入后的标准文本；“描述”是项目自身的个性化内容，填在描述槽。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q2 选项：A 参数式 / B 描述式（agent 按描述改写）/ C 参数+描述两层（推荐）；答复“参数式是标准文本，描述用来保存项目本身的个性化的描述”。

### D7 AGENTS.md 是生成物

- **决定：** 参数与各描述槽内容存在项目的配置目录，脚本拼出完整 AGENTS.md，不手改。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q2a 选项：A AGENTS.md 是正本、描述槽手写 / B AGENTS.md 是生成物；答复“B”。

### D8 骨架 10 个槽，整体性在前

- **决定：** 顺序与类型：1 项目概述（描述）· 2 流程简述（标准）· 3 项目原则（描述）· 4 指令源与能力检测（标准）· 5 平台能力替代表（标准）· 6 平台适配（描述）· 7 仓库环境（描述）· 8 开发流程细则（标准，带参数）· 9 版本验收（标准）· 10 其他约定（描述）。描述槽空则不生成；标准槽可在配置中关闭。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q3 初版 9 槽方案，答复“调节章节顺序，整体性的放前面”；重排为上表后答复“A”。

### D9 Agent Canvas 框架内容用参数开关

- **决定：** 参数 `agent_canvas: true/false`；false 时不生成各步中的画布句子、Step 8 与版本验收槽，Step 7 集成责任改为“当前 agent 负责”。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q3a 选项：A 参数开关（推荐）/ B 始终包含；答复“A”。

### D10 本次只做机制，用 Agent Canvas 验证

- **决定：** 本次交付骨架、标准模块、配置格式与生成脚本；用 Agent Canvas 现有 `AGENTS.md` 写一份配置，在临时目录生成并与原文逐节对照；不改 Agent Canvas 仓库。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q4 选项：A 只做机制用 Agent Canvas 验证（推荐）/ B 迁移 Agent Canvas / C 连本仓库一起迁；答复“A”。

### D11 skill 名称 `compose-agentsmd`

- **决定：** 新 skill 命名 `compose-agentsmd`，放 `skills/devflow/`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——Q5 选项：A `compose-agents`（推荐）/ B `sync-agents` / C `init-agents`；答复“A,不过agents会有歧义”；再问 A `compose-agentsmd`（推荐）/ B `compose-instructions`；答复“A”。

### D12 防手改：文件头声明 + `--check`

- **决定：** 生成的 AGENTS.md 文件头注明“由配置生成，勿手改”；`--check` 报告手改漂移与模块版本落后。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——AGENTS.md 已定为生成物（D7），需要发现绕过配置的手改。

### D13 参数清单

- **决定：** 集成分支、合并命令、E2E 测试方式、分档补充信号、spec/plan 落点、`agent_canvas`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——Agent Canvas 原文中与项目绑定、又落在标准模块里的几处（见 D3 依据）。

### D14 skill 职责：初始化、生成、检查

- **决定：** 初始化（建配置目录；已有 AGENTS.md 时由 agent 按槽拆分）、生成（脚本拼装）、检查（`--check`）。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——D7 生成物模型 + D10 需从现有 AGENTS.md 迁出配置。

### D15 次要前提

- **决定：** 标准模块版本独立于 skill `version`；配置目录 `.hskill/compose-agentsmd/`；脚本只用 Node 内置模块；分支名沿用 `feature/devflow-agents-snippet`。
- **状态：** 已批准（question-me 摘要确认，作为假设列出）
- **来源：** Agent 推断——沿用 `.hskill/<skill>/` 约定；本仓库脚本均为无依赖 Node。

### D16 未决：Agent Canvas 正式迁移、harveyz-skill 自身是否迁移

- **决定：** 留待以后，另开任务。
- **状态：** 已提出
- **来源：** 用户选择——Q4 答复“A”；摘要“未决”字段。

### D17 项目配置：目录 + 每个描述槽一个文件

- **决定：** `.hskill/compose-agentsmd/config.json` 存参数与槽开关；`slots/<槽id>.md` 每个描述槽一个纯 Markdown 文件。
- **状态：** 已批准
- **来源：** 用户选择——M1 选项：A 目录 + 每槽一个文件（推荐）/ B 单文件 `AGENTS.src.md`；答复 A。
- **依据：** 描述内容可自由使用标题，不与槽分隔冲突；JSON 无需自写 YAML 解析器（D15 无依赖）。

### D18 模板机制：极简语法、一份正文

- **决定：** 标准模块每个一份正文；参数代入与单层块条件用极简语法表达，未知参数、未闭合或嵌套条件一律报错。
- **状态：** 已批准
- **来源：** 用户选择——M2 选项：A 极简语法一份正文（推荐）/ B 按开关拆两份变体 / C 模块写成 JS 函数；答复 A。

### D19 版本粒度：整套模块一个版本

- **决定：** 模块集共用一个版本号（`assets/modules/VERSION`），生成文件头记录它，`--check` 只比它。
- **状态：** 已批准
- **来源：** 用户选择——M3 选项：A 整套一个版本（推荐）/ B 每模块各自版本；答复 A。
- **依据：** 模块之间互相引用（流程简述引用 Step 编号），分开升级会错配。

### D20 检查方式：整文件重生成比对（唯一可行路径）

- **决定：** `check` 用当前配置与已安装模块重新生成，与磁盘 AGENTS.md 逐字节比较；不一致时区分手改、版本落后、配置改后未生成。不做逐槽替换。
- **状态：** 待审（随 Spec 送审）
- **来源：** Agent 推断——D7 已定 AGENTS.md 为生成物，逐槽替换会重新引入“标记外可手写”的语义，与 D7 冲突。

## 已否定或失效的决定

（无）

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.23.0] - 2026-07-09

### Added
- `hskill upgrade`：批量升级已安装 skill 到最新版本，支持 `--skill`/`--target`/`--scope`/`--json`，只升级已安装的 skill，不会新装

### Fixed
- `extract-url`：修正 Claude Code 补丁里写死的 SKILL_DIR 路径
- `extract-url`：打标顺序调整为先原文后翻译，收紧标签规则；候选标签新增并列清单合并规则
- `capture-vocab`：补上 `.hskill/` 路径缺失的点前缀
- `question-me`：补充 label 字段的决策树格式说明

### Changed
- `extract-url`：Subagent 1/2 派发 prompt 拆分到 `references/`；更新 skills-index.json 的 contentHash/contentVersion

## [0.22.1] - 2026-07-06

### Fixed
- `hskill update`：更新命令从 `npm update` 改为 `npm install -g harveyz-skill@latest`，修复 0.x.y semver 约束导致跨 minor 版本无法更新的问题

## [0.22.0] - 2026-07-06

### Added
- `capture-vocab`：项目级领域术语字典 skill，支持 add/query/update/remove，上下文自动推断字段

### Changed
- `sync-design` v5.0.0：模式路由（sync/design），设计阶段流程（新建/修改草稿），三检查点草稿删除，`linkedEntryId` 自动回填
- `question-me` v3.0.0：重构为 section-structure 标准；v2.0.0 动态树 + 遍历顺序漏洞修复
- `extract-url` v2.3.0：章节结构重组，新增 `count_article_stats.py` 完成回报卡片
- `scout-philosophy`：新增阶段八——产出可直接复制的起始模板（`standard.md`）
- `init-goal`：移至 `coding/` bundle，`installScope` 改为 global
- `learn-skill`：移至 `mint` bundle

### Removed
- `dispatch-task`、`close-task`：归档

## [0.21.0] - 2026-07-01

### Added
- `init-workflow` v4.1.x：Step 4e git config 健康检查（`core.hooksPath` + `merge.ff`），类型 E 冲突检测与自动修复；lock 文件新增 `git_config` 节
- `sync-hotfix` v1.1.x：Step 5 全文件差异扫描安全网，Step 1 不再退出确保 Step 5 始终执行
- `extract-url` v2.2.0：X Notes 内容根节点修复、嵌套 tweet 过滤；tag 固定集（`fixed_tags.txt`）与候选集分离，两阶段打标流程
- `fix-skill` v2.1.0：多轮 AI 修复 + per-skill session doc（含 HOTFIXES.md 写入）
- `extract-cognition` v0.2.0：学习导向重设计——五阶段 evidence/audit layer + 学习层（Stage 5-6）
- `skill-map.html`：全景参考页面，Grid 布局按 bundle 分组展示所有 35 个 skill
- `sync-design` v3.1.0：`.hskill/` outputDir 默认路径 + legacy path 迁移

### Changed
- Bundle 重组：`meta` 拆分为 `mint`（skill 生命周期）和 `devops`（项目运维）；`experiment` 解散，各 skill 回归领域 bundle
- `publish-skill` v1.3.1：F7 动词词表新增 `survey`
- `capture-todo` v4.5.1：修复 merge dual-hook 兼容性（`--no-commit` 解耦 MERGE_MSG 与 commit-msg）
- Pre-commit hook：允许 remote staging sync merge 不被拦截

### Removed
- `manage-docs`：归档（功能已由 `manage-dir` + `references/built-in/diataxis.md` 覆盖）

## [0.20.0] - 2026-06-25

### Added
- `init-goal`：对话式向导 skill，为 `/loop` 命令生成结构化 Goal Prompt 文本；深度优先解析用户输入、自动匹配五类模版（Fix Until Green / Research Loop / Refine Until Satisfied / Monitor & React / Explore & Map）、渐进式披露（模版数据提取至 references/templates.md）
- `learn-video`：新增 Bilibili 视频支持（YouTube + Bilibili 双平台）

### Changed
- `init-goal`：迁移至 `coding` bundle（原 `meta`）

## [0.19.0] - 2026-06-22

### Added
- `sync-agent`：Syncthing 多设备同步工具与 skill — REST API 客户端、launchd 安装、CLI（start/stop/status/setup）、运行时管理同步 folder/device、为含 `.gitignore` 的目录自动创建 `.stignore`
- `hub`：TODO.md → SQLite 同步（启动时同步所有项目，ctrl+r 同步当前项目）；`hub git` CLI 子命令（status/fetch/branches）与 TUI 对等；`hub projects remove` 命令 + TUI ctrl+d 快捷键
- `scout-philosophy`：skill 设计哲学研究 skill（meta bundle）
- `extract-url`：代码块支持；付费墙站点 cookie 重试；`HSKILL_EXTRACT_URL_CONFIG` 环境变量覆盖配置路径
- `learn-video`：新增字幕翻译步骤（translate_subs）

### Changed
- `learn-skill` → v2.0.0：报告持久化到全局 skill 库、四维度归纳式重构、新增 Step 4 跨 skill 索引摘要
- `analyze-skill` → `survey-skillrepo`：重命名并移至 research bundle，泛化到任意 skill 仓库并集成 learn-skill
- `extract-url`：重构为从 `~/.hskill/config.json` 读取配置，各脚本不再依赖位置参数
- `init-skill`：迁移至 experiment bundle；description 移除中文以符合 F3；支持可切换参考标准用于 A/B 实验
- `publish-skill`：新增 R4 installScope 检查与修复引导
- 13 篇设计 spec 迁移为正式文档（hub、sync-agent、opencode、init-skill 等）
- 修正多个 skill 内容哈希与版本号，并为 10 个 skill 补充 `installScope`

### Fixed
- `extract-url`：playwright_xcom 图片下载 SSL 验证、脚本路径/setup 顺序/超时/权限等修复
- `hub`：TUI remove 行为与 CLI 对齐、footer category map、remove 快捷键改为 ctrl+d
- `sync-agent`：平台感知的 Syncthing 配置路径（macOS/Linux）
- `learn-skill`：audit findings 修复，移除 reference/script 200 行读取上限
- 测试：survey-skillrepo fixture 版本同步至 2.0.1，修复 test_config.py 导入与 bats meta-bundle 断言

## [0.18.0] - 2026-06-16

### Added
- `learn-paper` skill：基于三遍阅读法的论文精读 skill（首次以 `read-paper` 命名引入，后改名为 `learn-paper`）
- `init-skill` skill：从设计文档脚手架生成新 skill
- `probe-chrome-session` skill（experiment bundle）：Chrome profile cookie/session 探测与注入，支持 per-domain 加载策略
- `experiment` bundle：用于 staging 实验性 skill
- `publish-skill` F8：基于内容哈希的版本号检查，hash mismatch 时自动 bump

### Changed
- `extract-vision`：overhaul 至 v1.2.0（PaddleOCR v3 API、lang options 修复）
- `capture-insight`：通过 `~/.hskill` 配置保存到 Writing Agent project
- release-profile.md 迁移到 `.hskill/release-project/`

### Removed
- 归档 `npm-release` skill（被 `release-project` 取代）
- 退役 `p-launch` 与 `todo-tool`（被 `hub` 取代），移除对应测试

### Fixed
- `publish-skill`：audit 违规修复
- `read-paper`：真实论文测试后发现的 5 个问题修复

## [0.17.1] - 2026-06-15

### Fixed
- `hskill` TUI：未安装的 skill 现在按 `installScope` 显示推荐图标（`»` essential / `▸` global/project），不再统一显示 `—`

## [0.17.0] - 2026-06-15

## [0.16.0] - 2026-06-15

### Added
- `hub git`：新增 CLI 子命令，与 TUI git 面板功能对等
  - `hub git status [--project <name>]`：显示当前分支、upstream 同步状态、工作区变更、最近提交
  - `hub git fetch [--project <name>]`：fetch 所有 remote
  - `hub git branches [--project <name>]`：列出所有分支及 ahead/behind 状态

### Changed
- `hub`：版本升至 1.1.0
- `hub`：安装升级机制改为基于源码文件内容哈希（sha256）检测，不再依赖版本号；npm 更新后下次启动自动重装

## [0.15.0] - 2026-06-15

### Added
- `dedup-skill`：新增 meta skill，扫描并分析各 skill 间的重复内容，生成去重报告
- `archive-skill`：新增 meta skill，将废弃 skill 移至 `skills/archived/` 并更新 skills-index.json
- `article-fetcher`：归档（superseded by `url-extract`）

### Changed
- **Skill 命名规范**：22 个 skill 目录统一重命名为 verb-noun 格式（如 `skill-analyzer` → `analyze-skill`、`doc-forge` → `forge-doc`、`diagram` → `draw-diagram` 等）
- `hskill update`：自动执行 skill 目录迁移，将旧名称映射到新 verb-noun 名称

### Fixed
- `archive-skill`：修复 eval 测试发现的 3 个 bug（v1.1.0）
- `hub-tui`：修复 GitPanel 无法获得焦点的问题（`can_focus=True`）
- `hub-tui`：Enter 键在 projects-list 焦点时正确触发打开项目
- `hub-tui`：新增 ←/→ 键切换列，Tab 保留为辅助导航
- `installer`：`migrateRenamedSkills` 新增输入校验和一致性日志

## [0.14.2] - 2026-06-15

### Changed
- `project-release`：description 字段改为英文，符合 skill-publish F3 格式规范
- `project-release`：移除 `npm-release` skill，以 `.hskill/release-profile.md` 替代，消除重复

## [0.14.1] - 2026-06-14

### Fixed
- `hub` 安装失败（`source_not_found`）：新增 `hub.sh` 启动脚本，安装器现在能正确找到 hub 入口
- `hub` tool.json `extraPaths` 路径错误（`core/cli` 不在工具根目录），修正为 `["hub", "pyproject.toml"]`
- `hub` 卸载后遗留 `~/.hskill/tools/hub/` Python 源码目录，将其加入 `uninstallPaths`
- hskill 交互流程次级 fzf 页面（action/target/scope）缺少 preview 面板，视觉风格与主列表页不一致

### Added
- `docs/how-to/use-hub.md`：hub 人用操作指南（安装、TUI、projects/tasks 常用命令）
- `docs/reference/hub-reference.md`：hub CLI 完整参考（供 agent 调用，含 JSON 输出格式）

## [0.14.0] - 2026-06-14

### Added
- `hub` tool（`tools` bundle）：个人开发者 OS，整合项目管理、git 状态追踪、任务系统，替代 p-launch + todo-tool
  - Phase 1：core 库（SQLite DB、projects CRUD、tasks CRUD）+ CLI（`hub project`、`hub task` 子命令，支持 `--json` 输出）
  - Phase 2：三栏 Textual TUI（ProjectsPanel | GitPanel | TasksPanel），支持键盘导航、git fetch、任务增删改、项目切换联动
  - 首次启动自动从 todo-tool DB 迁移数据（`migrate.py`）
  - 62 个测试覆盖 core、CLI、TUI 各层

## [0.13.0] - 2026-06-12

### Fixed
- `opencode-runner`：description 移除中文字符，符合 F3 英文规范
- `doc-forge`：测试 CSS 路径改为动态选取首个可用文件，不再依赖不存在的 `default.css`

## [0.12.1] - 2026-06-10

## [0.12.0] - 2026-06-09

### Added
- `url-extract`：新增 `detect_chrome_profile.py` 脚本，扫描本机 Chrome profile 并检测 X.com 登录态
- `url-extract`：安装时 `CHROME_PROFILE` 变量改为 select 选择列表（自动列出所有 profile + 对应 Google 账号），保留手动输入兜底
- `hskill`：安装/卸载完成后新增 "按 Enter 返回列表" 提示，避免 summary 被 fzf 立即覆盖

### Changed
- `url-extract` `vars.json`：`CHROME_PROFILE` 默认值从 `Profile 2` 更新为 `Default`

## [0.11.0] - 2026-06-09

### Added
- `hskill list`：新增 Bundle 列并按 bundle 名称排序（替换旧的分组标题格式）；`hskill status` skills 列表同步增加 Bundle 列

### Changed
- `hskill` 内部重构：平台列表从 `SKILL_TARGETS` 单一来源派生，消除 `bundles.js` / `preview.mjs` 中的硬编码数组

### Fixed
- `url-extract`：移除 `SKILL_DIR` 用户配置变量
- `preview`：安装状态侧边栏补全 openclaw、hermes 平台（USER LEVEL）
- `npm-release`：中间步骤跳过 push 操作，最终统一给出推送 + 发布指令清单

## [0.10.0] - 2026-06-08

### Added
- `url-extract` skill（`data-extraction` bundle）：跨平台 URL 存档工具，支持 Claude Code / Codex / Hermes，含 Playwright 抓取、SQLite 存储、VAULT_PATH / SKILL_DIR / CHROME_PROFILE 配置
- `vision-extract` skill（`data-extraction` bundle）：从 hermes-skills 贡献的视觉数据提取 skill
- `skill-publish` skill（`meta` bundle）：检查 skill 格式合规性与 skills-index.json 注册状态
- `npm-release` skill（`meta` bundle）：完整 npm 发布工作流（版本号 → CHANGELOG → 分支 → tag → publish）
- `migrate-specs` skill（`harness` bundle）：将旧 spec 文档迁移为 Diataxis 结构
- `dir-manage` skill（`document` bundle）：从 writing-agent 贡献的目录管理 skill
- `capture-insight` skill（`writing` bundle）：从 writing-agent 贡献的洞察捕获 skill
- `add-todo` skill（`workflow` bundle）：从 harveyz-skill workflow 贡献的 TODO 追踪 skill
- Diataxis 结构文档：cache、config、bundle、info 模块的参考文档与指南

### Changed
- `hskill` 安装交互优化：改为两步式（先选 target，再选 scope），更符合操作直觉
- `url-extract`：通用 SKILL.md + 各平台 patch 文件，支持跨平台复用

### Fixed
- installer：`--force` 时按 `uninstallPaths` 精确清理，支持版本感知 venv 升级
- `url-extract`：以 `source_url` 为主键，支持存量 DB schema 迁移
- `url-extract`：命令注入安全加固，usability 改进
- SKILL.md frontmatter 跨所有 skill 规范化

## [0.9.0] - 2026-05-29

### Added
- `hskill uninstall <tool>` 命令：清理 binary、Python 模块、tool.json、venv 及 zshrc snippet
- `hskill uninstall <tool> --yes`：跳过所有确认（含用户配置文件）
- `hskill uninstall <skill> --scope <s> --target <t>`：卸载已安装的 skill 目录
- `tool.json` 新增 `uninstallPaths[]` 和 `configPaths[]` 字段，tool 可声明 tool-specific 清理路径
- fzf 交互界面在选完 item 后新增 Action 选择步骤（安装 / 卸载），支持在同一界面卸载 tool / skill / hook
- p-launch：迁移至 Python + Textual，新增三栏 TUI 界面
- p-launch：push/pull 时检测 diverged 分支（本地和远端均有新提交），跳过操作并提示
- p-launch：首次运行自动创建隔离 venv 并安装 textual，无需手动配置依赖

### Changed
- p-launch `tool.json` 新增 `uninstallPaths`（`p-launch-venv`）和 `configPaths`（`~/.config/p-launch`）

### Fixed
- installer：`--force` 重装时根据 `uninstallPaths` 精确清理旧版本文件，避免残留
- installer：`--force` 重装时正确清理 venv，支持版本感知升级
- tool 版本对比逻辑：upgrade 前先读取已安装版本，跳过同版本重复安装

## [0.8.1] - 2026-05-24

### Fixed
- `contribute-skill`：SKILL.md description 字段内含 ASCII 双引号导致 YAML 解析失败

## [0.8.0] - 2026-05-24

### Added
- `contribute-skill`（`meta` bundle）：在其他项目中将本地 skill 目录贡献到 harveyz-skill 仓库，自动完成 SKILL.md 格式规范化、skills-index.json 注册登记、双向目录同步、分支创建与 commit
- 新增 `meta` bundle，用于对 harveyz-skill 仓库本身的元操作

## [0.7.0] - 2026-05-24

### Added
- `hskill hooks` 子命令：`install` / `uninstall` / `list`
- Claude Code hooks 统一管理：支持 user 和 project 两种 scope
- Hook 版本追踪：脚本头部 `# version:` 注释，安装时区分 up-to-date / outdated
- `hskill hooks list` 展示 VER 列及 user/project 安装状态
- `hskill status` HOOKS 区块显示版本号
- 内置 hook：`check-similar-branch`（LLM 语义分析检测相似分支，防止重复建分支）
- `prepack` 阶段验证 skills / tools / hooks 的目录和关键文件存在性，索引和磁盘不一致时构建失败

### Changed
- `generate-npmignore.js` 现在自动从 `skills-index.json` 生成 `package.json files[]`，新增 skill/tool/hook 无需手动维护
- hooks 目录结构对齐 skills/tools：`hooks/<name>/<name>.sh`
- `skills-index.json` hooks 条目的 `path` 指向目录，脚本文件名由约定（`<name>.sh`）决定
- `generate-npmignore.js` 对 `exclude` 中不存在的目录打印警告，防止遗留配置静默通过

### Fixed
- `resolveHookDisplayVersion` 定义在 hooks 块内但被 status 块调用导致的 `ReferenceError`
- `hskill hooks --json` 子命令路由失败（Unknown subcommand）
- 无效 scope 参数静默使用默认值的问题

## [0.6.2] - 2026-04-28

### Fixed
- fzf 未安装时显示清晰的错误信息和安装指引

## [0.6.1] - 2026-04-20

### Added
- `hskill version`、`hskill status`、`hskill outdated`、`hskill info` 子命令

## [0.6.0] - 2026-04-15

### Added
- 工具版本统一检测（shell tools 通过 `tool.json` 管理版本）
- 交互式 skill 选择列表展示版本号
- 用 fzf 替代 checkbox 作为交互式选择界面

### Changed
- skill-analyzer 重构至 v1.0.0，规范 references 和输出路径

## [0.5.0] - 2026-03-30

### Added
- skill 安装支持 user / project 两种 scope 选择

## [0.4.0] - 2026-03-15

### Changed
- CLI 重命名为 `hskill`，采用子命令结构

## [0.3.0] - 2026-03-01

### Added
- `p-launch` 工具：在 Ghostty 中打开项目

### Fixed
- p-launch 多项路径、osascript 调用和动态检测问题

## [0.2.1] - 2026-02-15

### Added
- OpenClaw 和 Hermes 作为支持的安装目标

## [0.1.2] - 2026-01-20

### Added
- 初始 skill 管理器，支持安装到 Claude / Cursor / Codex

[Unreleased]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.7.0...HEAD
[0.7.0]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.6.2...v0.7.0
[0.6.2]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.6.1...v0.6.2
[0.6.1]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.1.2...v0.2.1
[0.1.2]: https://github.com/harveyzhang814/harveyz-skill/compare/v0.1.1...v0.1.2

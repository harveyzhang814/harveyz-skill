# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

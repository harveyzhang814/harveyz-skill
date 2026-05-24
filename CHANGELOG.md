# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

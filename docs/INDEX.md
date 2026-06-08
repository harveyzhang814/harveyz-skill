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

## reference/ — 参考文档

| 文件 | 用途 |
|------|------|
| [reference/git-branch-rules.md](reference/git-branch-rules.md) | 分支模型、分支定义、命名规则、违规行为表（v1.0.0） |
| [reference/agent-cli-guide.md](reference/agent-cli-guide.md) | AI agent / CI 脚本调用 hskill 的完整参考（JSON 输出格式、info 子命令、hooks 子命令、bundle 子命令、uninstall、非 TTY 行为） |
| [reference/testing-guide.md](reference/testing-guide.md) | hskill 测试文件结构、bats 写法规范、hooks.bats 场景、hook 脚本验收测试模式 |
| [reference/branch-cleanup-config.md](reference/branch-cleanup-config.md) | `.claude/branch-cleanup.md` 格式规范：Always Delete / Keep glob 规则、LLM 上下文段、内置默认值 |
| [reference/hskill-cache.md](reference/hskill-cache.md) | hskill 本地缓存命令接口（cache clear/status/set-ttl）、缓存文件字段定义、失效规则 |

## explanation/ — 理解类

| 文件 | 用途 |
|------|------|
| [explanation/skill-creator-testing-system.md](explanation/skill-creator-testing-system.md) | skill-creator 测试体系的设计哲学、核心机制与工作原理 |
| [explanation/pdf-math-translate-architecture.md](explanation/pdf-math-translate-architecture.md) | PDFMathTranslate 的整体架构、核心模块设计原理与已知限制 |
| [explanation/hskill-architecture.md](explanation/hskill-architecture.md) | hskill 包结构、target 路径映射、scope 模型、版本检测设计、tool.json 格式、bundle 管理设计原理、config 子命令设计原理 |
| [explanation/hskill-cache-design.md](explanation/hskill-cache-design.md) | hskill 缓存设计原理：为什么引入缓存、为什么 TTL 可配置而非固定、缓存覆盖范围的设计决策 |

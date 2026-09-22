# AGENTS.md 通用迁移设计

## 概述

新增仓库根目录 `AGENTS.md`，为支持 repository guidance 的 agent host 提供不绑定 Claude Code 的协作规则。保留现有 `CLAUDE.md` 原样，继续作为 Claude Code 的兼容入口和 Claude 专属说明来源。

## 目标

- 让 skill 的维护、发布、测试与 Git 规则可被不同 agent host 一致遵守。
- 保留可多平台部署的 skill，包括 `handoff`。
- 不把 Claude Code 的斜杠命令、工作区 API、配置目录或安装目录伪装成通用能力。

## 文档边界

`AGENTS.md` 是平台中立的主文档，包含：

- 本仓库是 `skills/` 的权威源，已安装副本不是编辑目标；部署必须从 `staging` 的归档内容进行。
- 安装器按 target 决定各 host 的安装目录；文档不假设 `~/.claude/skills/`。
- skill 目录、索引、测试和发布约定。
- 通用 Git 分支、worktree 和合并安全规则。
- `handoff` 作为通用 skill 的交接流程和平台适配要求。

`AGENTS.md` 不包含：

- `EnterWorktree`、`ExitWorktree` 或其他特定 host 的工具调用。
- `/handoff` 这类特定 host 的 slash-command 调用语法。
- `.claude/settings.json` 或某个 host 的 skill override 机制。
- 对某一 host 配置目录的通用化宣称。

## Worktree 与 handoff 规则

工作区协作的核心约束不依赖 host：从明确的 `staging` 基线创建分支；后续命令必须实际作用于指定 worktree；合并前核验当前分支；交接中由交出方创建并保留工作区，接手方不新建、不销毁，验收方回到同一工作区。

若 host 支持切换或绑定工作区，可以使用该能力；否则每条 Git 命令使用 `git -C <worktree>`，文件读写使用绝对路径。`.claude/worktrees/` 仅作为本仓库现有路径惯例和兼容目录，而非跨平台 API。

`handoff` 是通用 skill。支持 skill invocation 的 host 应调用它；不支持时须遵循其 `author`、`verify`、`self-test` 与 `accept` 流程，并读取 `.hskill/handoff/config.md`。同样，slash-command 只是可能的调用界面，不是流程定义。

## 验收

- `CLAUDE.md` 保持未修改。
- 根目录新增 `AGENTS.md`，不出现 Claude-only API 或 slash-command 作为必经机制。
- `AGENTS.md` 保留 `handoff` 的通用 skill 定位与跨平台工作区退路。
- 完成 Markdown 与 Git 差异检查；本次仅迁移指导文档，不运行完整项目测试。

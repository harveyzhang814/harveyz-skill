---
name: compose-agentsmd
description: "Compose, generate, or check a project's AGENTS.md from a fixed skeleton, reusable module packs and a small per-project config, so the standard development-flow rules stay in one place and the generated file never drifts by hand-editing. Triggers: 'compose AGENTS.md', 'generate AGENTS.md', 'check AGENTS.md', 'adopt the standard AGENTS.md skeleton', 'upgrade AGENTS.md modules'."
user_invocable: true
version: "0.1.0"
---

# 生成 AGENTS.md

## 作用（说明）

项目的 `AGENTS.md` 由三部分拼成：固定骨架（10 个槽，顺序和标题不变）、模块包（填标准槽的通用流程规则）、项目配置（`.hskill/compose-agentsmd/` 下的参数和描述槽）。流程规则只在发布包里维护一份；项目只写自己的内容。生成后的 `AGENTS.md` 首行带包版本和内容哈希，之后可以检测它是手改过、落后于新版包，还是只是配置改了没重新生成。

两类槽：

- 标准槽（`flow-summary`、`instruction-sources`、`platform-fallbacks`、`flow-steps`、`release-acceptance`）：由模块包填写，项目通过参数调整。
- 描述槽（`overview`、`principles`、`platform-adaptation`、`repo-env`、`other`）：项目自己写，每个槽对应 `slots/<槽id>.md`；文件为空时，`overview` 仍输出一级标题，其余描述槽整个不出现在输出里。

发布包随本 skill 安装在 `<skill 目录>/assets/packs/<名>/`，目前只有 `devflow`。

## 脚本

```bash
node <skill 目录>/scripts/compose-agentsmd.mjs <init|generate|check> [--root <项目根>] [--force]
```

`--root` 默认当前目录。标准输出每行一个 `key=value`：`status=`（可同时有多项，逗号分隔）、`path=`，以及每个发布包一行 `pack=<名> installed=<版本> generated=<版本>`；错误信息在标准错误。

| 子命令 | 退出码 |
|---|---|
| `init` | 0 已建；1 配置目录已存在（不动任何文件） |
| `generate` | 0 已写；1 目标文件疑似手改，拒绝覆盖（需 `--force`）；2 配置或模板错误 |
| `check` | 0 `ok`；1 其他状态；2 配置或模板错误 |

配置目录不存在时 `generate` 和 `check` 退出码为 2，先 `init`。

## 初始化

1. 运行 `init`。它在 `<项目根>/.hskill/compose-agentsmd/` 下写入 `config.json`（`pack` 预填 `devflow`，其余必填项留空字符串）和空的描述槽文件。已存在则退出码 1，不改任何文件，把现状告诉用户，不重来。
2. 发布包有多个时，先列出各包填哪些标准槽，请用户选主包（`pack`）。只有 `devflow` 时直接用。
3. 向用户确认必填参数：`title`（`overview` 的一级标题）、`integration_branch`、`merge_command`。可选参数：`e2e`、`complexity_signals`、`spec_dir`、`plan_dir`、`record_dir`；骨架级开关：`agent_canvas`（默认 `false`）、`disabled_slots`。各参数含义和默认值见包的 `pack.json`。

**项目已有手写 AGENTS.md 时：** 由你把现有内容拆开，再生成。

1. 对照 `<skill 目录>/assets/skeleton.json` 的槽和所选包的 `pack.json`，把现有内容归入描述槽（项目原则、平台适配、仓库环境、其他约定、概述）或配置参数（分支名、合并命令等）。
2. 凡属标准模块已覆盖的流程规则，不抄进描述槽；项目与模块写法不同的地方，用参数或本地包表达，不在描述槽里重复一套。
3. 运行 `generate --force`（原文件没有生成标记，会被判为手改，必须 `--force` 才能覆盖）。覆盖前先保留原文件副本。
4. 向用户展示原文与生成结果的差异，由用户确认。确认后才算完成；不确认则把副本恢复为 `AGENTS.md`。

## 生成 / 升级

- 改了配置或描述槽之后，运行 `generate`。退出码 2 时按 stderr 修配置，不要绕过校验。
- 装了新版 skill 之后，先运行 `check`。状态含 `outdated`（`AGENTS.md` 首行记录的发布包版本低于已安装版本）时，运行 `generate`，并按各 `pack=` 行汇报模块版本变化（`generated` 到 `installed`）。
- `check` 只在没有其他状态时才报 `stale`（配置或描述槽改了但没重新生成）。所以出现 `outdated` 的同时可能还有未生成的配置改动，这次 `generate` 会把它们一起带进去；汇报升级时要提醒用户这一点。
- `generate` 被拒绝（退出码 1）说明目标文件首行标记缺失或哈希不符，视为手改。不自行 `--force`：先让用户看清手改了什么，决定移回配置还是放弃，再由用户明确同意后才强制覆盖。

## 本地包

用户想替换某个标准槽的内容，又不想改发布包时：

1. 在 `.hskill/compose-agentsmd/packs/<名>/` 建本地包，可复制发布包里对应的模板作起点。本地包的 `pack.json` 声明它填哪些槽、用哪些参数，格式同发布包；模板里的参数写 `@{name}`，条件独占一行：`<!-- @if name -->`、`<!-- @else -->`、`<!-- @endif -->`，只允许单层。
2. 在 `config.json` 的 `slot_packs` 里指向它，例如 `"slot_packs": { "flow-steps": "my-steps" }`。该包必须声明了这个槽。
3. 不改发布包；本地包与发布包同名时校验报错，不做隐式优先。
4. 联动组里的槽（`devflow` 的 `flow-summary` 与 `flow-steps`，互相引用步骤编号）必须来自同一个包，只能一起替换、一起关闭；拆开会校验报错。
5. 本地包没有版本，它的改动只会在 `check` 里表现为 `stale`。

## 检查

运行 `check`，按 `status` 逐项汇报：

| status | 含义 | 你的动作 |
|---|---|---|
| `ok` | 与磁盘逐字节一致 | 汇报即可 |
| `missing` | 没有 `AGENTS.md` | 询问是否 `generate` |
| `hand-edited` | 首行缺失或哈希不符 | 提示用户把手改内容移回配置目录（描述槽、参数或本地包），不自行 `--force` |
| `outdated` | 某个发布包的已装版本更新 | 按「生成 / 升级」处理 |
| `stale` | 配置或描述槽改了没重新生成 | 询问是否 `generate` |

`check` 只读，不改任何文件。

## 边界

- 不提交 git：生成或改写 `AGENTS.md`、配置目录后，是否提交、在哪条分支提交，交给项目自己的流程。
- 不改其他宿主的指令文件（如 `CLAUDE.md`），也不替用户决定这些文件如何引用 `AGENTS.md`。
- 不改发布包；要定制只走参数、描述槽和本地包。
- 不手改生成出来的 `AGENTS.md`：改配置目录，再重新 `generate`。

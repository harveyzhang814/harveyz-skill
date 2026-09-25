---
status: 待执行
date: 2026-09-25
author_model: Codex
acceptance: hard
workspace_mode: shared-worktree
branch: fix/a1-skill-portability
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/fix+a1-skill-portability
base_commit: 6812670b12f3f262799119d1fbc2c66d6dae14df
source_node: 6401cd48-224a-4c03-8b99-d8571f8695d3
target_node:
---

# 交接：修复 A1 三个 Skill 的跨宿主执行断点

**交接目的**：由另一个 session 在已准备的独立工作区实施并自测 A1 修复，交回原 session 独立验收；接手方不合并或部署。

> 接手方先使用 `handoff` 的 verify 阶段校验本文件、分支和权威依据，无缺口再把状态改为「执行中」并开工。接手方完成后先按下方全部锚点自测，将结果写入标题含「自测」的独立小节，才把状态改为「待验收」并停手。「已验收」/「打回」只由交出方写。交接期间不要移除本 worktree。

## 背景与权威依据

本分支从本地 `staging` 的 `6812670b12f3f262799119d1fbc2c66d6dae14df` 建立，尚无 A1 源码改动。标准、静态审计、A1 规格与计划在另一条**尚未合并**的文档分支 `doc/skill-platform-adaptation-standard`，固定提交 `f3e63db353269f2c475714cd8bd53da9e0717f80`。接手时先读以下文件；该文档 worktree 在交接期间保留为只读依据：

- [平台适配标准](/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/doc+skill-platform-adaptation-standard/docs/reference/skill-platform-adaptation.md)
- [52 项静态审计](/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/doc+skill-platform-adaptation-standard/docs/reports/2026-09-24-published-skill-platform-audit.md)
- [A1 修复规格](/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/doc+skill-platform-adaptation-standard/docs/superpowers/specs/2026-09-25-a1-skill-portability-design.md)
- [A1 实施计划](/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/doc+skill-platform-adaptation-standard/docs/superpowers/plans/2026-09-25-a1-skill-portability.md)

若该工作区不可读，使用上述固定提交 `git show f3e63db353269f2c475714cd8bd53da9e0717f80:<仓库相对路径>` 读取同一版文件；不要从文档分支直接复制或合并提交到本修复分支。若固定提交也不可读，verify 应打回，不凭摘要猜规格。

## 关键决定与范围

- 只处理 `research/learn-video`、`research/extract-vision`、`agent-canvas/close-node`。共享任务语义不变，宿主工具只是实现方式；有能力时执行，缺能力时按规格顺序回退或安全停止。
- `learn-video` 保留模式确认、后台任务跟踪和 `DRIFT:` 由用户决定的门禁；不可默选模式，不猜 Video-Learner 或 skill 的个人安装路径，不启动无法追踪的长期任务。
- `extract-vision` 无委派能力时由当前 agent 过滤 OCR 文本；OCR 空且无原图视觉能力时报告并停止，不宣称图像无文字。
- `close-node` 接手方不得合并或删除 worktree。没有可靠“保留并离开/解除会话绑定”能力时在 handoff 收口步骤停下，不用单次 shell `cd` 冒充解除绑定，也不继续隐藏/停止节点。
- 不改安装器、vdl 工程、OCR 脚本、用户宿主配置、A2/B 批次或已安装 skill 副本。对真实视频、用户图像和活跃 Canvas 节点的实测需要明确授权；没有条件时记「未验证」，不可编造通过。

## 实施落点

主要文件是 `skills/research/learn-video/SKILL.md`、`skills/research/extract-vision/SKILL.md`、`skills/agent-canvas/close-node/SKILL.md`、`tests/skill-portability.test.mjs`、`skills-index.json`。按 A1 计划逐项做红绿测试、更新三个 skill 的 patch 版本及 index 的 `contentVersion`/`contentHash`。新增 `docs/reports/2026-09-25-a1-skill-portability-verification.md` 记录实际验证矩阵；原始静态审计不改写成运行结果。

## 工作流约定

工作区已由交出方创建并配置 `core.hooksPath=.githooks`、`merge.ff=false`。先核对 `git -C <worktree> branch --show-current` 为 `fix/a1-skill-portability`；不要自己再建分支或 worktree。Claude Code 可用 `EnterWorktree(path: "<worktree>")`；Codex 从该绝对路径启动/绑定 workspace，若无法重绑则每条 Git 命令用 `git -C <worktree>`，读写文件用绝对路径，不能靠跨调用的裸 `cd`。同一时刻只有一方操作本 worktree；接手方送验后停手。

先读本仓库 `AGENTS.md`、`docs/reference/git-workflow.md`、`docs/reference/testing-guide.md`。`.hskill/handoff/config.md` 里“无合并脚本、手动 merge”的旧句已经过时；以当前 `AGENTS.md` 为准：**接手方不合并**，将来只有交出方在验收通过且用户明确要求合并后使用 `scripts/merge-to-staging.sh`。不推送、不部署。

## 最小验收锚点

1. `learn-video`：测试先能在旧正文上证伪，修复后确认无需 `AskUserQuestion` 也可等待用户模式选择；脚本示例绑定真实 `SKILL_DIR`，不依赖两个 `$HOME/Projects/...` 固定目录；`DRIFT:` 与长期任务安全门禁未放宽。
2. `extract-vision`：测试先能在旧正文上证伪，修复后明确 OCR 文本的当前 agent 顺序回退，以及 OCR 空/模糊时无原图视觉能力的停止条件；不能把 OCR 空判成图像无内容。
3. `close-node`：测试先能在旧正文上证伪，修复后接手方在无可靠解除绑定能力时，保留 worktree 并停在隐藏/`stop-node` 前；Claude 的 `ExitWorktree(action: "keep")` 只是标明宿主的一个适配例子，不能删除接手方 worktree 或代替交出方合并。
4. 三个 `SKILL.md` 的 patch 版本与 `skills-index.json` 的 `contentVersion`/`contentHash` 一致，发布包包含所用脚本/适配文件；定向测试 `node --test tests/skill-portability.test.mjs` 通过，`git diff --check` 与暂存后的 `git diff --cached --check` 无错误。
5. 运行 `npm test` 并记录完整结果。若存在与本修复无关的红项，提供相同基线上的复现/归因证据并显式写「带着这条红送验」；不能引用过去豁免作为本轮通过。验证报告逐格区分静态、隔离路径、真实宿主与未验证，不声称七平台均已实测。
6. 交接文档由接手方写入逐项自测记录并置为「待验收」，代码和记录提交在本分支；本 worktree 仍存在，且没有合并到 `staging`、推送或部署。

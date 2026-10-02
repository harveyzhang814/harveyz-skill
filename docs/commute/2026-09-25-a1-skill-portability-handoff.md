---
status: 已验收
date: 2026-09-25
author_model: Codex
acceptance: hard
workspace_mode: shared-worktree
branch: fix/a1-skill-portability
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/fix+a1-skill-portability
base_commit: 6812670b12f3f262799119d1fbc2c66d6dae14df
source_node: 6401cd48-224a-4c03-8b99-d8571f8695d3
target_node: 0a795486-60f7-4c9d-a61b-26563ab01fbb
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

### 交出方独立验收记录（2026-09-25，第一轮）

结论：**打回**。在本文件指定的 `fix/a1-skill-portability` worktree 上，以 `6812670b12f3f262799119d1fbc2c66d6dae14df..bc3c2aa` 为改动范围独立核验；未合并、推送或部署。

1. **FAIL（锚点 1）**：`learn-video` 的模式选择、`SKILL_DIR` 路径和 `DRIFT:` 门禁已符合要求；但 A1 规格要求“若宿主不能可靠启动并追踪长期任务，启动前说明限制并停止”，现有正文仅要求后台启动及轮询，未给出能力缺失时的启动前停止分支。规格还要求 `npm run agent:serve` 前验证源码根目录及目标脚本存在；现有 `ECONNREFUSED` 分支直接使用 `<VIDEO_LEARNER_ROOT>`，未写该前置核验。两处均可能在能力/路径缺失时落入不可收尾或猜路径的执行断点。复修时请写明停止条件与服务脚本核验，且不放宽已存在的安全门禁。
2. **PASS（锚点 2）**：`extract-vision` 明确 OCR 文本由当前 agent 顺序回退；OCR 空或模糊而无原图视觉能力时停止，不断言图像无内容。仅静态/受控文本核验，未对真实图像实测。
3. **PASS（锚点 3）**：`close-node` 明确无可靠解除绑定能力时保留 worktree、停在第 4 步，禁止继续 `hide`/`stop-node`；未操作活跃 Canvas 节点。
4. **PASS（锚点 4）**：三个版本与索引 hash 用 SHA-256 占位符规则独立计算后均一致；`npm pack --dry-run --json --ignore-scripts` 清单含三个 `SKILL.md` 和四个引用脚本；`node --test tests/skill-portability.test.mjs` 为 5/5；`git diff --check`、`git diff --cached --check` 均退出 0。旧基线三项新增契约断言均不匹配，新正文均匹配。
5. **带着基线红项、未计作全绿（锚点 5）**：`npm test` 在 Bats 第 37、38 项失败并退出 1；修复 worktree 与本地 staging 基线分别执行 `bats -f 'hook e2e: real LLM' tests/hook-script.bats` 均在同两项失败。`bash scripts/run-skill-tests.sh` 单独退出 0（14 组、0 失败），被 `&&` 跳过的 Node 测试单独退出 0（340 项、333 pass、7 skip）。验证矩阵未声称真实视频、图像或 Canvas 宿主通过。
6. **PASS（送验时的锚点 6）**：接手方代码、自测记录均已提交，送验时 `status` 为「待验收」，worktree 保留；本轮验收后按流程改为「打回」。`git merge-base --is-ancestor HEAD staging` 退出 1，尚未合并。

复修后默认**重跑锚点 1–6 全集**，包括定向测试、版本/hash、打包清单、完整 `npm test` 及红项的基线归因；在新标题含「自测」的复修记录中逐项写实际命令、结果和未验证格子，再将状态置回「待验收」。不得覆盖本轮自测或验收记录。

### 交出方独立验收记录（2026-09-25，第二轮）

结论：**已验收**。在同一 `fix/a1-skill-portability` worktree 独立复核接手方提交 `180e88ca87c5598fc5fca752c160a1a393450407`；第一轮打回记录保留，不覆盖。

1. **PASS（锚点 1）**：旧基线不满足新增静态断言，当前正文满足；`learn-video` 在无可靠长期任务追踪时明确启动前停止，`agent:serve` 前要求用户提供根目录并核验 `package.json` 与目标脚本。模式选择、真实 `SKILL_DIR`、`DRIFT:` 用户确认门禁均保留；隔离的非默认 skill 路径下三个引用脚本均可定位。未启动真实视频任务。
2. **PASS（锚点 2）**：旧基线不满足当前 agent 的 OCR 文本顺序回退与无原图视觉能力停止断言，当前正文满足；未对用户图像执行实测。
3. **PASS（锚点 3）**：旧基线不满足安全解除绑定缺失时的停止断言，当前正文满足；接手方保留 worktree、停在隐藏/`stop-node` 前的契约未放宽。未操作活跃 Canvas 节点。
4. **PASS（锚点 4）**：SHA-256 version-placeholder 规则复算的三个 hash、版本与 index 一致；`npm pack --dry-run --json --ignore-scripts` 清单含三个 `SKILL.md` 和所用四个脚本；`node --test tests/skill-portability.test.mjs` 5/5 通过；基线到 HEAD、工作区及暂存区的 `git diff --check` 均退出 0。
5. **带着基线红项验收（锚点 5）**：完整 `npm test` 执行到 Bats 168 项，在第 37、38 项 hook real-LLM E2E 失败并退出 1；本地 `staging` 恰为交接基线 `6812670b12f3f262799119d1fbc2c66d6dae14df`，同两项用 `bats -f 'hook e2e: real LLM' tests/hook-script.bats` 复现失败，A1 diff 不涉及该 hook 或测试。因 `&&` 未执行的后半段分别独立运行：`bash scripts/run-skill-tests.sh` 14 组、0 失败；Node 聚合命令 340 项、333 pass、7 skip、0 fail。**不把 `npm test` 记为通过**；真实视频、用户图像、活跃 Canvas 与七平台端到端仍为未验证。
6. **PASS（锚点 6）**：复修代码和含“自测”的独立记录已提交，送验时状态为「待验收」，工作区干净且保留；`git merge-base --is-ancestor HEAD staging` 退出 1，未合并。验收只更新本交接文档，不推送、不部署、不移除 worktree。

## 接手方自测记录（2026-09-25）

1. PASS — `node --test tests/skill-portability.test.mjs`：5/5 通过，覆盖三个 A1 skill 的新增跨宿主安全契约。
2. PASS — 临时非默认 skill 路径下检查 learn-video 的 `store_config.py`、`archive.py`、`build_creator_index.py` 均可定位；未启动真实视频任务。
3. PASS（静态/隔离）— OCR 文本的金额、日期受控样例以及无原图视觉能力的停止契约均已核对；未对用户图像执行实测。
4. PASS — 三个 patch 版本与 `skills-index.json` 的 `contentVersion`/`contentHash` 已同步；`git diff --check` 与暂存后的 `git diff --cached --check` 均无错误。
5. 带着这条红送验 — `npm test` 的 hook E2E 第 37、38 项失败。相同命令在本地 `staging` 基线也失败，失败点为外部 `claude -p` 调用；完整归因见 `docs/reports/2026-09-25-a1-skill-portability-verification.md`。其他可见的定向回归为绿。
6. PASS — worktree 保留，未合并到 `staging`、未推送、未部署。待提交后停止操作，交出方应按 accept 阶段独立复核。

## 接手方复修自测记录（第 1 轮，2026-09-25）

1. PASS — `node --test tests/skill-portability.test.mjs`：5/5 通过；新增断言覆盖无可靠长期任务追踪时启动前停止，以及 `agent:serve` 的显式根目录、`package.json` 与脚本核验。
2. PASS — `npm pack --dry-run --json --ignore-scripts` 清单含三个目标 `SKILL.md` 及 learn-video 的三个引用脚本；未执行真实视频、用户图像或活跃 Canvas 节点，均保持未验证。
3. PASS — SHA-256 version-placeholder hash 与 index 一致：learn-video `88b278c447599308` (1.9.2)、extract-vision `c9f68c043bc09309` (1.2.1)、close-node `6d1a64ac69a377be` (1.0.4)。
4. PASS — `git diff --check` 与暂存后的 `git diff --cached --check` 均无错误。
5. 带着这条红送验 — `npm test` 完整运行至 Bats 结束，168 项中仅 hook E2E 第 37、38 项失败；与 `staging` 基线的相同失败归因不变，见验证报告。由于 npm 的 `&&`，后续 Node 聚合命令未在此轮 npm 调用中触发；首轮独立验收已记录其 340 项、333 pass、7 skip、退出 0 的结果。
6. PASS — 本轮改动和该复修记录将提交在 `fix/a1-skill-portability`；worktree 保留，未合并、推送或部署。

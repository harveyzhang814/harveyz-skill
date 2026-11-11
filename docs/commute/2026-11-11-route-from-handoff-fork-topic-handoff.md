---
status: 待执行
date: 2026-11-11
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/route-from-handoff-fork-topic
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+route-from-handoff-fork-topic
source_node: ce78124f-0115-46b5-86ec-44b7cb2b6db2
target_node: 071b2430-75f2-46a2-9318-7b9738b49e2a
---

# 交接：handoff 与 fork-topic 建节点改走路由引擎

**交接目的**：用户已确认 plan，接手方按 plan 实施四个 Task（画布命令桩、handoff 第 6 步、fork-topic 画布分支、全量回归与 eval 实跑），完成后交回本节点验收。

---

## 背景与现状

- Agent Canvas 新增了节点路由引擎：agent 给任务按类别字段定级，由引擎选出模型和 effort。实现目前只合进了 agent-canvas 的本地 staging，**还没发版**。你机器上已安装的 App 里，`agent-canvas-ctl create-routed-pty-node` 会报「未知子命令」，退出码 1。所以不要在真实画布上试路由命令，eval 一律用 Task 1 做的桩。
- 用户定下路由只有两个入口：handoff 建接手节点（develop 类别），fork-topic 分支线（think 类别）。本次只改这两个 skill。
- 本 worktree 已有两次提交：测试清单（`e7e3702`）和 plan（`e8aa5d2`）。实现还没开始。

## 关键决定（别改动）

这些都已经和用户逐条确认过，不要重新纠结：

1. **由 skill 触发，程序不强制；字段由发起方 agent 定级。** 已否决的方案：在 `create-pty-node` 入口强制走路由（程序分不清场景，查询类小活会被硬塞进不合适的类别）；由 App 内部调模型来定级（要新建子系统，而且每次都得从零读 plan）。
2. **skill 正文不抄写字段标准和段落名**，一律以 `describe-node-route-category` 的输出为准（plan 的静态测试会强制检查）。
3. **fork-topic 在画布里不建关系。** 用户要的是一种新的关系类型，这已经另立需求、要改 App，不在本次范围内。也不加 `--expect-reply`。
4. **agent-canvas-control 不改**（它会被 App 强制覆盖；触发规则归各场景 skill 自己管）。
5. **退回规则**：报未知子命令或 `PRECONDITION_FAILED` 时退回 `create-pty-node`；报 `INVALID_ARGUMENT` 时修正参数后重试路由；用户点名了节点类型或模型时，直接用 `create-pty-node`。

## 范围铁律

- **做**：plan 的 Task 1–4，plan 的 `Global Constraints` 全部遵守。
- **不做**：改 `skills/agent-canvas/`、改 Agent Canvas App、`npm publish`、合并到 `staging`、在真实画布上建节点。
- **接手方的边界**：函数内部怎么实现可以自己决定。不得修改接口签名、测试名称与断言、`Global Constraints`。plan 与代码库现状冲突或无法照做时，停手，按「画布通信」打回本节点，不要自行变通。

## 相关文档索引

- plan（权威，按它执行）：`docs/superpowers/plans/2026-11-11-route-from-handoff-fork-topic.md`
- 测试清单（权威，用例 H1–H5、F1–F4 的来源）：`docs/superpowers/specs/2026-11-11-route-from-handoff-fork-topic-test-plan.md`
- 路由命令契约（另一个仓库，只读）：`/Users/harveyzhang96/Projects/agent-canvas/docs/superpowers/specs/2026-11-10-node-routing-category-params-design.md` §4.2（develop 字段、证据、description 段）、§4.3（think）、§4.4（命令入参与 describe 出参结构）。Task 1 的 `describe-*.json` 内容从这里取。
- 测试写法：`docs/reference/testing-guide.md`；静态测试的先例：`tests/handoff-worktree.test.mjs`；eval 现场脚本的先例：`skills/coding/handoff/evals/fixtures/accept-worktree/setup.sh`；harness 实跑示例：`docs/superpowers/specs/measurements/2026-08-17-quality-eval-e2e.md`。

## 工作流约定

- 工作区已经建好（frontmatter 的 `worktree`），调用 `manage-worktree` 的「进入」，不建 worktree、不建分支。到位后确认 `git config core.hooksPath` 为 `.githooks`、`git config merge.ff` 为 `false`。
- 按 plan 开头的 `REQUIRED SUB-SKILL`（`superpowers:subagent-driven-development`）执行，不重写 plan。执行 skill 建议新建 worktree 时一律跳过。派发 subagent 时，prompt 第一段写目录守卫：`cd <worktree> && git rev-parse --show-toplevel && git branch --show-current`，结果不符就停。
- commit 用 Conventional Commits（`docs` 不是 `doc`），每个 Task 提交一次，结尾带 `Co-Authored-By` trailer。
- 完工后不合并、不 remove 工作区，`status` 推到「待验收」后按「画布通信」通知 `source_node`，然后停手。

## 最小验收锚点

全部为硬判据，逐条判对错：

1. plan 里各 Task 的测试与 plan 写定的测试名称和断言一致，并全部通过：`node --test tests/canvas-stub.test.mjs tests/handoff-routing.test.mjs tests/handoff-worktree.test.mjs tests/fork-topic-routing.test.mjs tests/harness/declarations.test.mjs` 退出码 0。
2. `npm test` 退出码 0。
3. `skills/coding/handoff/SKILL.md` 版本为 `1.19.0`，`skills/coding/fork-topic/SKILL.md` 版本为 `1.1.0`，`skills-index.json` 两个条目的 `contentVersion` 和 `contentHash` 与正文一致（由第 1 条里的测试覆盖）。
4. Task 4 的 eval 实跑：handoff 新增的 4 条（`author-canvas-routes-develop`、`author-canvas-named-codex`、`author-canvas-old-app-fallback`、`author-canvas-invalid-retry`）与 fork-topic 新增的 3 条（`fork-canvas-routes-think`、`fork-canvas-old-app-fallback`、`fork-canvas-named-model`），全部断言为 pass；handoff 原有 eval 0、1，fork-topic 原有 eval 0–2，断言结果不比改动前差。runId 与逐条结果记录在 `docs/superpowers/specs/measurements/2026-11-11-route-from-handoff-fork-topic-evals.md`。
5. `git diff $(git merge-base staging HEAD)..HEAD --name-only` 列出的文件不超出 plan 各 Task 的 Files 清单、本交接文档、测试清单与 plan 本身。

测试清单的 `## 验收标准`（V1–V3）要等带路由命令的 App 发版后才能验证，不属于本次交接的验收范围。

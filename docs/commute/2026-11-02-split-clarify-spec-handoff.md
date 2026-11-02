---
status: 待执行
date: 2026-11-02
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: shared-worktree
branch: feature/split-clarify-spec
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+split-clarify-spec
base_commit: de37def7e7e9b3df64a5dbda4e8388a78834cb31
source_node: 1966b96f-98dd-42cd-a253-e8ff5e46da16
target_node: 4f479d60-23d1-48d5-93ff-7d0ea3b4fdb8
---

# 交接：按获批 Spec 实施 question-me / init-spec 分工改造

**交接目的**：接手方依据已获用户批准的 Spec v1，先拆实施计划，再完成实现与自测，交回原 session 验收。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」章节开工。
>
> **完成后不是直接推状态，先自测**（skill 的 Phase 2.5）：逐条实跑「最小验收锚点」**全集**（不是只跑你改动相关的那几条），外加文档点名要复跑的既有资产；判成败的命令不接管道（`| tail` 的退出码是 `tail` 的，恒为 0）。把结果写成**独立小节**，标题里必须有「自测」二字（如「接手方自测记录（日期）」），逐条列 pass/fail 并附实际命令——写你自己这一节，别混进原 session 的验收记录。**有红就别推状态**：要么修到绿，要么在那一条旁边写出归因证据并显式声明「带着这条红送验」，不许沉默推上来。`validate-handoff.sh` 会拦：`status` 是「待验收」而正文没有含「自测」的小节直接 exit 1。
>
> 自测过了，才把 frontmatter 的 `status` 置为「待验收」并**停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。
>
> **被打回之后同理，而且默认跑全集**：打回轮范围小、容易觉得「就改一行」，恰恰是二次打回最常见的来源。复修完重新走一遍自测才能再置回「待验收」；要只跑子集，必须在记录里附改动范围证据（`git diff --name-only <打回点提交>..HEAD`）和「其余条目不可能被波及」的论证。复修记录另起一节（如「接手方复修自测记录（第 N 轮）」，同样含「自测」二字），不覆盖前几轮。
>
> **开工前**：若 frontmatter 有 `source_node`、且你也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from <source_node> --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：frontmatter 有 `worktree` 时，进那个工作区干活，核对当前分支与 `branch` 一致。**怎么进按你所在平台来**（Claude Code 用 `EnterWorktree(path: <worktree>)` 的 `path` 模式；Codex 从该路径启动/绑定 workspace，或用 `codex -C <worktree>`；没有这类能力就每条命令自带限定 `git -C <worktree>`，读写文件用绝对路径，别靠裸 `cd`——它只在单条命令内有效）。判据只有一条：后续命令的工作目录确实是那个工作区。**不要自己 `git worktree add` 或用 Codex `--worktree`**（那会另建工作区；原 session 验收时回的是 author 建的那一个，看不到替代工作区里的改动），**也绝不要销毁它**（`git worktree remove`，或平台的"退出并删除"）——验收还要用。路径不存在就打回原 session 重建，别自己挑地方。

---

## 背景与现状

init-spec 第一阶段自带一整套需求澄清规则，与 question-me 大面积重合且互相矛盾。用户决定拆开分工：question-me 只负责需求澄清，init-spec 依据 question-me 的确认摘要建决定记录、做方案审查并写 Spec。需求澄清、方案审查、Spec 编写、构建者检查都已在原 session 走完，Spec v1 已于 2026-11-02 获用户批准。

本分支已有提交只含 Spec 与决定记录（`.hskill/spec/2026-11-02-split-clarify-spec/`），还没有任何实现改动。改动前在本分支跑过 `npm test`，全绿。

## 关键决定（别改动）

以下都已获用户批准。Spec 是权威，这里只列最容易被推翻的几条：

- **question-me 迁入 `superpowers-rewrite` bundle**，目录迁到 `skills/superpowers-rewrite/question-me`（决定记录 D12）。不要改成跨 bundle 依赖，也不要在 init-spec 里留精简版提问作兜底；这两条路用户已经否决。
- **交接走会话，不写文件**：question-me 结束时输出一份自足的七字段摘要，init-spec 只依据摘要工作（D4、Spec 5.6）。
- **摘要确认即需求批准**：init-spec 不再重复提交需求条目审查（D5）。用户贴入的摘要例外，须重新确认（D15）。
- **发散的判定**：有多个候选方向未选、或还在找方向，才算发散；只有一个方向的继续澄清（D17，取代已失效的 D9）。
- **试做**：留在 init-spec，改在第二阶段方案审查中做；question-me 不做试做；HARD-GATE 只改试做例外那一句（D18）。
- **版本号**：question-me 升 `4.0.0`，init-spec 升 `0.3.0`（Spec 第 7 节）。

## 范围铁律

**做（全部以 Spec 第 2、5、6、7 节为准）：**
- 迁移 question-me 目录；
- 重写 question-me 的 `SKILL.md`；
- 修改 init-spec 的 `SKILL.md`；
- 同步 `skills-index.json`、`package.json` 的 `files`、`tests/skill-portability.test.mjs`、`docs/product/PRD.md`、`CHANGELOG.md`。

**不做：**
- 不改 rephrase、`render_tree.py` 及其测试、`skill-map.html`；
- 不改 `docs/superpowers/` 下的历史文档；
- 不碰 `~/.claude/skills/` 下任何装机副本（包括旧的 brainstorming）；
- 不新建 skill；
- **不合并到 staging**：合并只由原 session 做。

Spec 第 9 节的两条“未核实前提”不需要你去解决。工作中若顺带查明，写进自测记录即可。

## 相关文档索引

- **Spec（权威）：** `.hskill/spec/2026-11-02-split-clarify-spec/2026-11-02-split-clarify-spec-spec.md` v1。实现所需的决定都在里面。
- **决定记录：** 同目录 `2026-11-02-split-clarify-spec-record.md`，用来追溯 D1–D18 的来源与理由。
- **现有 skill：**
  - `skills/coding/question-me/SKILL.md`（迁移前路径）
  - `skills/superpowers-rewrite/init-spec/SKILL.md`
  - `skills/superpowers-rewrite/develop-plan/SKILL.md`（拆计划用）
- **仓库约定：**
  - `AGENTS.md`：`skills-index.json` 登记与 `contentHash` 规则
  - `docs/reference/testing-guide.md`：写新测试前读

## 受影响文件/落点

- `skills/coding/question-me/` → `skills/superpowers-rewrite/question-me/`（`git mv`，含 `scripts/`）
- `skills/superpowers-rewrite/question-me/SKILL.md`
- `skills/superpowers-rewrite/init-spec/SKILL.md`
- `skills-index.json`：question-me 与 init-spec 条目，以及 `bundleMeta.coding`、`bundleMeta.superpowers-rewrite`
- `package.json`：`files` 字段用 `node scripts/generate-npmignore.js` 重新生成；若出现与本任务无关的差异，按 Spec 第 7 节改为手工修改
- `tests/skill-portability.test.mjs`：两处 question-me 路径和期望版本
- `docs/product/PRD.md`
- `CHANGELOG.md`：写在 `[Unreleased]` 下
- 新增：实施计划 `.hskill/spec/2026-11-02-split-clarify-spec/2026-11-02-split-clarify-spec-plan.md`

## 工作流约定

1. **进入工作区并配置**：
   ```
   EnterWorktree(path: "/Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+split-clarify-spec")
   git branch --show-current            # 必须是 feature/split-clarify-spec
   git config core.hooksPath .githooks && git config merge.ff false
   ```
   不建 worktree、不建分支。离开时用 `ExitWorktree(action: "keep")`，绝不 remove。
2. **拆计划用 develop-plan，不用 writing-plans。**
   - develop-plan 和 init-spec 都**没有装机副本**（`~/.claude/skills/` 下没有），Skill 工具调不到。直接读本工作区里的 `skills/superpowers-rewrite/develop-plan/SKILL.md`（0.2.0），照着执行；输入为已批准的 Spec 路径、版本 `v1`、范围“全文”。
   - 计划写到上面那个 plan 文件路径，并提交。
   - `.hskill/handoff/config.md` 写的 `superpowers:writing-plans` 是旧约定；本任务的 Spec 出自 init-spec，按其流程衔接 develop-plan，这一点原 session 已与用户确认。
3. **执行计划**：可用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development`。**跳过它们要求的 `using-git-worktrees` 步骤**，工作区已经建好。
4. **提交**：遵守 Conventional Commits，类型用 `docs` 不用 `doc`，hook 会拒绝后者。每个 commit 末尾带上 `Co-Authored-By:` 行。
5. **`contentHash` 算法**：对 SKILL.md 全文，把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__`，取 sha256 十六进制前 16 位（见 `tests/skill-portability.test.mjs` 的版本与哈希断言）。

## 最小验收锚点

全部为硬判据，对应 Spec 第 8 节，另加计划落库一条。原 session 将逐条重跑。

1. `npm test` exit 0。
2. `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` exit 0。
3. `skills/coding/question-me` 不存在；`git grep -n "coding/question-me"` 只命中 `docs/superpowers/`、`docs/reports/`、`docs/commute/` 下的文件和 `CHANGELOG.md` 的既有条目。
4. question-me 的 `SKILL.md` 中 `grep -nE "Q1|Q2|Q3|至少 3 个|at least 3 options"` 无命中。
5. init-spec 的 `SKILL.md` 中 `grep -nE "共同澄清范围|探索性对话|定义性对话|阶段性复述|探索性试做"` 无命中，且第二阶段含试做条目。question-me 的 `SKILL.md` 含“探索模式”“阶段性复述”及 Spec 5.4 的六项标准，不含“试做”。
6. init-spec 的 description 不含 “clarify requirements”；question-me 的边界含“需要成文 Spec → 提议转 init-spec”的条目。
7. question-me 的摘要模板七个字段齐全（Spec 5.6），三类来源与节点状态的对应关系写明。init-spec 第一阶段对“用户原始需求”“决定”“已查明事实”“假设”“未决”五个字段各有建档规则。
8. 按 Spec 第 4 节走读三条路径，每一步都有明确去向：
   - 入口 A：正常路径与非正常出口，全程不存在“确认后直接执行”的分支；
   - 贴入摘要路径；
   - 入口 B 的三个出口。
9. `node bin/cli.js list --json` 输出中，question-me 的 `bundle` 为 `superpowers-rewrite`。
10. `skills-index.json` 中 question-me 的 `contentVersion` 为 `4.0.0`、init-spec 的为 `0.3.0`，两者的 `contentHash` 都与按上述算法算出的值一致。
11. 实施计划文件已提交到本分支。

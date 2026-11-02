---
status: 已验收
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

- **Spec（权威）：** `.hskill/spec/2026-11-02-split-clarify-spec/2026-11-02-split-clarify-spec-spec.md` v1.1（v1 的勘误版，只改了验收第 3 条的允许列表和引用编号范围）。实现所需的决定都在里面。
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
   - develop-plan 和 init-spec 都**没有装机副本**（`~/.claude/skills/` 下没有），Skill 工具调不到。直接读本工作区里的 `skills/superpowers-rewrite/develop-plan/SKILL.md`（0.2.0），照着执行；输入为已批准的 Spec 路径、版本 `v1.1`、范围“全文”。
   - 计划写到上面那个 plan 文件路径，并提交。
   - `.hskill/handoff/config.md` 写的 `superpowers:writing-plans` 是旧约定；本任务的 Spec 出自 init-spec，按其流程衔接 develop-plan，这一点原 session 已与用户确认。
3. **执行计划**：可用 `superpowers:executing-plans` 或 `superpowers:subagent-driven-development`。**跳过它们要求的 `using-git-worktrees` 步骤**，工作区已经建好。
4. **提交**：遵守 Conventional Commits，类型用 `docs` 不用 `doc`，hook 会拒绝后者。每个 commit 末尾带上 `Co-Authored-By:` 行。
5. **`contentHash` 算法**：对 SKILL.md 全文，把 `version:` 行替换为 `version: __HASH_PLACEHOLDER__`，取 sha256 十六进制前 16 位（见 `tests/skill-portability.test.mjs` 的版本与哈希断言）。

## 最小验收锚点

全部为硬判据，对应 Spec 第 8 节，另加计划落库一条。原 session 将逐条重跑。

1. `npm test` exit 0。
2. `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` exit 0。
3. `skills/coding/question-me` 不存在；`git grep -n "coding/question-me"` 只命中 `docs/superpowers/`、`docs/reports/`、`docs/commute/`、`.hskill/spec/2026-11-02-split-clarify-spec/` 下的文件和 `CHANGELOG.md`（本任务的 Spec、记录、计划和 CHANGELOG 新条目会合法地提到旧路径）。
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

## 接手方自测记录（2026-11-02）

在 HEAD `d053875` 上逐条实跑，锚点全集 1–11。判成败的命令都没接管道。下文 `Q` 指 `skills/superpowers-rewrite/question-me/SKILL.md`，`I` 指 `skills/superpowers-rewrite/init-spec/SKILL.md`。

| # | 结果 | 实跑命令 / 依据 |
|---|---|---|
| 1 | pass | `npm test` → exit 0：bats 全过，custom skill tests 14/14，node 356 pass / 0 fail / 7 skip |
| 2 | pass | `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` → exit 0，9 passed |
| 3 | pass | `test -e skills/coding/question-me` 为假。`git grep -n "coding/question-me"` 只命中允许范围：`.hskill/spec/2026-11-02-split-clarify-spec/` 下 3 个文件，`docs/commute/`、`docs/reports/`、`docs/superpowers/` 下的文件。`CHANGELOG.md` 无命中 |
| 4 | pass | `Q` 中 `grep -nE "Q1\|Q2\|Q3\|至少 3 个\|at least 3 options"` 无命中 |
| 5 | pass | `I` 中 `grep -nE "共同澄清范围\|探索性对话\|定义性对话\|阶段性复述\|探索性试做"` 无命中；`I` 第二阶段含「**试做。**」条目。`Q` 含「探索模式」「阶段性复述」及 Spec 5.4 六项原文，不含「试做」 |
| 6 | pass | `I` 的 description 不含 “clarify requirements”；`Q` 边界含「需要成文 Spec → 提议转 init-spec，等用户同意，不自动交棒」 |
| 7 | pass | `Q` 摘要模板七个字段齐全，来源三类对应关系写明（`done` 节点 → 用户选择，`infer` 节点 → Agent 推断，主动提出 → 用户原始需求）。`I` 第一阶段「按摘要建档」对用户原始需求、决定、已查明事实、假设、未决五个字段各有建档规则 |
| 8 | pass | 走读三条路径，见下 |
| 9 | pass | `node bin/cli.js list --json` → question-me 为 `{"path":"superpowers-rewrite/question-me","bundle":"superpowers-rewrite"}` |
| 10 | pass | 按交接文档的算法重算 hash，与 `skills-index.json` 一致。question-me：`contentVersion` 4.0.0，`contentHash` `33c8695fdd9fa2d6`。init-spec：`contentVersion` 0.3.0，`contentHash` `b60024f9874bd4af` |
| 11 | pass | `git log -- .hskill/spec/2026-11-02-split-clarify-spec/2026-11-02-split-clarify-spec-plan.md` → `c59d6aa` |

锚点 4–7 和 10 另用一段 node 脚本逐条断言，30/30 PASS。这段脚本是临时文件，没有入库。

**锚点 8 走读**

- **入口 A，正常路径：**
  1. `I` 第 28 行：简单任务直接完成。
  2. `I` 第 29 行：会话内已确认的摘要直接用；否则按名调用 question-me，并告知由 init-spec 发起。
  3. `Q` 第 24 行：只凭当前会话判定发起方。
  4. `Q` 第 151 行：摘要的确认句写明「确认后交回 init-spec」。
  5. `Q` 第 155 行：确认后不执行任务，交回。
  6. `I` 第 31 行：只依据摘要建档；用户的确认即为需求批准，进入第二阶段。

  整条路径里，「直接执行」只出现在 `Q` 第 157–158 行「独立使用」那一支，入口 A 走不到。
- **入口 A，非正常出口：**
  - 用户修改摘要：`Q` 第 151 行继续澄清，更新摘要后再请确认；与 `I` 第 33 行起的「非正常出口」一致。
  - 发散型请求，或用户决定不做：`Q` 第 155 行停下并告知 init-spec，不输出待确认的摘要；`I` 的「非正常出口」随之结束，不建记录。
- **贴入摘要路径：**
  1. `I` 第 29 行：贴入的摘要不视为已批准，交给 question-me，按七个字段补问。
  2. `Q` 初始化第 5 条：已覆盖的不再问，只补缺口，随新摘要一起确认。
  3. 之后同入口 A 第 4–6 步。
- **入口 B 三个出口：** `Q` 第 158–160 行：小任务直接执行；需要成文 Spec 的提议转 init-spec，用户同意后 init-spec 用这份摘要；用户决定不做的结束。

**工作中查明 / 需要原 session 知道的事**

- **全分支独立审查：** 由 Opus 子代理执行。没有 Critical，2 条 Important 已在 `d053875` 修复：
  - question-me 一侧缺「已知信息 / 贴入摘要」的处理规则；
  - 被 init-spec 发起时，question-me 缺「不做 / 发散」的退出规则。
- **超出 Spec 原文字面的两处：**
  - 上述两条修复补的是 Spec 第 4 节要求、而原先只在 init-spec 一侧兜底的行为，没有新增行为。
  - init-spec description 删掉了 “brainstorm a feature”，理由是它是被删的「帮我想想这个功能」对应的英文。
- **延后的 Minor：**
  - 试做在第二阶段单列为一段，没有并进「方案形成标准」段内；
  - 入口 B 没写「按名调用 init-spec」；
  - 结束判据还有「待确认」项、但节点已全部结案时，怎么处理 Spec 5.4 本身没写；
  - Spec 第 6 节「假设」条目建档后的批准状态措辞有歧义，按 Spec 原文照搬。
- **Spec 第 9 节两条未核实前提：** 未处理，Spec 也没要求处理。
- **`package.json` 的 `files`：** `node scripts/generate-npmignore.js` 的生成结果只改了 question-me 那一行，没有无关差异。
- **偶发红：** 一次 `npm test` 中 `tools/browser-fetch` 的 `test_download_images_real_network` 因网络失败。单独重跑通过，与本次改动无关，最终那次完整运行是全绿的。

## 原 session 验收记录（2026-11-02）

在交接工作区 HEAD `f84aca0`（分支 `feature/split-clarify-spec`）上逐条自己重跑，不采信自测结论。机器校验 `validate-handoff.sh` 通过。

| # | 结果 | 实跑命令 / 依据 |
|---|---|---|
| 1 | pass | `npm test` exit 0：custom skill tests 14/14，node 356 pass / 0 fail |
| 2 | pass | `python3 skills/superpowers-rewrite/question-me/scripts/test_render_tree.py` exit 0，9 passed |
| 3 | pass | `test -e skills/coding/question-me` 为假；`git grep -n "coding/question-me"` 命中 10 个文件，全在 `.hskill/spec/2026-11-02-split-clarify-spec/`、`docs/commute/`、`docs/reports/`、`docs/superpowers/` 下 |
| 4 | pass | question-me SKILL.md 中 `grep -nE "Q1\|Q2\|Q3\|至少 3 个\|at least 3 options"` rc=1 |
| 5 | pass | init-spec SKILL.md 中禁用词 grep rc=1；第二阶段含「**试做。**」（第 59 行），HARD-GATE 试做例外改为「在方案审查中做的试做」（第 99 行）。question-me 含「探索模式」「阶段性复述」与六项结束判据（第 113–120 行），`grep -n 试做` rc=1 |
| 6 | pass | init-spec SKILL.md 中 `grep -n "clarify requirements"` rc=1；question-me 第 31 行「需要成文 Spec → 提议转 init-spec，等用户同意，不自动交棒」 |
| 7 | pass | question-me 第 132–149 行七字段与三类来源对应齐全；init-spec 第 37 行对五个字段各有建档规则 |
| 8 | pass | 读原文核对：入口 A 为 I28 → I29 → Q24 → Q151 → Q155（不执行、交回）→ I31；非正常出口为 I33–35 与 Q151、Q155；贴入摘要为 I29 → Q49；入口 B 为 Q157–160。「直接执行」只在 Q158 的独立使用分支 |
| 9 | pass | `node bin/cli.js list --json` 中 question-me 与 init-spec 的 bundle 都是 `superpowers-rewrite` |
| 10 | pass | node 按算法重算：question-me 4.0.0 / `33c8695fdd9fa2d6`，init-spec 0.3.0 / `b60024f9874bd4af`，与索引一致 |
| 11 | pass | `git log -- …-plan.md` 得到 `c59d6aa` |

**回归面核对：**
- 改动面取自 `git diff --name-only $(git merge-base staging HEAD)..HEAD`，分叉点为 `de37def`，共 14 个文件。
- 被波及的组件有三个：skill 格式校验（`tests/skills.bats`）、打包与安装（`tests/install.bats`、`package.json`）、可移植性断言（`tests/skill-portability.test.mjs`）。三者都在第 1 条的 `npm test` 内，全绿。
- `package.json`、PRD、CHANGELOG 的 diff 已逐行读过，没有无关改动。
- 另想在临时 HOME 里实装 superpowers-rewrite bundle，核对 question-me 的 `scripts/` 是否一并装上。这条命令被权限拒绝，未执行；它不在锚点之内，记为未覆盖项。

**偏离 Spec 字面的两处，判定不构成未达成：**
- init-spec 的 description 删掉了 “brainstorm a feature”。Spec 第 6 节的保留清单里本来就没有这一项。
- 第三阶段构建者检查保留了「方案问题返回方案审查」。D16 约束的是“重新澄清需求”，方案问题回到方案审查不属于澄清，与 D16 不冲突。

**结论：** 达成。

**验收后补充（2026-11-02，publish-skill 检查）：** question-me 的 description 中有两个中文触发词，违反 F3「description 须为英文」。现已改为英文 `'clarify the requirements'`、`'help me think this through'`，正文第 16 行的中文触发词保留。版本仍为 4.0.0（该版本尚未发布），`contentHash` 更新为 `080681a3d025c13e`，上表第 10 条中的旧 hash 作废。修改后重跑 `npm test`，exit 0（356 pass / 0 fail）。

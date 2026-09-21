---
status: 打回
date: 2026-09-20
author_model: claude-opus-5
acceptance: hard
branch: feature/capture-vocab-retrieval
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+capture-vocab-retrieval
source_node: 563e3f7c-bb73-400b-a45a-bc5ab090c2e6
target_node: 4242f9e0-a3f2-44cd-961c-b49c44fe7d4b
---

# 交接：capture-vocab 检索机制重构（加切片脚本，词汇文件零迁移）

**交接目的**：设计已跟用户逐轮确认并定稿落盘（spec 见下），接手方按 spec 实施——新增一个 python 脚本、配套 pytest、改写 SKILL.md、升版本号。不需要重新设计，也不接受重新设计。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」章节开工。
>
> **完成后不是直接推状态，先自测**（skill 的 Phase 2.5）：逐条实跑「最小验收锚点」**全集**（不是只跑你改动相关的那几条）。判成败的命令不接管道（`| tail` 的退出码是 `tail` 的，恒为 0）。把结果写成**独立小节**，标题里必须有「自测」二字（如「接手方自测记录（日期）」），逐条列 pass/fail 并附实际命令——写你自己这一节，别混进原 session 的验收记录。**有红就别推状态**：要么修到绿，要么在那一条旁边写出归因证据并显式声明「带着这条红送验」，不许沉默推上来。`validate-handoff.sh` 会拦：`status` 是「待验收」而正文没有含「自测」的小节直接 exit 1。
>
> 自测过了，才把 frontmatter 的 `status` 置为「待验收」并**停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。
>
> **被打回之后同理，而且默认跑全集**。复修完重新走一遍自测才能再置回「待验收」；要只跑子集，必须在记录里附改动范围证据（`git diff --name-only <打回点提交>..HEAD`）和「其余条目不可能被波及」的论证。复修记录另起一节（如「接手方复修自测记录（第 N 轮）」，同样含「自测」二字），不覆盖前几轮。
>
> **开工前**：你若也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from 563e3f7c-bb73-400b-a45a-bc5ab090c2e6 --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：工作区已建好（frontmatter 的 `worktree`），`EnterWorktree(path: <worktree>)` 进去，核对当前分支等于 `branch`。**不要自己 `git worktree add`**（那条分支已被这个工作区 checkout，再建会失败；而且原 session 验收时回的是这个工作区，看不到你另建的那个），**也绝不要 `git worktree remove`**——验收还要用。

---

## 背景与现状

`capture-vocab` 维护项目级领域术语字典，落盘 `<project-root>/.hskill/capture-vocab/vocab.md`。当前唯一实际使用者是 agent-canvas：33 条术语、23008 字节、被 git 追踪。

问题：`query` 的实现是「读文件、自己找 section」，全文必然进上下文（33 条约 8–10k token）。用户提出的三类检索场景里，`add` 查重（低频）需要语义判断，而 agent 自发查词（高频）只需要「有无定义 + 命中那一条」。

**根因判断（已与用户确认）**：全文进上下文的根因是**没有切片工具**，不是存储格式。切片做在 shell 里，`vocab.md` 一个字节都不用改。

**一个容易误判的事实**：SKILL.md 文档里建议 `CLAUDE.md` 写「session 开始读取 vocab.md」，但 **agent-canvas 没有照做**，它手工写了「用 grep 查词条、不要读全文」。所以本次改动的净收益不是「省掉 session 开头 8–10k」，而是相对那个手工 grep 方案的增量（别名匹配、section 边界精确、未命中只花 ~20 token、以及查重）。spec §1.3 有完整说明。

## 关键决定（别改动）

这些是逐轮讨论后定下的，**不要在实施中推翻或"顺手改进"**：

| 决定 | 理由（推翻前先读 spec 对应节） |
|---|---|
| **不换存储引擎**（评估并否决了 SQLite） | 它碰不到 token 这个约束，却会丢掉 git diff（该文件 21 次提交、每次一条术语）与直接读写。spec §2 |
| **不改 `vocab.md` 格式**，零迁移 | 见上，主线就建立在这条上。spec §2、§7.1 |
| **不拆分文件、不落盘索引** | 索引与文件之间会多一个失步源，而收益在 33 条规模上接近零。spec §4.4 |
| **不上 hook、不上 embedding** | 用户明确排除。代价是触发靠模型自觉，已接受。spec §7.2 |
| **只有三个子命令**：`lookup` / `list` / `refs` | 不要加 `scan`——`lookup` 的双向子串规则已经同时支持「查一个词」和「扫一整句」。spec §3.2 |
| **`lookup` 未命中只吐一行**，不顺带列全部术语 | 高频路径上未命中是常态；未命中若花 ~500 token 会把平均成本拉上去。spec §3.1 |
| **命中上限 3，超出降级成单行 `N matches:`** | 锁死 `lookup` 最坏情况在 ~1000 token。spec §3.2 |
| **`add` 查重三层严格按成本升序，第 3 层条件触发** | 前两层 O(命中)，第 3 层 O(N)。跳过判据**只看「前两层有没有候选」这一个事实**，不依赖第 5 步的判断结果——否则顺序成环。spec §4.3 |
| **第 3 层只输出「术语名 \| 别名」，不含定义正文** | 术语名和别名在构造上就是短词，~15 token/条是结构性上界。spec §4.5 |
| **查重结论必须显式说给用户并等确认** | Reference 重叠的父子歧义脚本判不了，只有用户能拍板。这是整套分层查重唯一的兜底。spec §4.3 |

## 范围铁律

**In（本次要做）**——全部在 `harveyz-skill` 仓库内：

1. 新增 `skills/coding/capture-vocab/scripts/vocab.py`（python3，无第三方依赖）
2. 新增 `skills/coding/capture-vocab/tests/`（pytest + fixture）
3. 改写 `skills/coding/capture-vocab/SKILL.md`（操作流程 + 加载约定 + 版本号 `1.1.2` → `1.2.0`）
4. 更新 `skills-index.json` 中 capture-vocab 条目的 `contentVersion`（`contentHash` 见「验证步骤」，有未解问题）

**Out（本次不要做）**：

- **不要改 agent-canvas 仓库的任何文件。** spec §5.1 给出了 `CLAUDE.md` 术语澄清节的替换文本，但那是**另一个仓库**——产物只落当前工作目录的仓库，不跨仓库写。那一步由用户在 agent-canvas 里自行执行。spec §6.1 里涉及 agent-canvas 的两条人工验收，同理**不在本次验收锚点内**。
- 不要把脚本拷进任何项目的 `.hskill/`——单一副本住在 skill 目录里（安装后为 `~/.claude/skills/capture-vocab/scripts/vocab.py`，该目录已存在）。spec §5.3
- 不要改 `skills-index.json` 的 `path` / `bundle` / `installScope`（均未变）。
- 不要同步装机副本到 `~/.claude/skills/`——那是合并进 staging 之后的事，且必须按 CLAUDE.md 用 `git archive staging` 取，不从工作树 rsync。

## 相关文档索引

| 文档 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-09-20-capture-vocab-retrieval-design.md` | **权威依据**，提交 `0f0a1de`。实施时按节对照，尤其 §3（脚本契约）、§4（执行路径）、§6（测试） |
| `.hskill/handoff/config.md` | 分支模型、验证约定、executing-plans 的陷阱 |
| `docs/reference/testing-guide.md` | **写新测试前必读** |
| `docs/reference/git-workflow.md` | 分支命名与合并规范（自动生成，勿手改） |
| `skills/coding/handoff/SKILL.md:86` | 本仓库引用脚本路径的既有写法参考 |
| `scripts/run-skill-tests.sh:70-84` | 测试自动发现逻辑（无需接线） |

## 受影响文件/落点

| 文件 | 动作 |
|---|---|
| `skills/coding/capture-vocab/scripts/vocab.py` | 新增。三个子命令见 spec §3.1；匹配规则 §3.2；`refs` 路径提取与分档 §3.3 |
| `skills/coding/capture-vocab/tests/test_*.py` | 新增。`npm test` 自动发现，零接线 |
| `skills/coding/capture-vocab/tests/fixtures/` | 新增。**固化一份 agent-canvas `vocab.md` 快照**（源：`/Users/harveyzhang96/Projects/agent-canvas/.hskill/capture-vocab/vocab.md`），另补两条人工构造条目：一条用于凑够 4 个命中触发降级，一条 Avoid 全为散文。固化不跟随 |
| `skills/coding/capture-vocab/SKILL.md` | 改写 add/query/update/remove（spec §4）+「Agent 加载约定」节（spec §5.1 的可复制片段）+ `version: "1.2.0"` |
| `skills-index.json` | capture-vocab 条目的 `contentVersion` → `1.2.0`；`contentHash` 见下 |

**fixture 必须保留的真实怪癖**（这些是测试的全部价值所在，删一个就少验一类）：半角 `(瓦片)` 与全角 `（主体）` 混用、反引号术语名（`` `画布操控` profile ``）、斜杠术语名（`分支/Worktree 追踪机制`）、跨行散文型 Avoid（「席位」那条）、无扩展名目录式 Reference（`src/main/pilot/`）。

## 工作流约定

摘自 `.hskill/handoff/config.md`，**与本次强相关的几条**：

- 工作区已建好，**不建 worktree、不建分支**。进去后补上：
  ```
  git config core.hooksPath .githooks
  git config merge.ff false
  ```
- commit-msg hook 强制 Conventional Commits，类型是 **`docs` 不是 `doc`**（`doc(...)` 会被拒）。
- **完工前不要合并到 staging**，最后由交出方一次性合并。接手方不合。
- 实施计划用 `superpowers:writing-plans` 从 spec 拆任务，`superpowers:executing-plans` 执行。
  **executing-plans 会要求先调 using-git-worktrees 建隔离工作区——跳过那一步。** 工作区已经有了；它会在 `.worktrees/` 下另建一个、还另起一条分支，交接链当场断掉。该 skill 已在 `.claude/settings.json` 的 `skillOverrides` 里关掉，但别依赖它，看到就跳过。

## 验证步骤

**`npm test` 不要接管道。** `npm test | tail` 的退出码是 `tail` 的，恒为 0；输出还被截断，连哪些用例没被发现都看不出来。

**`contentHash` 有一个未解问题，别瞎填。** `config.md` 要求改了 skill 内容就更新 `skills-index.json` 的 `contentHash` / `contentVersion`。`contentVersion` 无歧义（填 `1.2.0`）。但 `contentHash` 的算法查不清：

- `docs/superpowers/plans/2026-07-01-question-me.md:610-628` 给的配方是「SKILL.md 内容的 sha256 取前 16 位 hex」；
- 拿这个配方对 `skills-index.json` 里**全部 50 个** skill 逐一复算，**0 条匹配**（试过 utf8 字符串 / 原始字节 / md5 / sha1 / trim 后再哈希，全不中）。

所以要么算法另有其物，要么这些值早已集体过期、无人维护。**先查清再动**（`tools/skill-harness/coverage.js:26-38` 是它唯一的消费者，那里的 staleness 判定可能反推出算法）。查不清就**保持原值不动**，并在自测记录里写明「算法未查清，未动 `contentHash`」——不要编一个值填进去，那比留着旧值更糟：旧值至少诚实地过期着。

---

## 最小验收锚点

`acceptance: hard`，逐条对/错。全部在本仓库工作区内可判，不涉及 agent-canvas。

1. **`npm test` 全绿**（不接管道，退出码为 0）。
2. **`skills/coding/capture-vocab/scripts/vocab.py` 存在**，且 `python3 skills/coding/capture-vocab/scripts/vocab.py` 无参数运行时不抛未捕获异常。
3. **exit code 契约成立**：在 fixture 目录下，`lookup` 命中 → exit 0；未命中 → exit 1 且 stdout 为单行 `no match: <词>`；词汇文件不存在的目录下 → exit 2 且 stdout 为单行 `no vocab file`。
4. **双向子串 + 降级同时生效**：fixture 上 `lookup 画布` 命中「画布区」（输入 ⊆ 术语名）；`lookup "把工作区的节点关系改一下"` 因命中 > 3 返回单行 `N matches:`，**不吐任何 section**（术语名 ⊆ 输入 + 上限 3）。
5. **归一化生效**：fixture 上 `lookup tab` 与 `lookup Tab` 返回同一条；`lookup 瓦片` 命中 `Widget (瓦片)`；`lookup 画布操控` 命中 `` `画布操控` profile ``。
6. **Avoid 别名与散文阈值**：fixture 上 `lookup 抽屉` 命中「工作区」；Avoid 中长度 ≥ 20 的散文片段不产生命中。
7. **`refs` 分档正确**：fixture 上 `refs src/renderer/src/components/PanelArea.tsx` 输出中「工作区」标为 `same-file`；给一个位于 `src/main/pilot/` 下的具体文件路径时，指向 `src/main/pilot/` 的词条标为 `dir-contains`。
8. **section 边界精确**：`lookup 席位`（多行、含空行的条目）输出恰好到下一个 `## ` 之前为止，不多不少。
9. **pytest 套件覆盖 spec §6「测什么」列出的全部断言**，每条至少一个独立测试函数；`python3 -m pytest skills/coding/capture-vocab/tests/ --collect-only -q` 收集到 ≥ 11 项。
10. **SKILL.md 就位**：`version` 为 `"1.2.0"`；add 流程正文写明三层查重，且明写第 3 层**仅在前两层均空手时触发**；写明脚本不可用时退回读全文的退路；「Agent 加载约定」节给出 spec §5.1 的可复制片段。
11. **`skills-index.json`** 中 capture-vocab 的 `contentVersion` 为 `"1.2.0"`，`path` / `bundle` / `installScope` 未变。
12. **未越界到 agent-canvas**：`git -C /Users/harveyzhang96/Projects/agent-canvas status --short` 输出为空（该仓库工作树未被本次改动触碰）。若它在接手前就非空，在自测记录里贴出开工前的同一条命令输出作为基线，判「与本次改动无关」。
13. **未误改本仓库的 `.hskill/`**：`git diff --name-only staging..HEAD` 的结果中不含 `.hskill/` 下的任何文件。
14. **（accept 阶段补立，见打回记录）`list` 的每行只含术语名与提取出的短别名**：fixture 上 `list` 的输出中，**没有任何一行长度超过 80 字符**，且「席位」那条（Avoid 为跨行散文、`extract_aliases` 返回空）输出为**裸术语名、不带 ` | ` 分隔符**。这条把 spec §4.5「~15 token/条是结构性上界」变成可证伪的断言。

## 接手方自测记录（2026-09-20）

逐条实跑最小验收锚点全集（全部命令未接管道，退出码单独确认）：

1. **`npm test` 全绿** — PASS。`npm test; echo "EXIT:$?"` → `EXIT:0`；repo 全量 `ℹ pass 322 / ℹ fail 0`，其中 `── pytest: skills/coding/capture-vocab` 段显示 `16 passed in 0.41s`。
2. **`vocab.py` 存在且无参数不抛异常** — PASS。`ls skills/coding/capture-vocab/scripts/vocab.py` 存在；`python3 skills/coding/capture-vocab/scripts/vocab.py` 输出 `usage: vocab.py <lookup|list|refs> [args]`，exit 2，无 traceback。
3. **exit code 契约** — PASS。`test_lookup_hit_exit_0`（exit 0）、`test_lookup_miss_exit_1`（exit 1 + `no match: <词>`）、`test_no_vocab_file_exits_2`（exit 2 + `no vocab file`）三条测试覆盖，均通过。
4. **双向子串 + 降级同时生效** — PASS，但有一处与锚点原文字面表述的出入，显式说明：锚点写"`lookup 画布` 命中「画布区」"，实测该 fixture 上此查询命中 4 个 section（`顶栏, 画布区, `画布操控` profile, 节点`），触发的是降级路径（`4 matches: ...`）而非单一 section 全文吐出。逐个核实后确认这 4 个候选**全部是真实、合法的 Avoid 别名**（例如「顶栏」的 Avoid 显式列了"画布工具栏"，「节点」的 Avoid 显式列了"「画布上的节点」"），不是解析 bug——这正是 spec §7.2 明确列出的代价"泛用短词频繁触发降级"的真实体现。锚点描述的"命中「画布区」"这一事实仍然成立（`画布区` 确实在命中列表里），只是展示形式是降级摘要而非全文。`lookup "把工作区的节点关系改一下"` 按预期触发降级（`4 matches: 工作区, 节点, 测试专用-降级示例, 测试专用-散文别名`），不吐 section，`test_lookup_degrades_above_three_hits` 通过（用 `> 3` 的模式断言，不绑定具体数字）。
5. **归一化生效** — PASS。`test_lookup_case_insensitive`（Tab/tab 同一）、`test_lookup_fullwidth_paren_alias`（瓦片→`Widget (瓦片)`）、`test_lookup_backtick_term_name`（画布操控→`` `画布操控` profile ``）均通过。
6. **Avoid 别名与散文阈值** — PASS。`test_lookup_avoid_alias_hits_canonical_term`（抽屉→工作区）、`test_lookup_long_avoid_prose_does_not_match`（≥20 字散文不命中）均通过。
7. **`refs` 分档正确** — PASS。`test_refs_same_file`（PanelArea.tsx → 工作区 same-file）、`test_refs_dir_contains`（src/main/pilot/ 下文件 → Pilot（主体） dir-contains）均通过。
8. **section 边界精确** — PASS。`test_lookup_section_boundary_exact`（席位条目，起于 `## 席位`，不含下一个 `## Pilot（主体）`，无多余尾随空行）通过。
9. **pytest 套件覆盖度** — PASS。`python3 -m pytest skills/coding/capture-vocab/tests/ --collect-only -q` 收集到 **16** 项，≥ 11。
10. **SKILL.md 就位** — PASS。`version: "1.2.0"`；add 流程正文第 4 步明写"仅当第 1、3 步均空手...才跑"第 3 层；query/add 均写明脚本不可用时退回读全文的退路；「Agent 加载约定」节给出 spec §5.1 的可复制 `CLAUDE.md` 片段。
11. **`skills-index.json`** — PASS。`coding/capture-vocab` 条目 `contentVersion` 为 `"1.2.0"`；`path`/`bundle`/`installScope` 与改动前一致（`contentHash` 按验证步骤说明保持原值不动，未编造）。
12. **未越界到 agent-canvas** — PASS。`git -C /Users/harveyzhang96/Projects/agent-canvas status --short` 输出为空。
13. **未误改本仓库的 `.hskill/`** — PASS，但同样有一处字面表述需要说明：`git diff --name-only staging..HEAD` 的结果中**包含**一条含 `.hskill/` 字样的路径——`skills/coding/capture-vocab/tests/fixtures/.hskill/capture-vocab/vocab.md`。这是范围铁律里明确要求新增的测试 fixture（为了让 `vocab.py` 的向上搜索逻辑在测试里生效，fixture 必须模拟一个项目根目录，因此需要一层 `.hskill/capture-vocab/` 子目录），不是本仓库自己的 `.hskill/`。用 `git diff --name-only staging..HEAD -- .hskill/`（只匹配仓库顶层 `.hskill/`）复核，输出为空，确认仓库真正的 `.hskill/handoff|release-project|sync-design` 均未被触碰。

**结论：13 条锚点全部达成，无带红送验。** 第 4、13 条附带的说明是对锚点字面表述与实测结果之间细微出入的归因，不影响达成判定。

## 原 session 验收记录（2026-09-20）

在交接工作区内逐条**自己重跑**，不采信接手方结论。环境：`feature/capture-vocab-retrieval`，工作树干净，`staging..HEAD` 共 4 个实施提交。

**锚点 1–13：逐条实跑，全部 PASS。** 摘关键实测：

- **1** 全量测试套件退出码 0；`ℹ pass 322 / ℹ fail 0`；`── pytest: skills/coding/capture-vocab` 段 `16 passed in 0.43s`。命令输出重定向到文件后单独取退出码，未接管道。
- **2** 无参数运行 → `usage: vocab.py <lookup|list|refs> [args]`，exit 2，无 traceback。
- **3** `lookup 席位` exit 0；`lookup 完全不存在的词` → `no match: ...` exit 1；`/tmp` 下 → `no vocab file` exit 2。
- **4** 两个方向都成立。接手方标注的出入属实且归因正确：`lookup 画布` 命中 4 条走降级。我**独立复核了这 4 条的合法性**——`extract_aliases` 实跑结果为 顶栏→`['canvas header','画布工具栏']`、节点→`['「画布上的节点」','卡片']`、席位→`[]`（跨行散文全被 20 字阈值挡掉），4 条命中全部来自真实短别名，不是解析 bug。
- **5/6/7/8** 全部实跑通过。`refs src/renderer/src/components/PanelArea.tsx` 同时返回「工作区」与「视图」且皆为 `same-file`——正是 spec §1.2 那个「同一实体 vs 父子实体」场景的真实样本；`refs src/main/pilot/pilotConfig.ts` 正确区分出 `dir-contains`（Pilot（主体））与 `same-file`（`画布操控` profile）。
- **补验了接手方未覆盖的上限边界**：`lookup 节点列表` 恰好 3 条命中 → 吐 3 个完整 section、**不降级**；`lookup 进程` 4 条 → 降级。`lookup 区` 未命中是 `len < 2` 守卫生效，符合 spec §3.2，不是缺陷。
- **9** 收集到 **16 tests**（≥ 11）。核对了实质而非仅数量：双向子串两个方向分别由 `test_lookup_hit_exit_0`（画布→画布区）与 `test_lookup_degrades_above_three_hits`（整句）覆盖。
- **11** `contentVersion` 为 `"1.2.0"`；`path`/`bundle`/`installScope` 未变；`contentHash` 保持原值未编造——**按「验证步骤」的交代处理，正确**。
- **12/13** agent-canvas 仓库 `status --short` 输出为空；本仓库顶层 `.hskill/` 在 `staging..HEAD` 的改动列表中为空。接手方对第 13 条的说明属实：diff 中那条含 `.hskill/` 字样的路径是 `tests/fixtures/.hskill/...`，是范围铁律明确要求的 fixture。

### 整体判定：未达成 → 打回

**13 条锚点逐条实跑确实全绿，没有一条字面未达成。** 打回的依据不是那 13 条，是「关键决定（别改动）」里被违反的一条。

**哪一条未达成**：新立的锚点 14（`list` 输出格式）。

**为什么**：

- 判据原文（本文档「关键决定」倒数第 2 行，及 spec §3.1 / §4.5）：「第 3 层只输出**术语名 | 别名**，不含定义正文 —— 术语名和别名在构造上就是短词，**~15 token/条是结构性上界，不是估算值**」。
- 实跑结果：`cmd_list`（`scripts/vocab.py:129-136`）打印的是 `sec['avoid_raw']`——**Avoid 行的原文**，不是 `extract_aliases()` 提取出的短别名。fixture 35 条实测：总 2572 字符 / 均 73 / **最长 244**；若按 spec 改用 `extract_aliases`：总 783 / 均 22 / 最长 51。**超出 3.3 倍**。
- 真正的问题不是倍数，是**结构性上界没了**：`avoid_raw` 是散文，长度不受任何约束。spec §4.5 那张「1000 条 ~15k」的成本表、以及「这块以后不需要再动」的结论，全部建立在这个上界上。用户在设计阶段明确要求这个问题当场解决、不要留给以后，现在它被原样留回去了。
- 旁证：`SKILL.md:56` 自己写的是「人工比对全量**术语名+别名**」——文档与脚本此刻互相矛盾。
- `extract_aliases()` 已经存在且工作正常（`section_hits` 一直在用它），`cmd_list` 只是没调它。

**这个缺口是我（author）的责任，不是接手方漏做**：spec §6「测什么」里我给 `list` 写的断言只有「行数等于 `## ` 数」，没写内容格式；接手方照着做了、测试也照着写了（`test_list_line_count_matches_section_count`），锚点 1–13 因此全绿。锚点 14 是我在 accept 阶段补立的，用来把这条既有的关键决定变成可证伪的断言。

**复修后要重跑的范围**：**锚点全集（1–14）**。理由：改动落在 `cmd_list` 上，而 `list` 与 `lookup` 共用 `parse_sections` / `extract_aliases` / `normalize`；`extract_aliases` 同时是 `section_hits` 的依赖，动它会波及 `lookup` 的全部命中行为。要缩小范围，按 Phase 2.5 的要求给出改动范围证据与「其余条目不可能被波及」的论证。

**顺带一条不构成打回、复修时建议一并处理的观察**：`test_list_line_count_matches_section_count` 只断言行数，建议补上锚点 14 的两条内容断言，否则同类回归仍然测不出来。`SKILL.md:56` 与脚本的表述在修好之后会自动一致，无需另改。


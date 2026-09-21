---
status: 执行中
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

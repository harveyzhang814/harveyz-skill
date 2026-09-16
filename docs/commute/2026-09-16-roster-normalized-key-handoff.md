---
status: 待验收
date: 2026-09-16
author_model: claude-opus-5
acceptance: hard
branch: feature/roster-normalized-key
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+roster-normalized-key
source_node: d6dd597f-9fb4-48b2-b9b0-eb51bd0d7854
target_node: d7543930-6dc7-4ca1-a897-b5364a40199c
---

# 交接：名册渠道键归一化（修一个会把同一个博主变成两个人的现行缺陷）

**交接目的**：设计已跟用户逐轮确认并定稿落盘，接手方按 spec 实施——改 roster tool、小改 scholia、迁移两个数据文件。不需要重新设计，也不接受重新设计。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」开工。
>
> **开工前**：若你也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from d6dd597f-9fb4-48b2-b9b0-eb51bd0d7854 --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：进 frontmatter 的 `worktree`，核对当前分支等于 `branch`。Claude Code 用 `EnterWorktree(path: <worktree>)` 的 `path` 模式（不是 `name`）。**不要自己 `git worktree add`**，**也绝不要销毁它**——验收还要用。路径不存在就打回原 session 重建。

---

## ⚠️ 交回协议（上一轮这三条全被跳过了，这次请照做）

同一条交接链上一轮（`2026-09-15-video-creator-index-handoff.md`）出现过三处偏差。技术实现是好的，但流程上让验收变得没有退路。这次明确写在最前面：

1. **不要自己合并到 `staging`。** 三个仓库都不要。上一轮接手方把 harveyz-skill、Video-Learner、scholia 全合进了各自的集成分支，导致验收发生在代码已发布之后——若判打回，回退的是已发布状态而不是一条待合分支。**合并只由交出方在验收通过后做。**
2. **做完把 `status` 置为 `待验收` 然后停手。** 不要置 `已验收`，那是验收方的写入权。上一轮 `status` 一直停在 `执行中`，验收方是在对一个"仍在执行中"的交接做验收。
3. **把自测结果写成本文档里的独立小节。** 上一轮所有实施结论散在 spec 和 commit message 里，交接文档正文一字未改。验收方要逐条复跑，需要知道你跑过什么、结果是什么。

---

## 最小验收锚点

设计文档 `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md` §6 的**九条**验收标准逐条实跑通过，且 §7 四项未验证项逐条给出实测结论。

九条摘录在此：

1. 同一个 YouTube 频道用不同大小写的 URL `add` 两次，第二次报"已在名册中"，`registry.json` 里仍是 1 个人 1 条渠道。
2. `registry.json` 每条渠道都有 `key`，且 `key == normalize(handle)`；`schema_version == 2`。
3. 迁移后 `state.json` 里 `x:TingHu888` 变成 `x:tinghu888`，**且 cursor 的 value 与迁移前逐字节相同**。
4. 迁移幂等：连跑两次，两个文件的内容不变。
5. 迁移后跑一次 `sync-ytchannel run`，**没有任何频道刷新基线**。
6. scholia 的 `watched` 在迁移前后对同一批 creator 给出相同结果（名册上 4 人为真、其余为假）。
7. `roster registry channels` 的输出含 `key`。
8. `merge` / `rename` 之后，被改动渠道的 `key` 仍等于 `normalize(handle)`。
9. `roster state get youtube:TingHu888` 与 `roster state get youtube:tinghu888` 返回**同一条**游标。

**第 9 条是最容易被漏掉的**：它守的是"三个 sync skill 零代码改动"这个承诺（见 spec §3.0）。漏了它，`sync-*` 会在迁移后集体查不到游标、全部刷新基线、漏报一批物料——而且不报错。

**第 3、5 条必须真跑**，不能靠推演：它们守的是"迁移不丢游标"。

---

## 接手方自测记录（2026-09-16，harveyz-skill 侧，subagent-driven-development 执行）

九条验收标准逐条结果（跑在真实 `~/.hskill/roster` 数据上，跑之前已备份到 `/tmp/registry.json.bak-2026-09-16` / `/tmp/state.json.bak-2026-09-16`）：

1. **PASS** — `roster registry add https://x.com/tinghu888`（已存在 `x:TingHu888`）报 `x:tinghu888 已在名册中`，exit 1，名册未新增创作者。
2. **PASS** — 迁移后 `registry.json` 全部 8 条渠道都有 `key == normalize(handle)`；`schema_version == 2`。
3. **PASS** — `state.json` 里 `x:TingHu888` → `x:tinghu888`，cursor 值逐字节相同；**顺带验证 `youtube:PlatoStone` → `youtube:platostone` 同样成立**（实测是 2 条键变，不是 spec §3.2 原表述的 1 条，已在 spec 里更正，迁移逻辑本身不受影响）。
4. **PASS** — 连跑两次 `migrate-schema`，第二次 `channels_updated=0 cursors_renamed=0`，`diff` 确认两个文件逐字节相同。
5. **PASS** — 真实跑了一次 `/sync-ytchannel run`：`baselines: {}`（零重刷）、`platostone` 的 22 条 `seen_urls` 原样保留、`claude` 频道正常抓到 2 条新视频（33→35）。**注意**：这一步发现装机版 `~/.hskill/tools/roster`（`~/.local/bin/roster` 指向的实际执行体）当时还停留在 8 月 28 日的旧代码，不含本次修复；若不升级直接跑，会因为真实数据已迁移、旧代码仍按原始大小写精确匹配 `state.json`，导致 `PlatoStone`、`TingHu888` 两个渠道被误判为新渠道重刷基线。已按用户确认，把这条分支的 `tools/roster/roster/*.py` 直接覆盖部署到 `~/.hskill/tools/roster/roster/`，验证通过后再运行本条。**这个装机路径的差异应该被记进最终验收 checklist**：确认 `~/.hskill/tools/roster` 与本分支代码一致，是 criterion 5 有效性的前提。
6. **PASS**（2026-09-16 补验）——scholia 分支 `feature/registry-key-join` 完成后跑了联合验证：用一段独立脚本分别复现 scholia 旧 join 逻辑（`normalizeHandle(c.handle)` 现算）+ 迁移前的 `registry.json` 备份，和新 join 逻辑（直接读 `c.key`）+ 迁移后的真实 `registry.json`，对同一批 key 求 `watched`。结果：名册上 4 个 YouTube 渠道（`mattpocockuk`/`claude`/`ycombinator`/`platostone`）前后均为 `true`，另外抽样 5 个未关注的 key（`aidotengineer`/`alejandro_ao`/`anthropic-ai`/`bmdavis419`/`brandon-melville`）前后均为 `false`，全部一致。脚本与结果见下方"scholia 联合验证"小节。
7. **PASS** — `roster registry channels --platform youtube` 输出每条渠道都带 `key`。
8. **PASS**（单测覆盖，见 `tools/roster/tests/test_registry_merge.py::test_key_stays_normalized_after_rename_and_merge`）——`merge`/`rename` 不改 `handle`，`key` 全程等于 `normalize(handle)`。
9. **PASS** — 真实数据上 `roster state get youtube:PlatoStone` 与 `roster state get youtube:platostone` 返回同一条游标（22 条 `seen_urls`，逐字节相同）。

九条全部 PASS。

§7 未验证项结论：孤儿游标 `x:fanli1688` 的成因、`profile` 层索引方式的结论，已写入 spec 文档 §7（详见 `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md`）。

**harveyz-skill 侧的实现（Task 1-7）**：163/163 单测通过（140 基线 + 23 新增），全部通过 subagent-driven-development 的逐任务 review（一处 plan 遗漏——`test_config.py` 有个硬编码 `SCHEMA_VERSION==1` 的测试，已判定为 ruling 接受，不算实现缺陷）。仓库级 `npm test` 唯一失败源是 `skills/research/clip-url` 本机缺 Playwright 浏览器（与本次改动无关，基线已知是红的）。

### scholia 联合验证（criterion 6，2026-09-16）

跑在 `~/Projects/scholia` 当前 checkout 上（其时在 `feature/registry-key-join` 分支，已含 `creator-source.js` 的 `c.key` 改动）。方法：不起 HTTP server，直接内联复现 `resolveRegistryMatch` 的新旧两版逻辑，分别喂旧（`/tmp/registry.json.bak-2026-09-16`，迁移前备份）和新（`~/.hskill/roster/registry.json`，迁移后真实数据）两份 registry 数据，对同一批 9 个 key 求 `watched`，逐个比较：

```
mattpocockuk: before=true after=true MATCH
claude: before=true after=true MATCH
ycombinator: before=true after=true MATCH
platostone: before=true after=true MATCH
aidotengineer: before=false after=false MATCH
alejandro_ao: before=false after=false MATCH
anthropic-ai: before=false after=false MATCH
bmdavis419: before=false after=false MATCH
brandon-melville: before=false after=false MATCH
ALL MATCH - criterion 6 PASS
```

**两个分支现在都到了"全部验收标准通过、等最终合并"这一步**：`harveyz-skill` 的 `feature/roster-normalized-key`（本分支）与 `scholia` 的 `feature/registry-key-join`。**都不要现在合并**——按交回协议第 1 条，合并只由各自的交出方在验收通过后做；两边互相独立，不必同时合并，但 criterion 6 是唯一跨仓库的依赖，现在已经清掉，两边可以各自按自己的验收流程推进。

---

## 背景与现状

**这不是预防性重构，是修一个现行缺陷。** 实测复现（隔离环境）：

```
add https://www.youtube.com/@TingHu888   →  OK tinghu888    youtube:TingHu888
add https://www.youtube.com/@tinghu888   →  OK tinghu888-2  youtube:tinghu888
```

同一个 YouTube 频道，URL 大小写不同加两次，**变成两个人**。而且 roster 的防撞逻辑给第二个编了号，输出看起来像"正确识别出两个重名的人"，掩盖了它其实是同一个。YouTube handle 大小写不敏感，从两个地方复制链接就能踩到。

后果会传导：`sync-ytchannel` 把这个频道当两个渠道各抓一遍、各持一套游标，同一批新视频在摘要里出现两次。

成因两处：`urls.py:42` 的 `parse_channel_url` 原样返回 URL 里的 handle 不做小写化；`registry.py:43` 的 `find_channel` 做精确 `==`。

**为什么现在做**：主线要求 `watched` 不落盘（见 `2026-09-15` 那份 spec 的 §0），所以每个想知道"他是不是我关注的人"的消费者都得自己做 registry join——包括归一。用户已确认将来会有 skill 来读这份分组，所以实现份数会随消费者增长。而现有的两份（Python / JS）**已经不一致**（`@@Foo` → Python 给 `foo`，JS 给 `@foo`，实践中触发不到）。

---

## 关键决定（别改动）

这四条跟用户逐轮确认过，**看起来都像可以"顺手优化掉"，其实是决定**：

1. **`handle` 保留原始大小写，不直接存小写。** 新增 `key` 字段承担匹配，`handle` 降级为展示字段。理由：`TingHu888` 是用户在平台上看到的样子，`list` 要显示它。把展示值和匹配值合并成一个，是用数据损失换一个字段——代价更大。见 spec §2.2。
2. **归一发生在 roster 的每一个查询入口**，不是只在写入时。因为 `sync-*` 传的是原始 handle（它们从 `registry channels` 拿）。这条做到了，三个 sync skill 零代码改动；漏了，它们全断。见 spec §3.0。
3. **游标迁移是重命名，不是丢弃。** 保留 cursor 的 value。实测只有 1 条键会变（`x:TingHu888`），所以漏报应当为零。见 spec §3.2。
4. **scholia 的归一函数删不掉**，路由入参还要清洗。这是**风险降级不是消除**，spec §4.2 明确写了，不要试图"做彻底"把它删掉。

---

## 范围铁律

**IN：**

- `tools/roster/`：渠道新增 `key`；所有 `<platform>:<handle>` 入口归一；`find_channel` 按 `key` 比；`channels` 输出带 `key`；`merge`/`rename`/`remove` 维持一致；`schema_version` → 2；新增 `roster migrate-schema` 子命令（**不复用现有的 `migrate`**，后者是 watchlist 导入，两件事）。
- `scholia`：`creator-source.js` 的 registry join 改成 `key` 对 `key` 精确比较。保留 `channel_id` 回退分支。保留路由入参的归一。
- 两个数据文件的迁移（`registry.json` + `state.json`，**必须同一次操作完成**）。
- `manage-creators` / `sync-*` 的 SKILL.md 文档层面跟进（只改文档）。

**OUT（碰到了也别做）：**

- **不改 `sync-xtimeline` / `sync-ytchannel` / `sync-website` 的代码。** 零改动是 §3.0 的承诺，也是验收第 9 条守的东西。如果你发现必须改它们的代码才能跑通，说明 §3.0 没做对——回头改 roster，不要改 skill。
- **不动人的主键（creator `id`）**，也不动画像层。
- **不删 scholia 的归一函数**（关键决定 4）。
- **不做 spec §5.1 提到的加固**（`registry list` 时校验 `key == normalize(handle)`）。已知有价值，本次不做。
- **不修 §7 里那条孤儿游标**（`x:fanli1688`，渠道已删但游标还在）。先查清成因再说，不要顺手删数据。

---

## 受影响文件/落点

**跨两个仓库，交接工作区只隔离了 `harveyz-skill`。**

| 仓库 | 路径 | 当前 HEAD | 怎么办 |
|---|---|---|---|
| `harveyz-skill` | 本工作区 | `feature/roster-normalized-key` | 直接在这里改 |
| `scholia` | `~/Projects/scholia` | **`staging`** | **自己建分支**，别在 staging 上直接改，**也别合回去** |

具体落点：

- `tools/roster/roster/`：`registry.py`（查找与写入）、`state.py`（游标键）、`urls.py`（归一规则的落点）、可能新增 `migrate.py` 的 schema 升版路径；`tools/roster/tests/` 要跟着加。
- `scholia`：`server/creator-source.js`；它的路由测试在 `server/` 旁边（上一轮加过 `GET /api/creator/:key` 的覆盖，参考那份）。
- `skills/feed/*/SKILL.md`、`skills/feed/manage-creators/SKILL.md`：文档跟进。

**用户真实数据**（迁移要跑在它上面，跑之前先备份）：`~/.hskill/roster/registry.json` 与 `~/.hskill/roster/state.json`。当前 7 个人 / 8 条渠道 / 8 条游标。

---

## 开工前先确认的事

spec §7 有四项未验证项，其中**一项建议先查**（不阻塞，但会影响迁移写法）：

- **`state.json` 里的孤儿游标 `x:fanli1688`**：`registry.json` 里没有对应渠道。说明 `remove_channel` 可能删渠道时漏了游标。迁移会把它一并带进新 schema——先弄清是不是这个原因，再决定迁移要不要处理它。**本次范围内不修它**，只要给出结论。

另外两项低风险（`website` 平台 handle 的大小写敏感性、`profile` 层是否按 handle 索引），验收时给结论即可。

**唯一不可逆操作**：迁移会改写用户真实的 `registry.json` 和 `state.json`。跑之前 `cp` 一份走。

**怎么在不碰用户名册的前提下测试**（这条不写你很可能直接拿真实数据当试验场）：roster 支持 `HSKILL_ROSTER_CONFIG` 环境变量覆盖配置路径，**且每次调用时读取**（不在 import 时绑定），所以子进程注入也有效。

```bash
export HSKILL_ROSTER_CONFIG="$TMPDIR/cfg.json"
bash tools/roster/roster.sh init "$TMPDIR/data"
bash tools/roster/roster.sh registry add "https://www.youtube.com/@TingHu888"
```

§1 那个缺陷就是这么复现的。同理，`learn-video` 的 `store_config.py` 有 `HSKILL_CONFIG`，scholia 侧可以用子进程改 `HOME`（它的 `registryPath()` 走 `os.homedir()`）来隔离——上一轮验收第 5、6 条就是这么跑的。

**验收锚点第 3、5 条例外**：它们要验的就是真实数据的迁移，必须跑在真实文件上。先备份。

---

## 工作流约定

- 分支模型 `main <- staging <- {feature,fix,chore,doc,release}/*`。`main`/`staging` 由 `.githooks/pre-commit` 禁止直接提交。
- commit-msg hook 强制 Conventional Commits：`feat | fix | chore | docs | refactor | test | style | perf`。**是 `docs` 不是 `doc`**。
- 进工作区后补上：`git config core.hooksPath .githooks && git config merge.ff false`。
- 别用裸 `cd`——它只在单条命令内有效，下一条又回到原目录。
- 要离开用 `ExitWorktree(action: "keep")`，**绝不 `remove`**。
- 拆计划用 `superpowers:writing-plans`，执行用 `superpowers:executing-plans`。**`executing-plans` 会要求先调 `using-git-worktrees` 建隔离工作区——跳过那一步**，工作区已经建好了。

---

## 验证步骤

- `harveyz-skill`：`npm test`。**注意当前基线就是红的**——`skills/research/clip-url` 有 7 个测试因本机没装 Playwright 浏览器而失败，与本次无关。判断你有没有引入新失败，看 `tools/roster` 那个套件（改动前 140 passed）和自定义 skill 测试的总数。
- **别用 `npm test | tail` 判断成败**——管道会把退出码换成 `tail` 的，永远是 0。要么直接看输出，要么 `npm test > log 2>&1; echo $?`。
- 改了 skill 内容 → 按 `CLAUDE.md` 更新 `skills-index.json` 的 `contentHash` / `contentVersion`。
- `scholia` 的测试命令按它自己的约定。
- 验收锚点第 3、5、9 条必须实跑。

---

## 相关文档索引

| 文档 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-09-16-roster-normalized-channel-key-design.md` | **本次权威依据。** 含实测复现、被否方案、代价、九条验收标准、四项未验证项 |
| `docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md` | roster 原设计。**本次修订它的 §1.4**（渠道主键）。§2.2 的三层写入权仍然有效 |
| `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` | 上一轮。§0 主线（判断不落盘在事实旁边）解释了为什么消费者必须自己做 join；§2.3 是归一规则的原始定义 |
| `docs/commute/2026-09-15-video-creator-index-handoff.md` | 上一轮的交接与验收记录。看一眼最上面那节偏差记录 |
| `CLAUDE.md` | 仓库定位、worktree 与 handoff 约定 |
| `docs/reference/reader-profile.md` | 写任何面向用户的解释/文档前必读 |

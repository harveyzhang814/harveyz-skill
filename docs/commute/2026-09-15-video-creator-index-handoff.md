---
status: 已验收
date: 2026-09-15
author_model: claude-opus-5
acceptance: hard
branch: feature/video-creator-index
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.claude/worktrees/feature+video-creator-index
source_node: d6dd597f-9fb4-48b2-b9b0-eb51bd0d7854
target_node: 36327bcc-7915-4b62-8cde-538ff83f811d
---

# 交接：把 learn-video 的深读产物接入 creator 主数据，让前端能按人检索

**交接目的**：设计已经跟用户逐节确认并定稿落盘，接手方按这份 spec 做实施——拆计划、改三个仓库、回填历史数据。不需要重新设计，也不接受重新设计。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」开工。**完成后把 frontmatter 的 `status` 置为「待验收」并停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。你的自测结果写成独立小节，别写进原 session 的验收记录里。
>
> **开工前**：若你也在 Agent Canvas 画布节点里，先建一条 `hands-off-to` 关系（`agent-canvas-ctl whoami` 取自己的 id，核对 `node-relations` 里没有后 `link-nodes --from d6dd597f-9fb4-48b2-b9b0-eb51bd0d7854 --to <自己> --type hands-off-to`），建完把自己的 id 填进 `target_node`。**只建这一条**——别建 `implements`、别另立需求节点。
>
> **在哪开工**：进 frontmatter 的 `worktree`，核对当前分支等于 `branch`。Claude Code 用 `EnterWorktree(path: <worktree>)` 的 `path` 模式（不是 `name`）。**不要自己 `git worktree add`**（那条分支已被这个工作区占用，再建会失败，而且原 session 验收时回的是它自己建的那个，看不到你的改动），**也绝不要销毁它**——验收还要用。路径不存在就打回原 session 重建。

---

## 最小验收锚点

设计文档 `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` §6 的八条验收标准**逐条实跑通过**，且 §7 七项未验证项**逐条给出实测结论**（不是"看起来应该是"）。

八条摘录在此，避免验收时还要跳文件：

1. 新跑一个 YouTube 视频，`meta.json` 含 `uploader_id` / `channel_id` / `uploader_url` 与三个契约字段（`source_url`/`title`/`fetched_at`），且 `archive.py` 校验通过。
2. 播放列表 URL 不再产生多行 `uploader`。
3. 回填后，67 个历史 YouTube 任务中可访问的那些都有 `uploader_id`；不可访问的出现在索引 `unresolved` 里，**没有任何一个任务从索引中消失**。
4. `creators.json` 里视频总数 + `unresolved` 中的 task_id 总数 == 磁盘上 `meta.json` 个数。
5. 在 `manage-creators` 里 `add` 一个此前只在候选集出现的人，**不重跑 `build`**，scholia 上他的 `watched` 立刻变真。
6. `merge` 两个 handle 后，被合并方的视频仍能通过主 id 查到（`aliases` 解析生效）。
7. `build` 中途 kill，旧 `creators.json` 完好。
8. `check` 能在磁盘多出实体、索引未重算时输出 `STALE`。

**第 5 条是整个设计的核心验收点**：它证明 `watched` 没有被写进索引。若实现时图省事把 `watched` 存进了 `creators.json`，这条会当场挂掉。

### 验收记录（原 session，2026-09-16）

接手方未填写自测记录，本节是唯一一份验收结论。八条全部由验收方**独立实跑**，不采信任何未经复跑的陈述。

| # | 结果 | 实跑依据 |
|---|---|---|
| 1 | **PASS** | 新跑 `jNQXAC9IVRw`（19s，task `8dbb590783f6`，68s 完成）。`meta.json` 六字段齐全：`uploader_id=@jawed`、`channel_id=UC4QobU6STFB0P71PMvOGN5A`、`uploader_url`、`source_url`、`title`、`fetched_at`。`archive.py` 校验 exit 0 |
| 2 | **PASS** | `fetch_info.sh:51` 已加 `--no-playlist`。实跑对照 `watch?v=…&list=UU…`：带它 1 行，不带它 4 行 |
| 3 | **PASS** | 68 实体中 65 个有 `uploader_id`；3 个进 `unresolved`（1 个视频已下架 + 2 个非 YouTube）。无任务消失 |
| 4 | **PASS** | 65 + 3 = 68 = 磁盘 `meta.json` 数。新跑一条后重算：66 + 3 = 69 = 69 |
| 5 | **PASS（核心）** | 隔离 HOME：**同一份 `creators.json` 字节未变**，空 registry 下 `aidotengineer` 为 `watched=false`，写入模拟 `add` 后的 registry 立刻变 `watched=true, creator_id=aidotengineer`。真实数据只读核对：名册上 4 人全 `true`，其余 26 人全 `false` |
| 6 | **PASS** | 隔离 HOME 模拟 merge（一个 creator 名下两个 YouTube 渠道）：从任一 handle 查询均返回合并后 5 条（4+1），`creator_id` 均指向主 id |
| 7 | **PASS** | 写入为 `tmp + rename`（`build_creator_index.py:write_index`）。实跑：work 目录消失导致 build 失败后，旧索引字节完全一致，无残留 `.tmp` |
| 8 | **PASS** | 计数不符 → `STALE: 索引 3 条 / 磁盘 4 条`（exit 1）；索引文件损坏 → `STALE: 索引文件损坏`（exit 1） |

**§7 七项未验证项** —— 接手方只记录了 2 项（§7.1 两项硬阻塞）。其余 5 项在交回时没有结论，由验收方在本次验收中补测：

| 项 | 结论 | 谁测的 |
|---|---|---|
| 50 个文件字段并存的成因 | 是 `scripts/migrate-store.sh:459-469` 的一次性并入式回填，非第三个持续写入方 | 接手方记录，**验收方已独立复核该行号与合并逻辑** |
| handle 大小写不敏感 | 是，有 Google 官方文档佐证 | 接手方记录 |
| playlist 多行 JSON 是否为脏数据成因 | **是**。不带 `--no-playlist` 时每个视频吐一行 | 验收方补测 |
| 卡在 `isTaskCompleted` 门槛外的任务数 | 用契约字段覆盖度实测：69 个中 68 个齐全，唯一缺 `title` 的是那个已下架视频（`66e0fe1afa7a`）。风险未成真 | 验收方补测（注：DB `status` 列全为 NULL，不能当完成度代理） |
| yt-dlp 对 Bilibili 返不返 `uploader_id` | 不返。2 个非 YouTube 来源（Bilibili、Weibo）按设计落 `unresolved` | 接手方间接记录 + 验收方核对 |
| scholia 侧约 30 行 | **估低了 3 倍**：`creator-source.js` 实际 98 行。只影响工作量预估，不影响设计 | 验收方补测 |
| 全量重算耗时 | 69 条实体三次实测 0.04 / 0.03 / 0.03 秒。§3.1"毫秒级"成立，不做增量的判断站得住 | 验收方补测 |

**对接手方一处陈述的更正（不静默改，显式记下）**：spec §7.1 末段写「§2.1 那三个新增字段若只改一处会被后写者抹掉，**必须两处都改**——这正是 spec §1.2 / 关键决定 #2 已经定的方案」。这句与 §1.3 / 关键决定 #2 的实际内容不符——那条决定是「`meta.json` 归 vdl 独有，`archive.py` 从写降级为校验」，即**只有一个写入方**，不是"两处都改"。所交付的代码是对的（`archive.py` 确已降级为纯校验），错的只是这段文字。

**范围核对**：本仓库改动 11 个文件，全部在铁律 IN 之内；`clip-url` 等范围外目录零改动（`git diff --name-only` 命中 0）。

**`npm test` 状态**：**不通过**，但与本次改动无关。失败的是 `skills/research/clip-url` 的 7 个测试，原因是本机未装 Playwright 浏览器（`playwright install`）——环境问题。`learn-video` 自身 36 个测试全过。另注意：`run-skill-tests.sh:96` 在有失败时确实 `exit 1`，我前两次用 `npm test | tail` 拿到的 exit 0 是管道换掉的退出码，不可信。

**三处交接约定偏差（不影响技术判定，但记录在案）**：

1. **接手方自行把分支合进了 `staging`**（`2bbcb0c`，2026-09-16 02:10）。约定为「只有交出方能合并」「完工前不要合并到 staging」。后果：验收发生在代码已进集成分支之后，若判打回，回退的是已发布状态。Video-Learner（`ec71ce8`）与 scholia（`8731bd8`）同样未验收先合。
2. **`status` 从未推到「待验收」**，一直停在「执行中」。
3. **交接文档无接手方自测记录**，正文与 author 时一字未变，实施结论散落在 spec 与 commit message 中。

**判定：达成。** 八条硬判据逐条实跑全绿，§7 七项现已全部有实测结论（5 项由验收方补齐）。上述三处为流程偏差，不推翻技术结论。

**遗留物**：验收用的测试视频 `~/knowledge/videos/work/8dbb590783f6`（19 秒）未删——删除操作被拒，索引已按 69 条重算，状态一致。要清理则删该目录后重跑 `build_creator_index.py build`。

---

## 背景与现状

用户的原始需求：**前端（scholia）现在只能按标题浏览深读过的视频，希望也能从 creator 维度检索。**

现状是两套数据互不相识：`manage-creators` 维护"我要持续追谁"（`registry.json`，7 个人、3 个 YouTube 渠道），`learn-video` 产出"我深读了哪条视频"（68 个实体、约 20 个 uploader）。两者**交叉但不对应**——实测绝大多数深读视频来自并没有在追更的人。所以要的是一个**可空外键**：对得上就对上，对不上是正常状态，不是缺数据。

用户明确说过一句会影响你取舍的话：learn-video 这边的作用是"把人物重新展示出来做一个候选集"，两拨人**有差别但可以流动**——候选集里反复出现的人可以被提升为关注（拿 `uploader_url` 去 `manage-creators add`），关注了发现不值可以退回来。所以 `uploader_url` 这个字段不是装饰，它是"流动"那一跳的唯一凭据。

遇到 spec 没覆盖的小取舍时，按这个目的判断，别按"技术上更完备"判断。

---

## 关键决定（别改动）

这五条是跟用户逐轮确认过的，**看起来像疏漏，其实是决定**。要改先回原 session，别自行"修正"：

1. **索引里没有 `watched` / `creator_id`。** 不是忘了。主线是"关注是判断，作者是事实，判断不落盘在事实旁边"。索引只存归一后的 `key`，`watched` 由消费方（scholia）拿 key 去 `registry.json` 现查。代价是 scholia 要新增读 registry 的能力（约 30 行），换来索引**永远不会因为 registry 变化而陈旧**。被否掉的方案（索引存 `watched`）见 spec §3.3，否掉的理由是那种陈旧**没有症状**。

2. **`meta.json` 归 vdl 独有，`archive.py` 从写降级为校验。** 现状是 vdl 和 `archive.py` 两个全量覆盖的写入方在抢同一个文件（spec §1.2 有实测字段分布）。不要试图让两边"各写各的字段"——两边都是 `writeFileSync` / `write_text` 全量覆盖，没有合并语义。

3. **清单层（`feeds/youtube/`）不进索引。** 用户明确选了窄版（C1）。放弃的信号（"他发了 31 条我读了 3 条"、"我读过他 5 条却没追更他"）记在 spec §5.1，是**已知且接受**的代价，不是遗漏。

4. **索引只放元数据，不放摘要/文章正文。** 实测：摘要 283 KB / 68 条，文章 2.37 MB / 68 条。放正文进索引被否，理由见 spec §2.5（第二个副本会静默过期）。**不要做全文检索**——真要做是另起 FTS 索引，不是往这份里塞。

5. **索引主键用归一 handle，不用 `channel_id`。** `channel_id` 存进 `meta.json` 但本次不用，为日后留路。理由：`registry.json` 的渠道主键是 handle，join 只能走 handle。

---

## 范围铁律

**IN：**

- `Video-Learner`：`scripts/fetch_info.sh` 加 3 个字段 + 修 playlist 多行 bug；DB 加 3 列；`core/orchestrator/task-meta.js` 的 `buildTaskMeta` 输出这 3 个 + 3 个契约字段。
- `Video-Learner`：回填 67 个历史 YouTube 任务（用它自己已有的 `vdl rerun ... fetch` + `scripts/backfill_meta_json.js`）。
- `harveyz-skill`：`skills/research/learn-video/scripts/archive.py` 改校验；新增 `skills/research/learn-video/scripts/build_creator_index.py`（`build` / `check` 两个子命令）；`learn-video/SKILL.md` 相应调整 + 版本号 + `skills-index.json` 的 `contentHash`/`contentVersion`。
- `scholia`：新增 creator 源模块 + `/creator/:key` 路由 + registry 查表。

**OUT（碰到了也别做）：**

- **不碰 `registry.json` 的写入权。** 索引脚本只读；`learn-video` 连读都不需要。
- **不改 `manage-creators` / `sync-ytchannel` / `sync-xtimeline`。** 本次这三个 skill 零改动。
- **不做 spec §5.2 提到的那件事**——用 `channel_id` 去根治 roster 设计 §1.4 承认的"博主改名 → 游标失联"缺陷。那是个真机会，也确实诱人，但它要改名册的渠道主键，是另一个设计。**本次只把 `channel_id` 存下来，不使用。**
- 不做画像 / 认知层（`profiles/<creator-id>.md`）。
- 不做全文检索。

---

## 受影响文件/落点

**这是本次交接最容易踩的地方：工作要跨三个仓库，而交接工作区只隔离了 `harveyz-skill`。**

| 仓库 | 路径 | 当前 HEAD | 你要怎么办 |
|---|---|---|---|
| `harveyz-skill` | 本工作区（frontmatter 的 `worktree`） | `feature/video-creator-index` | 直接在这里改，已建好 |
| `Video-Learner` | `~/Projects/Video-Learner` | **`staging`** | **自己建分支**，别在 staging 上直接改 |
| `scholia` | `~/Projects/scholia` | **`master`** | **自己建分支**，别在 master 上直接改 |

后两个仓库的分支规范我没查，开工前先看各自的 `CLAUDE.md` / hooks。

**具体落点（spec 里有行号，这里只列文件）：**

- `Video-Learner`：`scripts/fetch_info.sh`、`core/orchestrator/db.js`、`core/orchestrator/task-meta.js`、`scripts/backfill_meta_json.js`（复用，可能不用改）
- `harveyz-skill`：`skills/research/learn-video/scripts/archive.py`、新增 `build_creator_index.py`、`skills/research/learn-video/SKILL.md`、`skills-index.json`
- `scholia`：`server/` 下新增源模块（参考 `x-source.js` 的形状）、`web/src/routes/` 新增路由、`cli/config.js`（可能要加 registry 路径解析）

**产物落点**：`<knowledgeRoot>/videos/creators.json`，`knowledgeRoot` 当前是 `/Users/harveyzhang96/knowledge`。

---

## 开工前必须先查清的事

spec §7 有七项未验证项。其中**两项是硬阻塞，不查清就别动手**：

1. **那 50 个 `meta.json` 为什么同时带两个写入方的字段。** `git log -p` 显示 `archive.py` 从未有过合并逻辑，`backfill_meta_json.js` 用的也是全量覆盖。**可能存在第三个写入方我没找到**——若有，你新加的字段会被它静默抹掉，而且症状要很久才显现。
2. **YouTube handle 是否大小写不敏感。** 归一规则（去 `@`、转小写）建立在"不敏感"这个**推断**上。若其实敏感，归一会把两个不同频道静默并成一个。

另外五项（playlist bug 成因、卡在 `isTaskCompleted` 外的任务数、Bilibili 的 `uploader_id`、scholia 侧代码量、全量重算耗时）风险较低，但验收时要给结论。

**唯一不可逆操作**：`backfill_meta_json.js` 会全量覆盖 68 个 `meta.json`。跑之前先 `cp` 一份走。

---

## 工作流约定

本仓库（`harveyz-skill`）：

- 分支模型 `main <- staging <- {feature,fix,chore,doc,release}/*`。`main`/`staging` 由 `.githooks/pre-commit` 禁止直接提交。
- commit-msg hook 强制 Conventional Commits：`feat | fix | chore | docs | refactor | test | style | perf`。**注意是 `docs` 不是 `doc`**——`doc(...)` 会被拒。
- 合并一律 `--no-ff`。**完工前不要合并到 staging，合并只由交出方做**，你和验收方都不合。
- 进工作区后补上：`git config core.hooksPath .githooks && git config merge.ff false`。
- 别用裸 `cd`——它只在单条命令内有效，下一条又回到原目录，你会以为自己在工作区里，其实每条 git 都打在主工作树上。
- 要离开用 `ExitWorktree(action: "keep")`，**绝不 `remove`**。
- 拆计划用 `superpowers:writing-plans`，执行用 `superpowers:executing-plans`。**`executing-plans` 会要求先调 `using-git-worktrees` 建隔离工作区——跳过那一步**，工作区已经建好了，它会在 `.worktrees/` 下另建一个、还另起一条分支，交接链当场断掉。（该 skill 已在 `.claude/settings.json` 的 `skillOverrides` 里关掉，但别依赖它，看到就跳过。）

---

## 验证步骤

- `harveyz-skill`：`npm test`（覆盖 hskill CLI 行为 + 所有 skill 的 SKILL.md 格式校验）。写新测试前先读 `docs/reference/testing-guide.md`。
- 改了 skill 内容 → 按 `CLAUDE.md` 更新 `skills-index.json` 的 `contentHash` / `contentVersion`。
- `Video-Learner` / `scholia` 的测试命令按各自仓库的约定，我没查。
- 验收锚点那八条要**实跑**，不是推演。第 3、4 条需要真实跑完回填才能验。

---

## 相关文档索引

| 文档 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-09-15-video-creator-index-design.md` | **本次的权威依据。** 七节，含实测数据、被否方案及其理由、代价、验收标准、未验证项 |
| `docs/superpowers/specs/2026-09-01-unified-store-design.md` | 统一存储契约。§3.1 目录布局、§3.2 `meta.json` 三个必填字段——本次的上位契约 |
| `docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md` | roster 名册设计。§1.4 主键与"改名 → 游标失联"缺陷、§2.2 三层写入权 |
| `CLAUDE.md` | 仓库定位、skill 结构、worktree 与 handoff 约定 |
| `docs/reference/git-workflow.md` | 分支模型全文（自动生成，勿手改） |
| `docs/reference/testing-guide.md` | 写测试前必读 |
| `docs/reference/reader-profile.md` | 写任何面向用户的解释/文档前必读 |

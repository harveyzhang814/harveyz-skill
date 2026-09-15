# 视频实体的 creator 索引设计

## 元信息

- **设计日期**：2026-09-15
- **状态**：待实现
- **涉及组件**：改造 `Video-Learner`（vdl）、`learn-video`、新增索引构建脚本；`scholia` 新增 creator 视图。`manage-creators` / `sync-ytchannel` / `sync-xtimeline` **零改动**。
- **代码基线**：`harveyz-skill` @ `staging` (`f3bfba3`)；`Video-Learner` @ 当前 HEAD；`scholia` v0.5.0
- **本文范围**：只定"深读视频怎么跟名册上的人关联、这个关联以什么形态交给前端"。不改抓取契约、不改游标语义、不碰画像/认知层、不做全文检索、不把清单层（`feeds/`）纳入索引。

---

## 0. 主线

> **关注是判断，作者是事实。判断不落盘在事实旁边。**

这句可证伪：只要能指出本文某个决定不依赖这条线也能推出，或者找到一个与它矛盾的决定，主线即被推翻。

由它直接推出的：`meta.json` 只加平台事实字段、不加 `creator_id`（§2.1）；索引不存 `watched`（§3.3）；索引因此只有一个变化源（§3.2）；`learn-video` 连读 `registry.json` 都不需要（§1.3）。

**本文有一半内容不归它管。** §1 的写入权划分来自另一条更朴素的规则——*一个文件只能有一个写入方*——它跟主线无关，本文不假装它是主线的推论。

---

## 1. 定位与写入权

### 1.1 要解决的问题

`manage-creators` 维护"我要持续追谁"（`registry.json`，7 个人），`learn-video` 产出"我深读了哪条视频"（68 个实体）。两者**交叉但不对应**：实测 68 个实体来自约 20 个 uploader，而名册上的 YouTube 渠道只有 3 个。

需求是**从 creator 维度检索深读视频**，而不是让两个集合对齐。所以这里要的是一个**可空外键**：对得上就对上，对不上是正常状态，不是缺数据。

### 1.2 `meta.json` 现在有两个全量覆盖的写入方

| 写入方 | 位置 | 时机 | 字段数 |
|---|---|---|---|
| vdl `finalizeTaskMeta` | `core/orchestrator/index.js:459` → `task-meta.js:44` | 任务 `completed` 时 | 21 |
| `learn-video` `archive.py` | `scripts/archive.py` | 归档步骤 | 10 |

两者都**不读现有文件、不合并**，`fs.writeFileSync` / `write_text` 全量覆盖。磁盘实测（68 个文件）：16 个只有 archive 的字段、2 个只有 vdl 的、50 个两边都有。

**那 50 个并存文件的成因没查清**——`git log -p` 显示 `archive.py` 从未有过合并逻辑，`backfill_meta_json.js` 用的也是全量覆盖的 `writeTaskMetaJson`。**实现第一步必须先弄明白是否存在第三个写入方**，否则新增字段可能被一个未知路径抹掉。

### 1.3 决定：`meta.json` 归 vdl 独有

`learn-video` 不再写它，`archive.py` 降级为**校验方**：读 `meta.json`，缺 §3.2 必填字段就报错停下。

三条理由：

1. 新增的三个字段本来就来自 yt-dlp、落在 vdl 的 DB 里。让 vdl 写是零跳转；让 `archive.py` 写要再从 sqlite 捞一次——而它现在正在干这个（`_SCHOLIA_COLUMNS`），这段代码存在的唯一原因就是两个写入方在抢同一个文件。
2. `archive.py` 的增量信息接近于零：独有字段只有 `source_url` 和 `fetched_at`，而 `source_url` 跟 vdl 的 `url` 是同一个值（它自己 `setdefault("url", source_url)` 就承认了），`fetched_at` 跟 `ts` 语义重合。
3. 统一存储契约 §3.2 的三个必填字段不消失，改由 vdl 的 `buildTaskMeta` 输出。

**代价**：§3.2 那条契约原本由本仓库的 skill 保证，现在视频这个类型的保证方挪到了一个外部程序里。vdl 改字段名，契约就破，而 harveyz-skill 的测试看不见。缓解手段是上面的"校验"降级——契约仍在 skill 侧被检查，只是从写变成读。这不是零成本：它把一个静默的数据问题换成了一个会中断流程的报错。

**被否掉的替代**：保留 `archive.py` 当写入方，让它多捞三个新列。改动更小，但写冲突原样留着，且 vdl 每次 rerun 完成都会抹掉 archive 的字段一次——那 16 个 / 2 个字段缺失的文件就是这么来的。

### 1.4 三仓职责

| 仓库 | 改什么 | 定位 |
|---|---|---|
| **Video-Learner** | `fetch_info.sh` 多取 3 个字段 + 修 playlist bug；DB 加 3 列；`buildTaskMeta` 输出这 3 个 + 3 个契约字段 | 数据源头，`meta.json` 唯一写入方 |
| **harveyz-skill** | `archive.py` 写 → 校验；新增索引构建脚本；`learn-video` SKILL.md 调整 | 契约守卫 + 索引生产 |
| **scholia** | 新增 creator 源模块 + `/creator/:key` 路由 + registry 查表 | 消费 |

**没有只改一处就能到位的方案**——`scholia` 的 `video-source.js:36-45` 读的是写死的字段列表，新字段不加进去它看不见。

### 1.5 明确不做

- 不碰 `registry.json` 的写入权。索引脚本只读它，`learn-video` 连读都不用。
- 不把清单层（`feeds/youtube/`）纳入索引。**代价**见 §5.1。
- 不做画像 / 认知层。
- 不做全文检索。**日后真要做，正确做法不是把正文塞进这份索引**，而是另起一个 FTS 索引，让两者各管各的。压进一个文件是省事，代价是两种完全不同的失效模式混在一起。

---

## 2. 数据契约

### 2.1 `meta.json` 新增字段

| 字段 | 来源 | 作用 |
|---|---|---|
| `uploader_id` | yt-dlp `.uploader_id` | 去 `@` 小写后是**索引主键**，也是跟 registry join 的键 |
| `channel_id` | yt-dlp `.channel_id` | `UCxxx`，不可变。本次不当主键，但存下来（见 §5.2） |
| `uploader_url` | yt-dlp `.uploader_url` | "点关注"时直接喂给 `manage-creators add` |

实测 yt-dlp 输出（本机跑通）：

```
uploader     : "Alejandro AO"
uploader_id  : "@alejandro_ao"
uploader_url : "https://www.youtube.com/@alejandro_ao"
channel_id   : "UC1oXUA7qgs0GZc_yk46K2OQ"
```

数据一直在——`scripts/fetch_info.sh:51` 已经在跑 `yt-dlp --dump-json` 拿整个 info dict，`:60-66` 只 `jq` 出 5 个字段，其余全丢。

**注意 `meta.json` 里不写 `creator_id`、不写 `watched`。** 这是主线的直接推论：它们是判断，不是事实。

### 2.2 必须一起修的 playlist bug

`--dump-json` 碰到播放列表 URL 会**每行吐一个 JSON**，`jq -r '.uploader'` 因此返回多行，直接拼进 DB。现网数据里有一条 `uploader` 的值是 `"Claude\nClaude\n…"`（7 行重复）。三个新字段会同样中招。

修法：加 `--no-playlist`，或 `jq -s '.[0]'`。

> **把握度**：这条 bug 的成因是**推断**，没复现。但脏数据本身是实测的。

### 2.3 handle 归一

三处格式不一样：

| 来源 | 形态 | 例 |
|---|---|---|
| `registry.json` | 从 URL `youtube.com/@xxx` 解出，保原大小写 | `TingHu888`、`mattpocockuk` |
| yt-dlp `uploader_id` | 带前导 `@` | `@alejandro_ao` |

**规则：去前导 `@`，转小写。**

> **把握度**：这条规则的前提是 YouTube handle 大小写不敏感（`@TingHu888` 与 `@tinghu888` 指同一频道）。**这是推断，未验证。** 实现时必须先实测——若它其实敏感，归一会把两个频道静默并成一个。

`registry.json` 里 `merge` 过的人有 `aliases`，消费方解 `creator_id` 时要一起查，否则合并过的人会失联。

### 2.4 索引文件

**位置：`<knowledgeRoot>/videos/creators.json`** —— 挂在 `videos/` 类型目录下，跟 vdl 的 `work/` 平级。这样不用给统一存储契约 §3.1 那条"第一层是类型"加例外。索引只覆盖视频，放在视频类型下语义就是对的。

```json
{
  "schema_version": 1,
  "built_at": "2026-09-15T14:02:11+08:00",
  "scanned": { "entities": 68 },
  "creators": [
    {
      "key": "alejandro_ao",
      "display_name": "Alejandro AO",
      "channel_id": "UC1oXUA7qgs0GZc_yk46K2OQ",
      "uploader_url": "https://www.youtube.com/@alejandro_ao",
      "videos": [
        { "task_id": "44a7244295ea", "title": "...", "upload_date": "2026-06-05", "duration": "2338" }
      ]
    }
  ],
  "unresolved": [
    { "display_name": "Matt Pocock", "task_ids": ["..."] }
  ]
}
```

三点说明：

1. **没有 `creator_id` / `watched` 字段**（主线）。
2. **`built_at` + `scanned` 是故意放的**：前端显示"基于某时刻的快照、覆盖 N 条"，让陈旧可见。这是 §3.4 那个风险的唯一缓解手段。
3. **`unresolved` 是常驻的，不是过渡态。** 回填依赖网络且视频不能已下架；Bilibili 那条 yt-dlp 给不给 `uploader_id` 未验证。这些视频必须在索引里有去处——**在前端消失比归错类更糟**，因为归错了看得见，消失了你不知道它曾经存在。

### 2.5 索引深度：只放元数据

实测体积（68 条）：摘要合计 283 KB（均 4.2 KB），文章合计 2.37 MB（均 35 KB）。

**索引只放元数据**（标题 / 日期 / 时长），约 20 KB，1000 条约 300 KB。

**被否掉的替代：把摘要全文放进索引**（约 300 KB，1000 条约 4 MB），让 scholia 的客户端子串匹配自动覆盖摘要内容。否掉的三条理由：

1. 摘要已经在磁盘上，scholia 详情页现在就直接读（`video-source.js:109-118`）。放进索引是同一段字节的第二个副本。
2. 第二个副本是会**静默过期**的那个：换 focus 重跑摘要后磁盘变了、索引没变，而标题作者都没动，看不出来。这跟本设计否掉"把 `creator_id` 冻进 `meta.json`"是同一个理由。
3. 它唯一买到的是列表级跨摘要搜索——那是 scholia README 写明的非目标，也不是本需求提出的。

文章全文（2.37 MB / 68 条）无论如何不能进索引，1000 条就是 35 MB。

---

## 3. 索引的生命周期

### 3.1 全量重算，不做增量

构建脚本落在 `skills/research/learn-video/scripts/build_creator_index.py`，两个子命令：`build`（全量重算）、`check`（见 §3.4）。它向 `store_config.py` 要 `videos_dir()`，不自持任何路径配置——跟本仓库既有的四份 `store_config.py` 副本模式一致。

扫 68 个 `meta.json`，毫秒级；1000 条也就几百毫秒。**增量机制在这个规模下是纯粹的复杂度。**

原子写：临时文件 + rename（`scholia` 的 `server/index.js:27-32` 就是这个模式）。构建失败不留半个文件，旧索引原样保住——前端看到旧数据，不是空数据。

> **把握度**：毫秒级是基于 68 个小文件的推算，未实测。

### 3.2 变化源只有一个

因为索引不含 registry 的任何信息（主线），registry 怎么变都不影响它。剩下唯一的变化源是**新增 / 删除深读实体**。

触发点：`learn-video` 归档步骤末尾顺手跑一次 `build`。零额外成本——流程本来就在跑脚本。

### 3.3 `watched` 由消费方现算

索引给出归一后的 `key`，消费方拿 `key` 去 `registry.json` 查表得到 `creator_id` / `watched`。

因为索引已经把 68 条视频聚合成约 20 个人，**join 的对象是人不是视频**——约 20 次精确查表，不是 68 次模糊匹配。

scholia 侧要新增的能力：定位 roster `DATA_DIR`（读 `~/.hskill/roster/config.json`）→ 读 `registry.json` → 按 §2.3 归一 → 解 `aliases`。

> **把握度**：这部分约 30 行，是估算，没写过。scholia 至今只认三个各自配置的目录路径，这是它没有的一类能力。

**被否掉的替代：索引里存 `watched`。** scholia 只读一个文件、完全不必知道 roster 存在，改动更小。否掉是因为 registry 一变索引就陈旧，而这种陈旧**没有症状**——标题、作者、视频数全对，只有"他是不是我关注的人"是旧的。无症状的错误恰好落在你要用它做决定的那个字段上。

### 3.4 陈旧仍然要可见

索引相对**实体**还是会陈旧：深读完一个视频，若 `build` 没跑成功，它就不在索引里。

构建脚本提供 `check` 子命令：数一遍磁盘上的 `meta.json` 个数，跟索引里的 `scanned.entities` 比，不一致输出 `STALE: 索引 68 条 / 磁盘 71 条`。

**`check` 由谁触发，本次不定死。** §3.2 的自动 `build` 已经覆盖正常路径，`check` 是给异常兜底的手动工具。现在就接进 scholia 启动流程，等于为一个还没发生的问题加机制。

---

## 4. 回填与迁移

### 4.1 顺序是锁死的

1. **改 vdl** —— `fetch_info.sh` 加 3 个字段 + 修 playlist bug；`buildTaskMeta` 输出这 3 个 + 3 个契约字段。
2. **回填** —— 见 §4.2。
3. **改 harveyz-skill** —— `archive.py` 写 → 校验；新增索引脚本；SKILL.md 调整。
4. **改 scholia** —— creator 源模块 + 路由 + registry 查表。

**为什么锁死**：第 3 步一旦把 `archive.py` 改成"缺必填字段就报错停下"，而 `meta.json` 还没有契约字段，`learn-video` 当场跑不了。反过来，第 2 步若在第 1 步之前跑，回填出的 `meta.json` 照样没有新字段，白跑 67 次。

### 4.2 复用 vdl 自己的两个工具

```bash
vdl rerun <task_id> fetch --reset step     # 重拉元数据写进 DB（67 次）
node scripts/backfill_meta_json.js         # 从 DB 重新生成全部 meta.json（1 次）
```

第二个脚本 vdl 仓库已有，注释写明就是为"让已完成任务对 scholia 可见"而做的一次性回填。

**四个已知坑：**

1. **`rerun fetch` 之后 `meta.json` 未必会重写。** vdl 只在 `task.status === 'completed'` 时才写（`core/orchestrator/index.js:460`），rerun 单步未必让任务走到 completed。所以第二步的全量 `backfill_meta_json.js` **不是可选项**——DB 与 `meta.json` 靠它对齐。
2. **`backfill_meta_json.js` 有 `isTaskCompleted` 门槛。** 卡在门槛外、但磁盘上已有 `meta.json`（`archive.py` 写的）的任务会永远补不上契约字段，然后被第 3 步的校验拦下。**实现第一件事是数这类任务有多少**（本文未统计）。
3. **`rerun fetch` 会连 `title` 一起覆盖**（`fetch_info.sh:92` 的 UPDATE 写 title/duration/uploader/upload_date/lang）。视频改过名的标题会变。通常是好事，但要知道它会动。
4. **DB 里 243 行、磁盘上只有 68 个目录**，其余 175 行是 `example.com` 测试夹具。回填必须按**磁盘目录**遍历，不是按 DB 行，否则会去网络请求 175 个假 URL。

### 4.3 回填失败的进 `unresolved`

失败情形：视频下架、转私有、地区限制、要登录；以及 Bilibili（yt-dlp 返不返 `uploader_id` 未验证）。这些任务 `uploader_id` 留空，索引按 `display_name` 收进 `unresolved`（§2.4）。

### 4.4 回填前必须备份

`backfill_meta_json.js` 会全量覆盖 68 个 `meta.json`。**这是整个方案里唯一一个不可逆操作**，覆盖前先 `cp` 一份走。

`vdl rerun` 不会自启后端服务（`learn-video` SKILL.md 里那条 `ECONNREFUSED` 说的就是这个），67 次批量跑之前先 `npm run agent:serve`。批处理脚本要输出成功 / 失败清单，失败的单独列出，不许静默跳过。

---

## 5. 明确接受的代价

### 5.1 清单层不进索引（C1）

`sync-ytchannel` 的归档（`feeds/youtube/creators/<handle>.json`）不进本索引。它跟深读实体本来是可精确 join 的——两边都有 `video_id`，而且 `task_id = sha1(url + "\n").slice(0,12)`（`core/id.js:11`），拿 URL 就能 O(1) 判断实体在不在。

不 join 的代价是**两格信息算不出来**：

| | 有清单（在追更） | 无清单 |
|---|---|---|
| **有深读** | ① 能看到"他发了 31 条，我读了 3 条" | ③ 我读过他 5 条，却没在追更他 |
| **无深读** | ② 我追他，一条都没深读过 | — |

③ 是"该关注谁"的信号，② 是"该取关谁"的信号，两者都是**可排序的**。本设计放弃它们，这两个判断继续靠人脑记。

实测现状：③ 约 20 人、① 约 3 人——③ 这格现在很满。（**这是估算**：没有 `uploader_id` 无法精确匹配，是拿 DB 的 uploader 去重后跟 registry 目测比对的。）

### 5.2 索引主键用 handle，不用 `channel_id`

`channel_id`（`UCxxx`）是不可变 id，是更强的键，但 `registry.json` 里没有它——名册的渠道主键是 handle，所以 join 只能走 handle。

代价即 roster 设计 §1.4 自己承认的那个缺陷：**博主改名后 handle 失配**。本设计把 `channel_id` 存进 `meta.json` 但暂不使用，为日后切换留路。

> **顺带一个本设计范围外的发现**：roster 设计 §1.4 写明它想要平台侧不可变 id、但"当前抓取路径 `browser-fetch-mcp` 的两个工具都不返回它"，因此接受了"改名 → 游标失联 → 漏一批物料"。而 yt-dlp 这条路径拿得到 `channel_id`。若日后把它接进名册，那个缺陷可以根治。**本次不做。**

### 5.3 §3.2 契约的保证方移到仓库外

见 §1.3。缓解手段是 `archive.py` 的校验降级。

---

## 6. 验收标准

1. 新跑一个 YouTube 视频，`meta.json` 含 `uploader_id` / `channel_id` / `uploader_url` 与三个契约字段，且 `archive.py` 校验通过。
2. 播放列表 URL 不再产生多行 `uploader`。
3. 回填后，67 个历史 YouTube 任务中可访问的那些都有 `uploader_id`；不可访问的出现在索引 `unresolved` 里，**没有任何一个任务从索引中消失**。
4. `creators.json` 里视频总数 + `unresolved` 中的 task_id 总数 == 磁盘上 `meta.json` 个数。
5. 在 `manage-creators` 里 `add` 一个此前只在候选集出现的人，**不重跑 `build`**，scholia 上他的 `watched` 立刻变真。（这是 §3.3 路 2 的核心验收点。）
6. `merge` 两个 handle 后，被合并方的视频仍能通过主 id 查到（`aliases` 解析生效）。
7. `build` 中途 kill，旧 `creators.json` 完好。
8. `check` 能在磁盘多出实体、索引未重算时输出 `STALE`。

---

## 7. 未验证项汇总

实现前必须逐条落实，否则会把推测当依据：

| 项 | 所在 | 风险 |
|---|---|---|
| 68 个 `meta.json` 中 50 个字段并存的成因 | §1.2 | 可能存在第三个写入方，新字段会被静默抹掉 |
| YouTube handle 是否大小写不敏感 | §2.3 | 若敏感，归一会把两个频道静默并成一个 |
| playlist 多行 JSON 是否就是脏数据成因 | §2.2 | 修错地方 |
| 有多少任务卡在 `isTaskCompleted` 门槛外 | §4.2 坑 2 | 这些任务会被 §1.3 的校验拦下，流程跑不动 |
| yt-dlp 对 Bilibili 返不返 `uploader_id` | §4.3 | 只影响 1 条，低 |
| scholia 侧 registry 读取约 30 行 | §3.3 | 估算偏差，只影响工作量预估 |
| 全量重算的实际耗时 | §3.1 | 估算偏差，规模大了才显现 |

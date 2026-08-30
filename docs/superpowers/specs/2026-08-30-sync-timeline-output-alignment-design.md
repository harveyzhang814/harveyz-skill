# sync-xtimeline / sync-ytchannel 输出格式对齐设计

## 元信息

- **设计日期**：2026-08-30
- **状态**：待实现
- **涉及组件**：改造 `sync-xtimeline`、`sync-ytchannel`（`roster` / `manage-roster` 不改，仍是两者共用的名册与 `DATA_DIR` 持有方）
- **代码基线**：`sync-xtimeline` v0.5.0、`sync-ytchannel` v0.4.0（`staging`）
- **本文范围**：只定两个 sync skill 的输出——流水线阶段、落盘目录、digest.md 格式、归档 JSON schema。不改 `registry.json` / `state.json` 契约（见 [[2026-08-26-creator-channel-registry-design.md]]），不改抓取契约（见 [[2026-08-27-browser-fetch-cli-design.md]]）。

---

## 0. 主线

> **两个 sync skill 的流水线形状必须一致；两者输出内容的差异只允许来自平台数据本身，不允许来自谁先实现、谁的功能没跟上。**

这句可证伪：只要能指出某处流水线阶段数、去重时机、存储层级两边不同，而这个不同追溯不到 X 与 YouTube 数据本身的差别（type 分类、时间戳精度、游标语义），主线即被推翻。

本文所有决定都是这条线的直接推论：YouTube 补翻译、补归档、补去重，不是因为 YouTube "应该更像 X"，而是因为它们本来就该在同一条流水线上跑，只是历史上 YouTube 少实现了两步。

---

## 1. 现状问题（调研结论）

两个 skill 共用同一个 `browser-fetch` CLI 抓取层、同一个 `roster` 名册层，但渲染/归档层各写各的，出现两类差异：

**硬约束（源自平台数据本身，本设计不动）**
- X 的 `type`（post/repost/reply/quote）分类：X 页面结构能提供，YouTube 频道页不能。
- 时间戳精度：X 每条推文都有精确到秒的时间；YouTube 只有约 15 条最新视频的 `published_at`，更早的只有相对文案 `published_text`。
- 游标语义：X 用 `last_seen_id`（单调递增可比大小），YouTube 用 `seen_urls`（video_id 不透明，只能判"见过没有"）。

**纯历史遗留（本设计要修）**
- YouTube 没有翻译步骤——SKILL.md 里漏写了，不是数据拿不到。
- YouTube 没有归档 JSON——不是没数据，是没写这一步；连带地，YouTube 判定"新增"完全依赖 `seen_urls` 这个只覆盖最近 15 条的游标窗口，没有全量历史可比对，存在漏检/误判重复的风险。
- X 有 `view.html` 累计视图，YouTube 没有——用户已决定这层展示不再由 skill 生产（外部应用直接读归档 JSON），所以这不是"补给 YouTube"，而是两边一起删。
- digest 链接写法、标题措辞、量词字符串、落盘目录结构，两边各写各的模板，没有共同来源。

---

## 2. 流水线对齐

两个 skill 的 `run` 统一为五段，**去重环节从"只在追加归档时做"提前到"决定新增内容之前做"**：

```
1. fetch + dedupe + advance cursor（脚本：fetch_new_tweets.py / fetch_new_videos.py）
                   browser-fetch CLI 拉取本次可见的全部条目，与游标比对出「新增」，
                   再与归档 JSON（tweets/creators/<handle>.json 或 youtube/creators/<handle>.json）
                   已有 id 集合（tweet_id / video_id）二次过滤，排除已经报告过的条目；
                   立刻推进游标，并把这份报告写入 <channel>/pending.json 兜底
2. translate       LLM 在对话里翻译第 1 步筛出的新增条目（X 译推文正文，YouTube 译标题），写入 translated 字段
3. archive         把第 2 步的新增条目追加进归档 JSON（脚本：archive_tweets.py / archive_videos.py）
4. write digest    用第 2 步的结果渲染 digest-<TS>.md（脚本：render_digest.py / digest.py），
                   成功写盘后清掉 pending.json
```

**为什么去重要在游标之外再查一次归档、且两边都要有**：当前 X 的"新增"完全信任游标（`last_seen_id`），归档脚本 `archive_tweets.py` 只在追加时对归档文件自己再去一次重——这保护了归档文件不重复，但不保护 digest 本身不重复。YouTube 更明显：`seen_urls` 只是最近 15 条的滑动窗口，没有全量历史可比对，此前没写进归档所以问题没暴露。改成"游标算出候选新增后，再查归档排除已报告过的"之后，归档 JSON 成为"哪些条目已经报过"的补充真值来源，游标继续管"这次该往前抓多远"（X 靠 id 排序、YouTube 靠窗口比对）——这是两个不同的问题，都要保留，不是互相替代。

**为什么 YouTube 也要有 `pending.json`**：翻译现在是 LLM 在对话里做的，夹在"抓取"和"写 digest"这两次脚本调用之间——这个间隙如果中断（翻译没做完、进程被杀），游标已经推进过了，重新抓取会永久漏掉这批条目。X 现有的 `pending.json` 机制正是为此设计：抓取成功立刻推游标、把 report 落盘，只有 `write digest` 跑完才清掉；下次调用发现 pending 还在就原样回放，不重新抓取。YouTube 补齐翻译步骤后同样存在这个间隙，必须有同款机制，否则翻译中断就会永久丢内容。

**为什么 archive 排在 write digest 前面**：`write digest` 是清掉 `pending.json` 这道安全网的那一步，`archive` 是幂等的（按 id 去重，重复追加是无害的空操作）。如果顺序反过来，一旦进程恰好在"digest 写盘、pending.json 已清掉"和"archive 追加完成"之间崩溃，这批条目就会两头落空：`pending.json` 没了没法重放，游标又已经在第 1 步推过、不会被重新抓到，归档 JSON 里永久少这一批。按"先 archive、后 write digest"的顺序，崩溃窗口只可能落在两步之间——此时 `pending.json` 还在，下次调用原样回放同一份 report，重跑 archive 是空操作，digest 照常补写，不存在数据永久丢失的窗口。

`run` 对外契约不变：无交互、`EMPTY` / `WRITTEN: <path>`（[[2026-08-26-creator-channel-registry-design.md]] 5.2 已定，本次不动）。

---

## 3. 目录结构

顶层按渠道分，渠道下归档（`creators/`）与通知（`digest/`）平级：

```
<DATA_DIR>/                          # 仍由 roster 持有，config.json 不变
├── registry.json                    # 不变，manage-roster 独占写
├── state.json                       # 不变，抓取层写游标
│
├── tweets/                          # 渠道：X/Twitter
│   ├── pending.json                 # 崩溃恢复暂存，从 DATA_DIR 根目录挪到这里（原因见下）
│   ├── creators/
│   │   └── <handle>.json            # 归档，tweet_id 去重，逐条追加
│   └── digest/
│       └── digest-<TS>.md           # 每次 run 合并一份（不拆分 handle），按 ## @handle 分节
│
└── youtube/                         # 渠道：YouTube（新增三项）
    ├── pending.json                 # 新增，同上机制
    ├── creators/
    │   └── <handle>.json            # 归档，video_id 去重，逐条追加
    └── digest/
        └── digest-<TS>.md
```

**`pending.json` 从 `DATA_DIR` 根目录挪到各自渠道目录下**：YouTube 补齐翻译步骤后（见下）也需要同款崩溃恢复机制，如果两边共用根目录下同一个 `pending.json`，两个 skill 交替运行时会互相踩文件——X 写的 pending 会被 YouTube 的下一次 run 当成自己的积压去回放，反之亦然。挪到各自渠道目录下之后两边天然隔离。

**删除**：`view.html`（若已生成过）、`render_view.py`、`sync-xtimeline` 的 `view` 子命令。展示不再由 skill 生产，外部应用直接读 `tweets/creators/*.json` / `youtube/creators/*.json`。

**目录命名说明**：顶层用 `tweets` / `youtube` 而非 `x` / `youtube`——`tweets` 沿用现状既有目录名，避免无谓改名；`creators` 替代了此前草案里的 `handle`，因为这层放的是"这个人在该渠道的归档"，用 `handle` 容易和 `registry.json` 里 `channels[].handle` 字段本身混淆。

---

## 4. digest.md 格式

**X**（结构不变，仅落盘路径变化）：
```
# X 追更摘要 — {run_time}

## @{handle}
- [{timestamp}] {translated}{类型标注}（[原文]({url})）

## 已建立追踪基线
- @{handle}：起始 {count} 条推文，从下次运行开始报告新增

## 失败
- @{handle}：{error}
```
`{类型标注}`：post 为空；转推 `（转推自 @x）`；回复 `（回复 @x）`；引用 `（引用 @x：{quoted_text}）`。`{timestamp}` 始终是完整 ISO 时刻。

**YouTube**（三处改动：链接语法、译文、时间精度回退）：
```
# YouTube 追更摘要 — {run_time}

## @{handle}
- [{时间}] {translated}（[原文]({url})）

## 已建立追踪基线
- @{handle}：起始 {count} 个视频，从下次运行开始报告新增

## 失败
- @{handle}：{error}
```
`{时间}` 回退链：`published_at` 有值 → 完整 ISO 时刻（不再像现在的 `format_date()` 截断成日期）；否则 `published_text` 有值 → 原样显示相对文案（如 "2 weeks ago"）；都没有 → `"日期未知"`。

**保留不统一的部分**：量词"条推文" / "个视频"——中文量词跟名词走，统一成同一个词反而读着不对，不算格式对齐要修的差异。空报告规则不变：完全没有 new/baseline/failure 时打印 `EMPTY`，不落盘。

---

## 5. 归档 JSON schema

X 和 YouTube 各自保留自己的字段形状，不强行统一字段名——第 1 节已定性：type 分类、时间精度是平台数据本身的差异，字段名跟着数据形状走，不跟着"两边看起来要一致"走。

**X** — `tweets/creators/<handle>.json`（内容不变，只是路径从 `tweets/<handle>.json` 挪过来）：
```json
[
  {
    "tweet_id": "2093176635940016380",
    "url": "https://x.com/trq212/status/2093176635940016380",
    "text": "life is stranger than fiction",
    "translated": "生活比小说更离奇",
    "timestamp": "2026-08-28T03:19:34.000Z",
    "author_handle": "@trq212",
    "type": "post",
    "reply_to_handle": null,
    "quoted_author": null,
    "quoted_text": null,
    "quoted_timestamp": null
  }
]
```
去重键：`tweet_id`。

**YouTube**（新增）— `youtube/creators/<handle>.json`：
```json
[
  {
    "video_id": "abc123",
    "url": "https://www.youtube.com/watch?v=abc123",
    "title": "Original title text",
    "translated": "翻译后的标题",
    "published_at": "2026-08-14T10:00:00Z",
    "published_text": "2 weeks ago",
    "channel_handle": "@mattpocockuk"
  }
]
```
去重键：`video_id`。`published_at` 没有值时为 `null`。不放 `type` / `reply_to_handle` / `quoted_*` 这类字段——YouTube 不存在这个概念，不用 `null` 占位，直接不出现在 schema 里。

---

## 6. 迁移

现有数据是可重建的抓取产物（不是第 1.2 节意义上的判断类数据），迁移只是挪目录，不改内容：

| 现状路径 | 新路径 |
|---|---|
| `tweets/<handle>.json` | `tweets/creators/<handle>.json` |
| `digests/x/<TS>--digest.md` | `tweets/digest/digest-<TS>.md` |
| `digests/youtube/<TS>--digest.md` | `youtube/digest/digest-<TS>.md` |
| `pending.json`（根目录，X 专用） | `tweets/pending.json` |
| `view.html`（若存在） | 删除，不迁移 |

一次性 `mv`，不需要写迁移脚本框架——数据量小（单用户、个位数 handle），且此前 `pending.json`/游标机制已保证"丢一批顶多刷一次基线"，迁移失败的代价可接受。

---

## 7. 边界（本设计明确不做）

- **不统一归档 JSON 字段名**。第 5 节已定，type/时间精度是平台差异，不是格式债。
- **不给 X 或 YouTube 补 HTML view**。展示层交给外部应用直接读归档 JSON。
- **不改 `registry.json` / `state.json` 契约**。名册层不动，见 [[2026-08-26-creator-channel-registry-design.md]]。
- **不改抓取契约**。`browser-fetch` CLI 的调用方式和返回 schema 不动，见 [[2026-08-27-browser-fetch-cli-design.md]]。
- **不做定时调度**。`run` 谁来触发是另一个设计。
- **不合并两个渠道的 digest**。一次 run 只处理一个平台，两份 digest 各自独立落盘。

---

## 8. 替代方案与为什么没选

| 方案 | 为什么没选 |
|---|---|
| 顶层按内容类型分（`digests/` `tweets/` `videos/`） | 用户明确要求按渠道分（`tweets/` `youtube/`），归档和 digest 挂在各自渠道下面，而不是内容类型下面挂着不同渠道。 |
| digest 拆成每个 handle 一份 | 用户明确要求保持合并——digest 是"这次 run 发生了什么"的整体通知，不是按人分的日志。 |
| 去重只修 YouTube，X 保持现状 | 去重时机（archive-diff 而非纯游标）是同一个正确性问题，X 现在的"digest 可能重复"只是因为游标够可靠、没被注意到，不代表它没有这个风险。两边一起改，行为对称。 |
| 归档字段名跨平台统一（如都叫 `id`/`author_handle`） | type 分类、时间精度本来就是平台数据形状的差异，字段名强行对齐只会制造"看似一样、实际语义不同"的假对称。 |

---

## 9. 源码锚点

| 位置 | 与本设计的关系 |
|---|---|
| `skills/feed/sync-xtimeline/scripts/render_digest.py` | digest 写盘路径改到 `tweets/digest/digest-<TS>.md`；模板不变（链接语法已符合） |
| `skills/feed/sync-xtimeline/scripts/archive_tweets.py` | 路径改到 `tweets/creators/<handle>.json`；去重逻辑不变（仍是追加时的安全网） |
| `skills/feed/sync-xtimeline/scripts/fetch_new_tweets.py` | 新增：算出候选新增后再查归档过滤一次；`pending.json` 路径从 `DATA_DIR/pending.json` 改到 `DATA_DIR/tweets/pending.json` |
| `skills/feed/sync-xtimeline/scripts/render_view.py` | 删除 |
| `skills/feed/sync-xtimeline/SKILL.md` | 删 `view` 子命令说明，更新目录结构描述 |
| `skills/feed/sync-ytchannel/scripts/digest.py` | 模板改动：链接语法、译文、`format_date()` 不再截断；新增 CLI `main()`（读 stdin report，写 digest，处理 `pending.json`），对齐 `render_digest.py` 的角色 |
| `skills/feed/sync-ytchannel/scripts/sync_channels.py` | 改名为 `fetch_new_videos.py`，退化成纯 stage-1 脚本：抓取→游标 diff→查归档去重→立刻推游标→写 `youtube/pending.json`，不再自己写 digest |
| `skills/feed/sync-ytchannel/scripts/archive_videos.py` | 新增，镜像 `archive_tweets.py`，路径 `youtube/creators/<handle>.json` |
| `skills/feed/sync-ytchannel/SKILL.md` | 补翻译步骤说明（对齐 X 第 3 步的写法）、补归档步骤说明、`pending.json` 崩溃恢复说明、更新目录结构描述，把"update log"措辞改成与实现一致的"追更摘要" |
| `skills/feed/*/tests/` | 两边都要补：dedupe-against-archive 的测试、pending.json 崩溃恢复测试（YouTube 新增）、archive 步骤测试（YouTube 新增）、路径迁移后的现有测试更新 |

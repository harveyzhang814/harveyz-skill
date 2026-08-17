# 交接：写一份 sync-xtimeline 归档 JSON 的数据格式规范文档

**日期**：2026-08-17
**author 模型**：Claude Sonnet 5
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：把 `~/.hskill/sync-xtimeline/tweets/<handle>.json`（sync-xtimeline 的推文归档文件）的数据格式，写成一份正式的参考文档，让其他应用的开发者可以把这份 JSON 直接当数据源使用，不需要读 Python 源码反推字段含义。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，没有「工作流约定」章节，直接开工，完成后等原 session 按「最小验收锚点」验收。

---

## 最小验收锚点

在 `docs/reference/sync-xtimeline-data-format.md` 写出的文档，逐条满足：

1. 文档存在于该路径，Markdown 格式，风格与 `docs/reference/todo-format-spec.md` 一致（标题 + 一句话点出唯一权威来源 + 结构示例 + 字段表 + 补充说明，不用 YAML frontmatter）。
2. 明确写出：`~/.hskill/sync-xtimeline/tweets/<handle>.json` 是这份数据的**唯一权威来源**（single source of truth），`view.html`、Markdown 摘要（digest）、`report.json` 中间态都是从它派生或与它无关的临时产物，不是数据源本身。
3. 字段表覆盖全部 11 个 key：`tweet_id` `url` `text` `timestamp` `author_handle` `type` `reply_to_handle` `quoted_author` `quoted_text` `quoted_timestamp` `translated`，每个字段写明类型、是否可为 `null`、`null` 出现的条件。
4. 明确写出一条容易被读错的事实：**这 11 个 key 在四种 `type` 下都会出现**（不是按 type 有不同的字段集合），不适用的字段值是 `null`，不是缺省不写。
5. 对 `post`/`repost`/`quote`/`reply` 四种 `type`，每种给一个完整 JSON 对象示例；其中 `reply` 类型在本地真实归档数据里没有出现过（20 条样例数据只有 post/repost/quote），该示例需要标注为"根据代码字段命名 + SKILL.md 语义描述构造，非真实抓取数据"，不能冒充是从真实数据摘出来的。
6. 明确写出持久化模型：按 handle 分文件、JSON 数组、**只增不改**（append-only）、按 `tweet_id` 去重（重复 id 保留先写入的那条，后来的丢弃）、文件内顺序是**抓取到达顺序**，不保证按时间倒序——倒序排列是消费方（`render_view.py`）读取时自己做的，不是落盘时的顺序，这点必须提醒外部消费者不要假设文件已排序。
7. 明确写出：当前没有独立的 schema version 字段，也没有版本化机制；给外部开发者的建议是按「未知字段容忍」（unknown-field-tolerant）方式解析，为将来新增字段留余地。

## 背景与现状

`sync-xtimeline` skill（`skills/research/sync-xtimeline/`）批量追更一批 X 博主，每次 `run` 抓取增量推文、翻译、产出 Markdown 摘要，同时把新推文追加进按 handle 分文件的归档：`~/.hskill/sync-xtimeline/tweets/<handle>.json`。这份归档文件是整个 skill 里**唯一持久化保存全部历史推文内容**的地方——这个结论是本次对话里明确核实过的（读了 `archive_tweets.py`/`render_view.py` 源码 + 真实归档样例数据 `~/.hskill/sync-xtimeline/tweets/trq212.json` 逐条核对得出）。现在需要把这个结论写成正式文档，方便其他应用（不是这个 skill 自己）把这份 JSON 当数据源直接消费，而不用去读 Python 实现反推格式。

## 关键决定（别改动）

- **权威数据源 = 归档文件本身，不是 `view.html`、不是 digest、不是中间态 `report.json`。** `view.html` 每次都是 `render_view.py` 从归档全量重新生成的衍生产物；Markdown 摘要是单次 `run` 的临时报告，看完即弃；`report.json`（`fetch_new_tweets.py` 的输出，`run` 步骤 2-3 之间的管道中间态）在 `~/.hskill/sync-xtimeline/pending.json` 落一份，但那是抓取阶段的临时文件，不等同于归档。
- **归档条目 = `report["new"][handle]` 里的推文 dict，外加 skill `run` 流程步骤 3 手工注入的 `translated` 字段。** `archive_tweets.py` 本身不校验、不要求 `translated` 一定存在（`test_archive_tweets.py` 里没有 `translated` 字段的用例也能跑通），但正常走 skill `run` 流程产出的归档，`translated` 一定有值——这个"正常流程保证但脚本层不强制"的细节值得在文档里带一句，避免外部消费者假设某个字段绝对存在就不做容错。
- **字段集合对四种 `type` 完全一致，是同一组 11 个 key，不适用的值是 `null`。** 这不是猜的，是从真实归档数据 `~/.hskill/sync-xtimeline/tweets/trq212.json`（20 条记录，覆盖 post/repost/quote）逐条核对出来的：三种 type 打印出来的 key 集合完全相同。
- **落盘顺序 ≠ 展示顺序。** `archive_tweets.py` 按到达顺序 append；`render_view.py` 的 `load_archives()`（`skills/research/sync-xtimeline/scripts/render_view.py:136`）读取时才用 `sorted(tweets, key=lambda t: int(t["tweet_id"]), reverse=True)` 做倒序。写文档时如果直接说"归档按时间倒序"就是错的，必须明确这是消费方行为，不是持久化保证。
- **没有 `reply` 类型的真实样例数据可用。** 本地唯一的真实归档文件（`trq212.json`）里没有 `reply` 类型的记录。写 `reply` 示例时要靠 `archive_tweets.py`/`SKILL.md` 里的字段命名和语义描述自己构造一条，并在文档里如实标注是构造出来的，不是抓取来的——不要因为凑不齐四种类型就悄悄跳过这条要求，也不要冒充是真实数据。

## 范围铁律

**In scope**：只写 `~/.hskill/sync-xtimeline/tweets/<handle>.json` 这一份归档文件本身的数据格式规范，面向"想把它当数据源接进自己应用"的外部开发者。

**Out of scope**：
- 不改动任何现有脚本或测试代码（`archive_tweets.py`/`render_view.py`/`fetch_new_tweets.py` 等）——这是纯文档任务，不是格式迁移或加 schema version 字段的任务。
- 不需要给 `watchlist.json`（关注列表/游标文件）、Markdown 摘要、`report.json`/`pending.json`（抓取中间态）单独写完整格式规范——提一句它们是什么、和归档文件的关系即可，不用展开。
- 不需要验证或修改 `browser-fetch-mcp` 抓取层的实现细节，那是归档数据的上游来源，不是归档格式本身。

## 相关文档索引

- `skills/research/sync-xtimeline/SKILL.md` — `run` 子命令的完整流程、字段来源说明；里面这句话是理解 `repost` 类型字段语义的关键："转推卡片的 `author_handle`/`text`/`url` 本来就是原推文的，不是账号自己的"。
- `skills/research/sync-xtimeline/scripts/archive_tweets.py` — 归档写入的唯一实现：按 `tweet_id` 去重、追加、按 handle 分文件落盘，权威代码，字段真值来源之一。
- `skills/research/sync-xtimeline/scripts/render_view.py:136`（`load_archives()`） — 归档文件的读取方式（按 handle 分组、按 `tweet_id` 倒序），用来佐证"落盘顺序≠展示顺序"这条关键决定。
- `skills/research/sync-xtimeline/scripts/render_digest.py`（`_type_suffix()`，约第 27 行起） — `reply_to_handle`/`quoted_author`/`quoted_text` 等字段在下游怎么被消费，帮助理解四种 `type` 各自的语义。
- `skills/research/sync-xtimeline/tests/test_archive_tweets.py` — 归档行为的可执行规范：去重、追加、无新推文时不落盘等边界情况都在这里，写文档时可以直接照着这些用例反推持久化模型的边界行为。
- 真实样例数据：`~/.hskill/sync-xtimeline/tweets/trq212.json`（20 条真实归档记录，可直接读取核对字段与 `type` 分布——里面有 post/repost/quote，没有 reply）。
- 风格参照：`docs/reference/todo-format-spec.md`（本仓库里同类型的"给某个数据格式写规范文档"的现成范例，标题 + 一句话点出唯一来源 + 结构示例 + 字段表的写法可以直接照抄这个模式）。

## 受影响文件/落点

新建 `docs/reference/sync-xtimeline-data-format.md`。不改动仓库里任何其他文件。

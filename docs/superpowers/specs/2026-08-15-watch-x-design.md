---
migrated: false
---

# watch-x：批量追更 X 博主推文设计

## 背景

`browser-fetch-mcp` 目前只有 `fetch_article`（单条 URL 的完整抽取，供 `clip-url` 使用）。用户想要的是"固定关注一批 X 博主，定时批量拉取新推文"——这不是单条抓取场景，需要：

1. 一个能一次性列出某个账号时间线上多条推文的抓取能力（`fetch_article` 没有）。
2. 一个维护"关注列表 + 每个账号已看到到哪条"的持久化状态，每次只报告增量。
3. 一个适合无人值守定时运行（`/loop` 或 `schedule`）的产出形式。

这轮设计新增一个 browser-fetch-mcp 工具 + 一个新 skill，跟 `clip-url` 的入库流程完全独立。

## 范围

**做：**
- `browser-fetch-mcp` 新增 `fetch_user_timeline(profile_url, chrome_profile, max_tweets=20)` 工具，复用 xcom 现有的一次性浏览器启动生命周期（headed 优先、cookie 注入、失败降级 headless），抽取时间线上可见的推文卡片列表。
- 新 skill `skills/research/watch-x/`：维护关注列表、按游标计算增量、翻译新推文文本、写 Markdown 摘要文件。
- 关注列表管理入口（增/删/查）与"运行一次抓取"入口，同一个 skill 的不同子命令。
- 首次关注某账号时只建立游标基线，不把当前时间线全量当增量推送。
- 无新推文时不产出摘要文件。

**不做：**
- 不展开长线程/引用推文，只取时间线页面直接可见的文本。
- 不下载图片。
- 不进 Obsidian、不复用 `clip-url` 的打标/去重库（`dedup_check.py`/`article_meta.py`）——语义不同（账号级游标 vs URL 级去重）。
- 不在这轮实现"定时触发"本身——`/loop`/`schedule` 是已有能力，用户后续自行配置去调用 `watch-x` 的运行入口，这轮只负责让运行入口能被无人值守调用（无交互式 prompt）。
- 不写 `fetch_user_timeline` 抽取 JS 的自动化测试（跟现有 xcom 抽取测试策略一致，原因见下方"测试策略"）。

## 架构

### a) `browser-fetch-mcp`：新增 `fetch_user_timeline`

```
fetch_user_timeline(profile_url, chrome_profile, max_tweets=20)
  │
  ├─ chrome_profile 为空 → ValueError（沿用 fetch_article xcom 分支的硬性要求，时间线抓取同样需要登录态）
  ├─ 从 chrome_profile 提取 cookie（复用现有 extract_cookies()）
  ├─ 尝试 headed：browser.launch(headless=False, ...) → new_context → add_cookies → goto(profile_url)
  │    → 滚动编舞（复用 _xcom_scrape 的 window.scrollTo 循环，多滚几屏以凑够 max_tweets 或到底）
  │    → page.evaluate(_EXTRACT_JS_TIMELINE_HEADED) → browser.close()
  ├─ 若异常 → 降级 headless，同样的滚动+抽取逻辑，用 headless 版抽取 JS
  ├─ 两次都失败或 JS 返回 {error: ...} → RuntimeError
  └─ 返回按时间倒序排列的推文列表，每条含 tweet_id/text/url/timestamp/author_handle，最多 max_tweets 条
```

复用 `_xcom_scrape` 同款 try/finally 包裹的一次性浏览器生命周期（长期运行的 server 进程不能留僵尸 Chrome 进程），但目标页面从单条推文页换成 profile 时间线页，抽取 JS 收集的是"时间线上多张卡片的摘要字段"而不是"单条推文的完整正文"，所以是新的一对 `_EXTRACT_JS_TIMELINE_HEADED`/`_EXTRACT_JS_TIMELINE_HEADLESS`，与 `fetch_article` 现有的 `_EXTRACT_JS_HEADED`/`_EXTRACT_JS_HEADLESS` 并存，不复用不修改。

不下载图片（`download_images()` 不参与这条路径）。

### b) 新 skill `watch-x`

`skills/research/watch-x/`，与 `clip-url` 同组（`research`），依赖同一个 `browser-fetch-mcp` launcher 定位方式（复用 `browser_fetch_mcp_locate.py` 的定位逻辑）和同一份持久化 chrome_profile 配置（复用 `chrome_profile_config.py` 的 get，不用户第二次设置）。

两个入口：

- **管理关注列表**：`/watch-x add <profile_url>`、`/watch-x list`、`/watch-x remove <handle>`——交互式使用，人工确认即可。
- **运行一次抓取**：`/watch-x run`（或无参数默认走这个）——这是要支持 `/loop`/`schedule` 无人值守调用的入口，过程中不能有需要用户回答的 prompt（chrome_profile 缺失时直接在摘要里报错，不阻塞等用户输入）。

## 数据流

```
watchlist.json (~/.hskill/watch-x/watchlist.json)
  [{handle, profile_url, last_seen_tweet_id}, ...]
       │
       ▼
/watch-x run
       │
  for each watched handle:
       │
       ├─ 调用 fetch_user_timeline(profile_url, chrome_profile)
       ├─ last_seen_tweet_id 为空（首次关注）：
       │     不产出增量，只把本次拿到的最新 tweet_id 写回游标，
       │     在本次运行的汇总里记一行"已建立追踪基线（{handle}，起始 N 条）"
       ├─ last_seen_tweet_id 非空：
       │     过滤出 tweet_id > last_seen_tweet_id 的条目（X 的 tweet id 是递增雪花 ID，直接数值比较）
       │     无新推文 → 跳过，游标不变
       │     有新推文 → 翻译文本（skill 主流程直接处理，纯文本翻译不需要单独派发 subagent）
       │              → 更新 last_seen_tweet_id = 本次拿到的最新一条的 id
       │
       ▼
汇总所有账号本次的新推文（+ 基线建立提示 + 失败账号列表）
       │
  全部空（无新增、无基线建立、无失败）→ 不写文件，运行静默结束
  否则 → 写入 ~/.hskill/watch-x/digests/{YYYYMMDDTHHMMSS}--digest.md
```

摘要文件格式（每个账号一个小节，按 handle 分组）：

```markdown
# X 追更摘要 — {运行时间}

## @{handle}
- [{timestamp}] {中文翻译}（[原文]({url})）
- ...

## 失败
- @{handle2}：{错误信息}

## 已建立追踪基线
- @{handle3}：起始 N 条推文，从下次运行开始报告新增
```

## 去重与游标

不复用 `clip-url` 的 `dedup_check.py`（那是按文章 URL 做的去重索引，语义是"这篇文章抓过没有"）。这里是账号级增量游标，语义是"这个账号我看到哪了"，用 `last_seen_tweet_id` 单值即可，X 的 tweet id 是递增雪花 ID，数值比较判断新旧，不需要解析时间戳。

## 错误处理

- 单个账号抓取失败（页面结构变化、未登录、限流、`RuntimeError`）：记入摘要"失败"小节，附错误信息；不中断其他账号的处理；该账号游标不更新，下次运行重试。
- `chrome_profile` 未配置：`/watch-x run` 直接在本次摘要里对所有账号记为失败（"未配置 chrome_profile"），不阻塞等待用户输入——这条路径必须能被无人值守调用。
- URL scheme 校验、cookie 提取失败等：沿用 `fetch_article` xcom 分支已有的错误处理模式。

## 测试策略

- `fetch_user_timeline` 的抽取 JS 部分：不写自动化测试，原因与现有 xcom 抽取测试策略一致——headed 模式需要真实显示环境和真实登录态，自动化测试环境大概率没有。实现完成后人工用真实关注的账号手动跑一次验证（headed 路径能启动、抽取到的字段合理、headless 降级路径也能跑通）。
- `watch-x` 侧的游标比较、watchlist 读写、"无新推文不写文件"这些逻辑是纯函数，写单元测试覆盖。
- 集成层面：人工配置 1-2 个真实关注账号，跑 `/watch-x run` 两次（第一次建立基线、第二次验证增量），确认摘要文件内容和游标更新符合预期。

---
name: sync-ytchannel
version: "0.2.0"
description: "Run one incremental fetch over every YouTube channel on the roster and write a Markdown update log listing each new video's title, publish date and URL. Trigger phrases: '/sync-ytchannel run', '/sync-ytchannel', 'check my YouTube channels for new videos', or a request to run sync-ytchannel on a schedule via /loop or schedule. Adding or removing a watched channel is manage-roster, not this skill. Listing only — never downloads a video, transcript or description, and never ingests into Obsidian (use clip-url or learn-video for a single video)."
user_invocable: true
---

# sync-ytchannel

批量追更一批 YouTube 频道，每次运行只报告上次运行之后新上传的视频，产出一份 Markdown 更新日志。抓取字段只有三个：**标题 / 发布日期 / URL**，URL 是唯一键。下文脚本路径均相对本 SKILL.md 所在目录。

**关注哪些频道由 [manage-roster](../manage-roster/) 维护，不在这里改。** 本 skill 只负责跑一次增量抓取：从名册读渠道列表，回写游标。

## 初始化（run first）

**① 加载平台补丁**

根据当前执行平台读取对应补丁：Claude Code → `platforms/SKILL.claude.md`；
Codex → `platforms/SKILL.codex.md`；Hermes → `platforms/SKILL.hermes.md`；
Pi → `platforms/SKILL.pi.md`。若补丁顶部带「⚠️ 未在本平台实测」标注，
先告知用户再继续。

**② 检查 roster 名册**

本 skill 自己没有配置。数据目录归 roster 名册持有，检查它在不在：

```bash
python3 scripts/roster_locate.py
```

若输出 `NOT_FOUND: <error>`（exit 1），向用户报告"roster tool 未安装：{error}"，流程终止。若从未初始化过名册（`~/.hskill/roster/config.json` 不存在），让用户先跑一次 [manage-roster](../manage-roster/)。

## 用法

只有一个子命令：

- `/sync-ytchannel run`（或无参数默认）— 跑一次增量抓取，产出更新日志

`add` / `remove` / `list` 已迁到 [manage-roster](../manage-roster/)。

### run（支持 /loop、schedule 无人值守调用，过程中不能有需要用户回答的交互）

1. 运行 `python3 scripts/browser_fetch_locate.py`。若输出 `FOUND: <path>`，继续步骤 2；若输出 `NOT_FOUND: <error>`（exit code 1），向用户报告"browser-fetch 未安装或未找到：{error}。在本仓库 checkout 内运行会自动定位；若通过 `hskill install` 安装到别处运行，需要先运行 `hskill install --tool browser-fetch`"，流程终止，不再执行后续步骤。
2. 运行 `python3 scripts/sync_channels.py`。这一步自己完成抓取、增量对比、渲染更新日志、推进游标，中间不需要任何介入（视频标题不翻译）。
3. 根据输出：
   - `EMPTY`：向用户报告"本次没有新视频，未生成更新日志"。
   - `WRITTEN: <path>`：向用户报告更新日志路径，并简述本次涵盖了哪些频道的新视频（每个频道几个）、哪些频道是首次建立基线、哪些频道抓取失败。

`chrome_profile` 不由本 skill 单独配置，直接读取 browser-fetch 里持久化的默认值（跟 clip-url、sync-xtimeline 共用同一份配置），用它带上 YouTube 登录态。频道页本身是公开的，所以没配过也能跑，只是不是登录态视角。

## 日期精度

频道 Videos 页只给相对日期（"2 weeks ago"），确切时间戳来自频道的 Atom uploads feed，而 feed 只覆盖最近约 15 个上传。所以更新日志里的日期：feed 覆盖到的显示 `YYYY-MM-DD`，覆盖不到的原样显示 YouTube 给的相对说法，不会拿相对说法反推出一个假的确切日期。日常追更报的都是最新几个视频，实际上总是落在 feed 覆盖范围内。

## 边界

只做"有没有新视频"这一件事：不下载视频、不抓字幕、不抽正文、不进 Obsidian、不打标。单个视频要精读走 [learn-video](../../research/learn-video/)，单篇入库走 [clip-url](../../research/clip-url/)。跟 [sync-xtimeline](../sync-xtimeline/) 共用同一份 roster 名册和同一个数据目录，digest 各落各的平台子目录（本 skill 落 `digests/youtube/`）。

游标存在名册的 `state.json` 里，是"已报告过的 URL 集合"，不是 sync-xtimeline 那种单个 last_seen id——X 的 snowflake tweet id 按时间递增，可以比大小；YouTube 的 video id 是不透明的，只能判断"见过没有"。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/config.py` | 数据目录：运行时向 roster 要，本 skill 不再自持 `DATA_DIR` |
| `scripts/browser_fetch_locate.py` | 定位 browser-fetch launcher（跟 clip-url 同款，独立副本） |
| `scripts/roster_locate.py` | 定位 roster launcher（跟 `browser_fetch_locate.py` 同款，独立副本） |
| `scripts/roster_client.py` | 与名册的桥：读本平台渠道列表、读写游标。只调 `registry channels` 和 `state`，绝不写 registry |
| `scripts/cursor.py` | 纯函数游标 diff（`compute_update`），不碰磁盘不碰网络 |
| `scripts/mcp_channel_client.py` | 调用 browser-fetch 的 `channel` 子命令（解析逻辑全在 CLI 侧） |
| `scripts/digest.py` | 纯函数：把报告渲染成 Markdown 更新日志 |
| `scripts/sync_channels.py` | `run` 子命令：抓取 → 对比 → 写更新日志 → 推进游标（写盘成功才推进游标） |

---
name: sync-ytchannel
version: "0.1.0"
description: "Batch-watch a fixed set of YouTube channels for newly uploaded videos and write a Markdown update log listing each new video's title, publish date and URL. Trigger phrases: 'watch this YouTube channel', '/sync-ytchannel add <channel_url>', '/sync-ytchannel list', '/sync-ytchannel remove <handle>', '/sync-ytchannel run', or a request to run sync-ytchannel on a schedule via /loop or schedule. Listing only — never downloads a video, transcript or description, and never ingests into Obsidian (use clip-url or learn-video for a single video)."
user_invocable: true
---

# sync-ytchannel

批量追更一批 YouTube 频道，每次运行只报告上次运行之后新上传的视频，产出一份 Markdown 更新日志。抓取字段只有三个：**标题 / 发布日期 / URL**，URL 是唯一键。下文脚本路径均相对本 SKILL.md 所在目录。

## 初始化（run first）

**检查配置文件**

```bash
ls ~/.hskill/sync-ytchannel/config.json 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

**若输出 `NOT_FOUND`，进行初始化：**

1. 询问用户更新日志和关注列表要保存到哪个目录（`DATA_DIR`，必须由用户手动提供，不得猜测或自动选择）；若用户没有偏好，可建议默认值 `~/.hskill/sync-ytchannel`。
2. 用 Python 写入配置（避免 shell 注入，将 `<DATA_DIR>` 替换为用户输入的路径）：
   ```python
   import json
   from pathlib import Path
   cfg_path = Path.home() / '.hskill' / 'sync-ytchannel' / 'config.json'
   cfg_path.parent.mkdir(parents=True, exist_ok=True)
   cfg_path.write_text(json.dumps({
       'DATA_DIR': '<DATA_DIR>',
   }, indent=2, ensure_ascii=False), encoding='utf-8')
   print(f"配置已保存：{cfg_path}")
   ```

`DATA_DIR` 由 `scripts/config.py` 在运行时读取，之后 `watchlist.json` 和 `digests/` 都落在这个目录下，脚本自身不内置默认路径。配置文件本身的位置是固定的，只有它指向的数据目录可配。

## 用法

四个子命令：

- `/sync-ytchannel add <channel_url>` — 关注一个频道
- `/sync-ytchannel remove <handle>` — 取消关注
- `/sync-ytchannel list` — 查看当前关注列表和游标
- `/sync-ytchannel run`（或无参数默认）— 跑一次增量抓取，产出更新日志

### add / remove / list

直接调用 `scripts/watchlist.py`，handle 由脚本从 URL 里解析，不需要在这一步额外处理：

- `add`：运行 `python3 scripts/watchlist.py add <channel_url>`。`<channel_url>` 支持 `/@handle`、`/channel/UCxxx`、`/c/xxx`、`/user/xxx` 各种形式，带不带 `/videos` 后缀都行。输出 `OK @<handle>` 表示已加入关注；失败（已在关注中、或不是频道 URL）原样报告 stderr。
- `remove`：运行 `python3 scripts/watchlist.py remove <handle>`，同样原样报告结果。
- `list`：运行 `python3 scripts/watchlist.py list`，原样展示给用户（每行是 `@handle  channel_url  seen=<N videos 或 (none)>`，或 `EMPTY`）。

### run（支持 /loop、schedule 无人值守调用，过程中不能有需要用户回答的交互）

1. 运行 `python3 scripts/browser_fetch_mcp_locate.py`。若输出 `FOUND: <path>`，继续步骤 2；若输出 `NOT_FOUND: <error>`（exit code 1），向用户报告"browser-fetch-mcp 未安装或未找到：{error}。在本仓库 checkout 内运行会自动定位；若通过 `hskill install` 安装到别处运行，需要先运行 `hskill install --tool browser-fetch-mcp`"，流程终止，不再执行后续步骤。
2. 运行 `python3 scripts/sync_channels.py`。这一步自己完成抓取、增量对比、渲染更新日志、推进游标，中间不需要任何介入（视频标题不翻译）。
3. 根据输出：
   - `EMPTY`：向用户报告"本次没有新视频，未生成更新日志"。
   - `WRITTEN: <path>`：向用户报告更新日志路径，并简述本次涵盖了哪些频道的新视频（每个频道几个）、哪些频道是首次建立基线、哪些频道抓取失败。

`chrome_profile` 不由本 skill 单独配置，直接读取 browser-fetch-mcp 里持久化的默认值（跟 clip-url、sync-xtimeline 共用同一份配置），用它带上 YouTube 登录态。频道页本身是公开的，所以没配过也能跑，只是不是登录态视角。

## 日期精度

频道 Videos 页只给相对日期（"2 weeks ago"），确切时间戳来自频道的 Atom uploads feed，而 feed 只覆盖最近约 15 个上传。所以更新日志里的日期：feed 覆盖到的显示 `YYYY-MM-DD`，覆盖不到的原样显示 YouTube 给的相对说法，不会拿相对说法反推出一个假的确切日期。日常追更报的都是最新几个视频，实际上总是落在 feed 覆盖范围内。

## 边界

只做"有没有新视频"这一件事：不下载视频、不抓字幕、不抽正文、不进 Obsidian、不打标。单个视频要精读走 [learn-video](../learn-video/)，单篇入库走 [clip-url](../clip-url/)。跟 [sync-xtimeline](../sync-xtimeline/) 是同一套架构的两个独立实例，互不共享数据。

游标是"已报告过的 URL 集合"，不是 sync-xtimeline 那种单个 last_seen id——X 的 snowflake tweet id 按时间递增，可以比大小；YouTube 的 video id 是不透明的，只能判断"见过没有"。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/config.py` | 配置读写：从 `~/.hskill/sync-ytchannel/config.json` 读取 `DATA_DIR`（数据目录），供其余脚本统一调用 |
| `scripts/browser_fetch_mcp_locate.py` | 定位 browser-fetch-mcp launcher（跟 clip-url 同款，独立副本） |
| `scripts/watchlist.py` | 关注列表持久化（增/删/查）+ URL→handle 解析 + 纯函数游标 diff（`compute_update`），也是 `add`/`remove`/`list` 子命令的 CLI 入口 |
| `scripts/mcp_channel_client.py` | 调用 browser-fetch-mcp 的 `fetch_channel_videos` MCP 工具（解析逻辑全在 MCP 侧） |
| `scripts/digest.py` | 纯函数：把报告渲染成 Markdown 更新日志 |
| `scripts/sync_channels.py` | `run` 子命令：抓取 → 对比 → 写更新日志 → 推进游标（写盘成功才推进游标） |

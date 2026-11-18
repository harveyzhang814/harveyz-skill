# feedr 拆分：本机切换与真实数据验收记录

- **日期：** 2026-11-18
- **执行者：** 接手方（交接文档 `docs/commute/2026-11-18-feedr-split-handoff.md`）
- **范围：** 计划 Task 14 的 Step 1、2、3、4、6。**Step 5**（合并、部署 6 个 skill 后手动跑一轮）和 **Step 7**（本文件的最终验收提交）按交接约定由交出方在合并后完成，本次未做。
- **被验代码：** feedr `feature/initial-split` @ `2c379b3`（全局安装的 `feedr` 与仓库源码逐文件一致，已核对）；全局命令 `~/.local/bin/feedr` → `~/.local/share/uv/tools/feedr`（Python 3.12，非 editable 快照）。
- **总判断：** Step 1、2、3、6 通过；Step 4 抓取通过，但发现一个必须由人处理的前置条件（见「钥匙串授权」），**AC8 的人工验收之前要先处理它**。

## Step 1　切换前基线（旧工具）

| 命令 | 退出码 | 输出 |
|---|---|---|
| `~/.local/bin/roster registry list > /tmp/before-registry.txt` | 0 | 614 字节，8 位关注者 |
| `~/.local/bin/browser-fetch profile get > /tmp/before-profile.json` | 0 | `{"profile_path":".../Google/Chrome/Profile 9"}`，92 字节 |
| `~/.local/bin/browser-fetch articles-rule list > /tmp/before-rules.json` | 0 | 565 字节（含 claude.com、simonwillison.net 等规则） |

切换前旧数据快照：`~/.hskill/roster` 4 个文件（`config.json`、`registry.json`、`state.json`、`state.json.corrupt-20261111T0904.bak`），`~/.hskill/browser-fetch` 3070 个文件、452 个目录、约 509 MB。`~/.feedr` 不存在。旧配置：`DATA_DIR=/Users/harveyzhang96/.hskill/roster`，`knowledgeRoot=/Users/harveyzhang96/knowledge`。

## Step 2　`feedr init`

命令：`feedr init`（真实 HOME，退出码 0）。stdout：

```
{"status":"INITIALIZED","config":{"archive_root":"/Users/harveyzhang96/knowledge","roster_dir":"/Users/harveyzhang96/.feedr/roster"},"items":[
 {"item":"roster","source":"/Users/harveyzhang96/.hskill/roster","target":"/Users/harveyzhang96/.feedr/roster","action":"copied"},
 {"item":"browser","source":"/Users/harveyzhang96/.hskill/browser-fetch/contexts","target":"/Users/harveyzhang96/.feedr/browser","action":"copied"},
 {"item":"archive_root","source":"/Users/harveyzhang96/.hskill/config.json","target":"/Users/harveyzhang96/knowledge","action":"from_knowledgeRoot"}]}
```

stderr：`feedr: 已从 /Users/harveyzhang96/.hskill/browser-fetch/contexts 复制浏览器数据到 /Users/harveyzhang96/.feedr/browser`。

与计划预期逐项对照：`browser` = `copied` ✔；`roster` = `copied` ✔；`archive_root` 来自 `knowledgeRoot`，值 `/Users/harveyzhang96/knowledge` ✔。`~/.feedr/browser` 权限 `drwx------`（0700）✔，`~/.feedr/config.json` 只含 `archive_root`、`roster_dir` 两个键 ✔。

## Step 3　与基线对比

| 对比 | 结果 |
|---|---|
| `feedr roster registry list` vs `/tmp/before-registry.txt` | **无差异**（614 字节） |
| `feedr fetch profile get` vs `/tmp/before-profile.json` | **无差异**（92 字节） |
| `feedr fetch articles-rule list` vs `/tmp/before-rules.json` | **无差异**（565 字节） |
| `diff -rq ~/.hskill/roster ~/.feedr/roster` | 无差异（名册目录逐文件一致） |

→ Spec AC6 满足。

## Step 4　登录态保留（Spec §13 未核实前提 / AC7）

命令：`feedr fetch timeline https://x.com/trq212 --max 5`（真实 Chrome profile、复制后的 `~/.feedr/browser`）。

- 退出码 0，stderr 为空，返回 `{"tweets":[…]}` 共 **5 条**（tweet_id `2122438328079524159`、`2122438326431154210`、`2122154124024381828`、`2121069823069421706`、`2121067561915916575`，时间 2026-11-13～11-16），**没有要求重新登录**。
- feedr 自己的节奏日志（`~/.feedr/browser/timeline_pace_log-2026-11-18.jsonl`）：`fetch_end … total_tweets=5, headless_fallback=false, duration_s=28.65, error=null`。

→ 抓取通过。未发现登录态因目录复制而失效的迹象（§13 的担心没有出现）。AC7 的字面要求是「需要登录才能看到完整内容的账号」，这里只验证了能带登录态取到时间线，未单独验证该账号有无登录墙内容，请验收时知悉。

### 发现：钥匙串授权会让命令卡住（需要人处理）

这次命令的墙钟时间是 **16 分 50 秒**，但 CPU 只用了约 5 秒；feedr 日志里 `cooldown` 事件落在 03:09:31，而进程启动于约 02:53——浏览器启动之前有约 16 分钟没有任何输出。

- **已核实：** 用同一账号再跑一次（`--max 2`，计时），进程在 90 秒后仍然没有写出任何事件，CPU 0%、没有子进程，同时系统里出现 macOS 的 `SecurityAgent` 进程（起始时间与该 feedr 进程一致）。代码上，浏览器启动前 `feedr/fetch/cookies.py::extract_cookies` 调用 `pycookiecheat.chrome_cookies`，它要读取钥匙串里的 "Chrome Safe Storage" 密钥。结论：命令在等钥匙串授权弹窗。我没有替用户点击弹窗，在 94 秒后结束了这次测试进程（退出码 143），没有产生任何抓取。
- **推断（未直接观察）：** 第一次的 16 分钟是同一个弹窗，等到它被应答后命令才继续往下走。
- **原因（推断）：** 钥匙串按调用程序授权。旧的 `browser-fetch` 用的是它自己 venv 里的 Python；现在是 `~/.local/share/uv/tools/feedr/bin/python3`（另一个可执行文件），需要重新授权一次。是否「始终允许」，以及之后重装 feedr（`uv tool install --force --reinstall`）是否会再次触发，**未核实**。
- **影响：** 在有人看着屏幕、点击弹窗之前，`feedr fetch timeline` / `feedr sync fetch x` 以及任何需要读 Chrome cookie 的命令都会无限等待。无人值守或定时运行的 sync-xtimeline 会因此挂住。
- **建议（产品决定，非本次范围）：** 验收前由用户在终端里手动跑一次 `feedr fetch timeline …`，在弹窗里选「始终允许」；之后再做 AC8。是否要在 feedr 里加超时或在 README 中写明，留给交出方决定。
- 测试进程结束后，系统里仍可能残留一个钥匙串弹窗，需要用户手动关闭（取消/拒绝即可，不影响数据）。

## Step 6　旧数据未被改动（只复制，不删除）

| 目录 | 切换前 | 切换后 |
|---|---|---|
| `~/.hskill/roster` 文件数 | 4 | 4 |
| `~/.hskill/browser-fetch` 文件数 | 3070 | 3070 |
| `~/.hskill/browser-fetch/contexts/timeline_pace.json` mtime | 11-17 09:04 | 11-17 09:04（未变） |
| `~/.hskill/roster/state.json` mtime | 11-17 09:05 | 11-17 09:05（未变） |

`~/.feedr/browser` 现有 3071 个文件 = 复制来的 3070 个 + 今天 feedr 在新位置写下的 1 个节奏日志。旧目录没有任何新增、删除或改写。

→ AC6 的「只复制不删除」与 Spec D10 满足。

## 未做 / 留给交出方

- **Step 5**：合并、部署改动的 6 个 skill 后，手动各跑一轮 sync-xtimeline、sync-ytchannel、sync-website、clip-url 抓一篇文章、`manage-creators list`、`capture-opinion show <id>`（即 Spec AC8），并把结果追加到本文件。先处理上面的钥匙串授权。
- **Step 7**：Step 5 完成后的最终验收提交。本文件已随 Step 1–4、6 的记录先行提交，便于验收方在交接工作区里核对。
- **过渡期风险（Spec §9）：** 现在 `~/.feedr` 已初始化，在 skill 部署完成之前不要运行旧版 sync-*、manage-creators、capture-opinion，否则 `~/.hskill/roster` 与 `~/.feedr/roster` 的游标会分叉。

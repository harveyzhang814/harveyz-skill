---
name: manage-roster
version: "0.1.1"
description: "Maintain the roster of watched creators and their channels — the shared watchlist behind sync-xtimeline and sync-ytchannel. Add a channel URL, merge two handles that turn out to be the same person, rename a placeholder, view the roster with cursor state. Trigger phrases: '/manage-roster add <url>', '/manage-roster list', '/manage-roster merge <a> <b>', '/manage-roster rename <id> <name>', '/manage-roster remove <id>', 'watch this X account', 'watch this YouTube channel', 'who am I following'. Does not fetch anything — running an incremental fetch is sync-xtimeline / sync-ytchannel; writing a creator's profile is the cognition layer."
user_invocable: true
---

# manage-roster

维护"关注了哪些人、每个人有哪些渠道"这份名册。抓取本身不归它管——`sync-xtimeline` 和 `sync-ytchannel` 从这份名册读渠道列表去抓。

**渠道必属于一个人。** 机构号、聚合频道也当人处理。`add` 会自动建一个占位人（名字先用 handle 顶着），之后用 `merge` 把"这俩 handle 其实是同一个人"合起来。

**这个 skill 只写 `registry.json`。** 游标归抓取层写，画像归认知层写，它一概不碰。

## 初始化（run first）

```bash
python3 scripts/roster_locate.py
```

若输出 `NOT_FOUND: <error>`（exit 1），向用户报告"roster tool 未安装：{error}"，流程终止。

若输出 `FOUND: <path>`，检查配置：

```bash
ls ~/.hskill/roster/config.json 2>/dev/null && echo "EXISTS" || echo "NOT_FOUND"
```

**若 `NOT_FOUND`：**

1. 询问用户名册数据要存在哪个目录（`DATA_DIR`，必须由用户手动提供，不得猜测）。可建议默认值 `~/.hskill/roster`。提醒用户：这个目录里的画像文件是累积出来的、删了长不回来，值得跟笔记一样对待（`registry.json` 和 `state.json` 都可重建，画像不能）。
2. 运行 `<roster_path> init <DATA_DIR>`。

**若用户此前用过 sync-xtimeline / sync-ytchannel**，初始化后问一次是否迁移旧关注列表：

```bash
<roster_path> migrate \
  --from-xtimeline "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-xtimeline/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")" \
  --from-ytchannel "$(python3 -c "import json,pathlib;print(pathlib.Path(json.loads((pathlib.Path.home()/'.hskill/sync-ytchannel/config.json').read_text())['DATA_DIR']).expanduser()/'watchlist.json')")"
```

任一旧配置不存在就省掉对应的参数。迁移是幂等的，重复跑安全。迁移后告诉用户：每个 handle 现在各自是一个人，同一个人的 X 和 YouTube 需要用 `merge` 合并，并主动列出名字相近的候选对给用户确认——**不要自己替用户合并**。

## 用法

`<roster>` 指 `roster_locate.py` 输出的路径。

| 用户说 | 运行 | 报告 |
|---|---|---|
| `add <url>` | `<roster> registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字 |
| `list` | `<roster> registry list` | 原样展示。`EMPTY` 表示还没关注任何人 |
| `merge <a> <b>` | `<roster> registry merge <a> <b>` | `OK merged b into a` → 告知 b 的 id 已进 aliases，旧引用仍可查到 |
| `rename <id> <name>` | `<roster> registry rename <id> <name>` | `OK` |
| `remove <id>` | `<roster> registry remove <id>` | 输出里带画像归档路径时，**必须把这个路径转告用户**——画像没被删，只是移走了 |
| `remove <platform>:<handle>` | `<roster> registry remove <platform>:<handle>` | `OK removed ...`。人还留着 |

所有失败原样把 stderr 报给用户，不要自行改写或重试。

## 边界

不抓取、不翻译、不写画像、不进 Obsidian。跑一次增量抓取走 [sync-xtimeline](../sync-xtimeline/) 或 [sync-ytchannel](../sync-ytchannel/)。单条物料入库走 [clip-url](../../research/clip-url/)，单个视频精读走 [learn-video](../../research/learn-video/)。

设计文档：`docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/roster_locate.py` | 定位 roster launcher（跟 `browser_fetch_locate.py` 同款，独立副本） |

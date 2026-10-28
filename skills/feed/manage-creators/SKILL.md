---
name: manage-creators
version: "0.3.2"
description: "Maintain the roster of watched creators and their channels — the shared watchlist behind sync-xtimeline, sync-ytchannel and sync-website. Add a channel URL, merge two handles that turn out to be the same person, rename a placeholder, view the roster with cursor state. Trigger phrases: '/manage-creators add <url>', '/manage-creators list', '/manage-creators merge <a> <b>', '/manage-creators rename <id> <name>', '/manage-creators remove <id>', 'watch this X account', 'watch this YouTube channel', 'who am I following'. Does not fetch anything — running an incremental fetch is sync-xtimeline / sync-ytchannel / sync-website; writing a creator's profile is the cognition layer."
user_invocable: true
---

# manage-creators

维护"关注了哪些人、每个人有哪些渠道"这份名册。抓取本身不归它管——`sync-xtimeline`、`sync-ytchannel`、`sync-website` 从这份名册读渠道列表去抓。

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
3. 若 `~/.hskill/sync-xtimeline/config.json` 或 `~/.hskill/sync-ytchannel/config.json` 存在（旧版关注列表），问用户一次是否迁移；同意就读 `references/migration.md` 执行。迁移后**不要自己替用户 `merge`**，只列出名字相近的候选对，交给用户确认。

**roster 命令报「名册数据是旧 schema」时**，运行 `<roster_path> migrate-schema`（幂等），然后重跑原命令。

## 用法

`<roster>` 指 `roster_locate.py` 输出的路径。

| 用户说 | 运行 | 报告 |
|---|---|---|
| `add <url>` | `<roster> registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字。支持 X、YouTube、网站列表页 URL（后者 `platform` 为 `website`）。渠道按归一 key（去 `@`、trim、小写）去重，重复时报"已在名册中"。 |
| `list` | `<roster> registry list` | 原样展示。`EMPTY` 表示还没关注任何人 |
| `merge <a> <b>` | `<roster> registry merge <a> <b>` | `OK merged b into a` → 告知 b 的 id 已进 aliases，旧引用仍可查到 |
| `rename <id> <name>` | `<roster> registry rename <id> <name>` | `OK` |
| `remove <id>` | `<roster> registry remove <id>` | 输出里带画像归档路径时，**必须把这个路径转告用户**——画像没被删，只是移走了 |
| `remove <platform>:<handle>` | `<roster> registry remove <platform>:<handle>` | `OK removed ...`。人还留着 |

所有失败原样把 stderr 报给用户，不要自行改写或重试。

## 边界

不抓取、不翻译、不写画像、不进 Obsidian。跑一次增量抓取走 [sync-xtimeline](../sync-xtimeline/)、[sync-ytchannel](../sync-ytchannel/) 或 [sync-website](../sync-website/)。单条物料入库走 [clip-url](../../research/clip-url/)，单个视频精读走 [learn-video](../../research/learn-video/)。

设计文档：`docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/roster_locate.py` | 定位 roster launcher（跟 `browser_fetch_locate.py` 同款，独立副本） |
| `references/migration.md` | 从旧版 sync-xtimeline / sync-ytchannel 关注列表迁移 |

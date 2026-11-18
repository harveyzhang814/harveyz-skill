---
name: manage-creators
version: "0.4.0"
description: "Maintain the roster of watched creators and their channels — the shared watchlist behind sync-xtimeline, sync-ytchannel and sync-website. Add a channel URL, merge two handles that turn out to be the same person, rename a placeholder, view the roster with cursor state. Trigger phrases: '/manage-creators add <url>', '/manage-creators list', '/manage-creators merge <a> <b>', '/manage-creators rename <id> <name>', '/manage-creators remove <id>', 'watch this X account', 'watch this YouTube channel', 'who am I following'. Does not fetch anything — running an incremental fetch is sync-xtimeline / sync-ytchannel / sync-website; writing a creator's profile is the cognition layer."
user_invocable: true
---

# manage-creators

维护"关注了哪些人、每个人有哪些渠道"这份名册。抓取本身不归它管——`sync-xtimeline`、`sync-ytchannel`、`sync-website` 从这份名册读渠道列表去抓。

**渠道必属于一个人。** 机构号、聚合频道也当人处理。`add` 会自动建一个占位人（名字先用 handle 顶着），之后用 `merge` 把"这俩 handle 其实是同一个人"合起来。

**这个 skill 只写 `registry.json`。** 游标归抓取层写，画像归认知层写，它一概不碰。

## 初始化（run first）

```bash
command -v feedr
```

若找不到，向用户报告并终止流程：

> feedr 未安装：uv tool install git+https://github.com/harveyzhang96/feedr && feedr fetch install-browser

若找到，直接运行下文的 `feedr roster` 命令。命令在 stderr 第一行用固定标记报告初始化状态：

- ``NOT_INITIALIZED: run `feedr init` ``：名册从未初始化过。先运行 `feedr init`（有旧数据时是纯迁移，不需要问用户），然后重跑原命令。
- 若 `feedr init` 返回 `MISSING_ROSTER_DIR`（exit 2）：feedr 推不出名册目录，需要用户提供。
  1. 询问用户名册数据要存在哪个目录（必须由用户手动提供，不得猜测）。可建议默认值 `~/.feedr/roster`。提醒用户：这个目录里的画像文件是累积出来的、删了长不回来，值得跟笔记一样对待（`registry.json` 和 `state.json` 都可重建，画像不能）。
  2. 运行 `feedr init --roster-dir <目录>`，然后重跑原命令。

**`feedr roster` 命令报「名册数据是旧 schema」时**，运行 `feedr roster migrate-schema`（幂等），然后重跑原命令。

## 用法

| 用户说 | 运行 | 报告 |
|---|---|---|
| `add <url>` | `feedr roster registry add <url>` | `OK <id> <platform>:<handle>` → 告知已加入，并提示这是占位人、可用 `rename` 填正式名字。支持 X、YouTube、网站列表页 URL（后者 `platform` 为 `website`）。渠道按归一 key（去 `@`、trim、小写）去重，重复时报"已在名册中"。 |
| `list` | `feedr roster registry list` | 原样展示。`EMPTY` 表示还没关注任何人 |
| `merge <a> <b>` | `feedr roster registry merge <a> <b>` | `OK merged b into a` → 告知 b 的 id 已进 aliases，旧引用仍可查到 |
| `rename <id> <name>` | `feedr roster registry rename <id> <name>` | `OK` |
| `remove <id>` | `feedr roster registry remove <id>` | 输出里带画像归档路径时，**必须把这个路径转告用户**——画像没被删，只是移走了 |
| `remove <platform>:<handle>` | `feedr roster registry remove <platform>:<handle>` | `OK removed ...`。人还留着 |

所有失败原样把 stderr 报给用户，不要自行改写或重试。

## 边界

不抓取、不翻译、不写画像、不进 Obsidian。跑一次增量抓取走 [sync-xtimeline](../sync-xtimeline/)、[sync-ytchannel](../sync-ytchannel/) 或 [sync-website](../sync-website/)。单条物料入库走 [clip-url](../../research/clip-url/)，单个视频精读走 [learn-video](../../research/learn-video/)。

设计文档：`docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`。

## 参考文件

| 文件 | 用途 |
|------|------|
| `references/migration.md` | 旧版 sync-xtimeline / sync-ytchannel 关注列表（watchlist.json）：feedr 不再迁移 |
| [feedr](https://github.com/harveyzhang96/feedr)（外部 CLI） | 名册命令 `feedr roster ...` 与初始化 `feedr init` 都由它提供 |

---
name: note-creator
version: "0.1.0"
description: "Record your own judgment about a creator on the roster — you say what you think, this skill tidies it into points, stamps it with the current time, shows it back for confirmation, then appends it to that creator's profile. Trigger phrases: '/note-creator <name>', '/note-creator', 'I have a take on this person', '记一下我对 X 的看法', '这人最近怎么样', 'what do I think of <name>', 'show me my profile of <name>'. Adding or removing a watched channel is manage-roster; running an incremental fetch is sync-xtimeline / sync-ytchannel. Never saves anything to Obsidian and never tags — saving an article or tweet is clip-url."
user_invocable: true
---

# note-creator

给名册上的人记一笔判断。**判断由你出，这个 skill 只做整理、盖时间戳、落盘。**

它写的是 `profiles/<creator-id>.md`——整套数据里唯一不可重建的部分。名册和游标删了重加一遍就回来了，画像不会。所以这里有两条硬规矩：

- **未经你确认不写盘。** 整理后的正文先回显，你点头才落。
- **只写 `profiles/`。** 名册归 manage-roster，游标归抓取层，一概不碰。

## 初始化（run first）

```bash
python3 scripts/roster_locate.py
```

若输出 `NOT_FOUND: <error>`（exit 1），向用户报告"roster tool 未安装：{error}"，流程终止。

若从未初始化过名册（`~/.hskill/roster/config.json` 不存在），让用户先跑一次 [manage-roster](../manage-roster/)，流程终止。

`<roster>` 指 `roster_locate.py` 输出的路径。

## 记一笔（默认动作）

### 1. 确定是谁

```bash
<roster> registry list
```

从用户提到的名字或 handle 里找 `creator_id`（每人一行，行首那个词就是 id）。

- 名册为空（`EMPTY`）或找不到匹配：告诉用户这人不在名册上，让他先用 manage-roster 加渠道，流程终止。**不要自己加。**
- 多个候选：列出来让用户选，**不要猜**。写错人的画像比不写更糟——观察是只追加的，写进去就在那儿了。

### 2. 整理

把用户口述的内容归纳成要点：提炼观点、重组逻辑、去掉口语碎片，用整齐的 Markdown 呈现。

三条底线：

- **不发明。** 用户没说的判断不能加，包括你自己对这个人的印象。
- **不加依据。** 不要去查名册、去翻抓取下来的物料给用户的话找佐证。这一笔的来源就是他本人。
- **拿不准的地方保留原话。** 归纳时如果某句话有两种理解，别替他选一种，原样留着。

### 3. 回显确认

把三样东西一起展示给用户：`creator_id` 和显示名、时间戳、整理后的正文。

用户要改就改完再确认一次。**没拿到明确的确认，不要执行第 4 步。**

### 4. 落盘

时间戳取当前本地时间：

```bash
date "+%Y-%m-%d %H:%M"
```

```bash
<roster> profile append <creator_id> --date "<YYYY-MM-DD HH:MM>" <<'EOF'
<整理后的正文>
EOF
```

正文走 stdin，不要塞进 `--body`——归纳后的多行 Markdown 走命令行参数会被引号和换行搞坏。

依据默认记成 `人工`，这个值同时就是作者标记（将来 agent 自己写的观察会填真实来源）。**只有用户主动说了这一笔是看了什么才来的**（比如给了一条推文链接），才加 `--source "<用户给的来源>"`。

成功输出 `OK <画像文件路径>`，把路径转告用户。

## 看画像

```bash
<roster> profile show <creator_id>
```

`EMPTY` 表示这人还没有画像。原样展示，不要替用户总结。

## 边界

不抓取、不翻译、不写名册、不改游标、不进 Obsidian、不打标。

关注谁走 [manage-roster](../manage-roster/)，跑一次增量抓取走 [sync-xtimeline](../sync-xtimeline/) 或 [sync-ytchannel](../sync-ytchannel/)，单条物料入库走 [clip-url](../../research/clip-url/)。

「当前判断」那一段（从观察重算出一句总结）现在还没有入口，观察攒够了再说。

两个已知限制，用户问起时如实说：

- 写盘是全文件重写，没有加锁。你在编辑器里手改画像的同时跑这个 skill，后落盘的赢。
- 新条目固定插在最前，不按时间戳重排。补录一条旧时间的观察，它会出现在最上面。

设计文档：`docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md`。

## 参考文件

| 文件 | 用途 |
|------|------|
| `scripts/roster_locate.py` | 定位 roster launcher（跟 manage-roster 同款，独立副本） |

# 人与渠道名册（roster）设计

## 元信息

- **设计日期**：2026-08-26
- **状态**：待实现
- **涉及组件**：新增 `roster` tool、新增 `manage-roster` skill、改造 `sync-xtimeline` / `sync-ytchannel`
- **代码基线**：`sync-xtimeline` v0.2.0、`sync-ytchannel` v0.1.0（`staging` @ `ea2e522`）
- **本文范围**：只定"人和渠道这两个东西是什么、存在哪、谁能写"。不含调度、不含 agent 判断的执行权、不含认知层 skill 的实现。

---

## 0. 主线

> **整个设计只由一条线推出：渠道数据可重建，人的画像不可重建。**

分三个文件、写入权按文件边界切、画像只追加不覆盖、名册不寄生在 `browser-fetch-mcp` 底下——这四个决定没有一个是独立成立的，全部是这条线的直接推论。

这句可证伪：只要能指出上述任一决定不依赖这条线也能推出，或者找到一个与这条线矛盾的决定，主线即被推翻。

---

## 1. 定位

### 1.1 渠道是事实的宿主

渠道（channel）的字段——平台、URL、handle、抓取游标、上次失败原因——真值全在平台那边。字段错了叫 bug，重抓一次就该对。

整份渠道数据**可重建**：删掉游标重跑，最坏情况是刷一次基线，漏报一批新物料，没有任何东西永久丢失。

### 1.2 人是判断的宿主

人（creator）的字段——为什么关注他、他擅长什么、他的物料值不值得深读、上次读完的反馈——平台上不存在这些信息，真值在用户和 agent 这边。字段"错了"不叫 bug，叫判断过时。

这份数据**不可重建**：删掉就是删掉，重抓一百次也长不回来，因为它是跨多次运行累积出来的。

### 1.3 归属关系

**每个渠道必属于且只属于一个人。** 机构号、聚合频道一律当作"人"处理——不为它们单开一个实体类型。

不存在孤儿渠道；删除一个人即删除其名下全部渠道。人可以暂时没有渠道（认识但还没订阅）。

**代价**：机构号被迫进入一个为"人"设计的画像模型，"他擅长什么"这类字段对一个新闻聚合号是空转的。接受这个代价换取模型少一个分支。

### 1.4 主键

**人的主键不能是 handle。** 同一个人在 X 是 `karpathy`、在 YouTube 是 `AndrejKarpathy`，且 handle 会改。人用自己的稳定 slug 作 `id`，创建后不可变。

渠道用 `(platform, handle)` 复合键定位；归属由它嵌在哪个 creator 对象下表达，不另存 `creator_id` 外键（见 3.1）。

**这是必须改的一处**：`sync-xtimeline/scripts/watchlist.py` 和 `sync-ytchannel/scripts/watchlist.py` 目前都拿 handle 当主键。

**已知缺陷**：渠道主键里的 handle 本身是可变的——博主改名后，`state.json` 里那条游标就失联了，表现为该渠道被当成新渠道重新刷一次基线，漏报改名前后那一批物料。平台侧有不可变 id（YouTube 的 `UCxxx`、X 的数字 user id），但当前抓取路径 `browser-fetch-mcp` 的两个工具都不返回它。不为此改抓取契约：改名是低频事件，代价是漏一批，用户重新 `add` 即可恢复。若日后抓取侧开始返回不可变 id，渠道主键应换成它，`handle` 降为展示字段。

---

## 2. 三层与写入权

### 2.1 三层

| 层 | 管什么 | 现状 |
|---|---|---|
| **名册** | 人是谁、有哪些渠道、渠道归谁 | 不存在，散在两个 `watchlist.json` |
| **抓取** | 去平台拿新物料、推进游标 | 两个 sync skill，已有 |
| **认知** | 他擅长什么、为什么关注、值不值得深读 | 不存在，后续 skill |

### 2.2 写入权用文件边界切，不用字段约定

第 1 节那条线落到实现上：三类数据的变更频率差两个数量级，写入方也不同，所以是三个文件。

| 文件 | 内容 | 唯一写入方 | 变更频率 | 丢失后果 |
|---|---|---|---|---|
| `registry.json` | 人的身份、别名；渠道定义 | 名册层（代表用户） | 加人/加渠道时 | 重加一遍，烦但可恢复 |
| `state.json` | 游标、last_run、last_error | 抓取层 | 每次 run | 刷一次基线，漏一批新物料 |
| `profiles/<creator-id>.md` | 画像：观察记录 + 当前判断 | 认知层 | 读完一批物料后 | **不可恢复** |

**规则**：一层只能写自己能重建的东西。画像是例外——它不可重建，因此只能追加，不能原地覆盖已有的观察条目。

越权因此是文件级的、一眼可见的：抓取脚本不打开 `registry.json` 的写句柄，认知 skill 不碰 `state.json`。不依赖"约定好别改那个字段"——那种约定迟早会破。

```
  用户 ──> manage-roster ──写──> registry.json ──读──> sync-* ──写──> state.json
                                      │                   │
                                      │                   └──产出──> 物料
                                      │                                │
                                      └──读──> 认知 skill <────────────┘
                                                    │
                                                    └──追加──> profiles/<id>.md
```

**代价**：`list` 这类展示命令要 join 三份文件。文件小、本地读，性能无所谓；真实代价是多了三处"文件不存在 / schema 不匹配"的边界要处理，以及用户手改文件时得知道改哪一份。

---

## 3. 数据契约

全部落在一个共享 `DATA_DIR` 下（不再是两个 skill 各一个）。**这个路径由 `roster` tool 单独持有**：配置在 `~/.hskill/roster/config.json`，两个 sync skill 的 `scripts/config.py` 改为向 `roster` 要，不再各自读 `~/.hskill/sync-*/config.json`（旧配置文件在迁移后废弃，但不自动删除）：

```
<DATA_DIR>/
  registry.json
  state.json
  profiles/<creator-id>.md
  digests/<platform>/ # 抓取层产出。两个 skill 共用 DATA_DIR 后按平台分子目录，
                      # 否则同一天的两份 digest 会撞文件名
  tweets/<handle>.json # sync-xtimeline 归档，沿用现状
```

### 3.1 registry.json

```json
{
  "schema_version": 1,
  "creators": [
    {
      "id": "andrej-karpathy",
      "display_name": "Andrej Karpathy",
      "aliases": ["karpathy"],
      "placeholder": false,
      "added_at": "2026-08-26",
      "channels": [
        {"platform": "x",       "handle": "karpathy",        "url": "https://x.com/karpathy"},
        {"platform": "youtube", "handle": "AndrejKarpathy",  "url": "https://youtube.com/@AndrejKarpathy"}
      ]
    }
  ]
}
```

- `id`：slug，创建后不可变。渠道通过所在的 creator 对象隐式归属，不再冗余存 `creator_id`。
- `placeholder`：`true` 表示这个人是 `add` 时自动建的占位，`display_name` 只是从 handle 推的，等待用户确认或合并。
- `channels[].handle`：在该平台内唯一。跨平台可以重名，`(platform, handle)` 才是渠道主键。

### 3.2 state.json

```json
{
  "schema_version": 1,
  "channels": {
    "x:karpathy": {
      "cursor": {"type": "last_seen_id", "value": "1876543210987654321"},
      "last_run": "2026-08-26T09:14:00+08:00",
      "last_error": null
    },
    "youtube:AndrejKarpathy": {
      "cursor": {"type": "seen_urls", "value": ["https://...", "..."]},
      "last_run": "2026-08-26T09:14:03+08:00",
      "last_error": "fetch_channel_videos timed out"
    }
  }
}
```

游标**不统一语义**，按平台各存各的：X 的 snowflake id 单调递增可比大小，YouTube 的 video id 不透明只能判"见过没有"。强行统一会逼 X 那边退化成 URL 集合，白丢一个更省的表示。`cursor.type` 显式标出用的是哪种。

`compute_update` 这两个纯函数因此**不需要改**——它们只吃 `entry + 物料`，跟存储形态无关。

### 3.3 profiles/&lt;creator-id&gt;.md

```markdown
---
creator_id: andrej-karpathy
updated_at: 2026-08-26
---

## 当前判断

<可从下方观察重算的摘要。这一段允许重写。>

## 观察

### 2026-08-26 · 依据：sync-xtimeline 本次 12 条推文

<一条观察，带依据>

### 2026-08-19 · 依据：sync-ytchannel 3 个新视频标题

<更早的观察，永不改写>
```

"观察"段落**只追加，不改写**——这是全套数据里唯一不可重建的部分。"当前判断"允许重写，因为它可以从观察重算。

每条观察必须带日期和依据来源。理由：三个月后看到"他擅长 X"，得能判断这是基于 40 条推文写的，还是基于 3 个视频标题猜的。渠道数据的 `last_seen` 不需要出处——它只有一个可能的来源。

---

## 4. 载体：独立 CLI tool

名册做成一个独立 tool，形态对齐 `tools/hub`（普通 CLI，不是 MCP server），装到 `~/.hskill/tools/roster`，配置在 `~/.hskill/roster/config.json`（只存 `DATA_DIR`，沿用两个 sync skill 现有的配置模式）。

它比 `hub` 更轻：读写 JSON 和 Markdown，stdlib 够用，不需要 venv。

**为什么不合并进 `browser-fetch-mcp`**：那个 tool 的 `tool.json` 里 `uninstallPaths` 覆盖整个 `~/.hskill/tools/browser-fetch-mcp`——它是个删掉重装属于正常操作的抓取后端（Playwright 升级、登录态失效、venv 损坏）。把第 1 节里唯一不可重建的数据托管在它底下，是这个设计里最不该犯的错。

次要理由两条：名册的两个主要写入方（`manage-roster`、认知 skill）根本不抓取，为读写本地 JSON 去起一个 headless 浏览器 MCP server 触达方式不对位；名册加个字段就要给 `browser-fetch-mcp` 升版本，而它另外两个消费者 `clip-url` / `extract-url` 跟名册无关却被卷进升级。

**代价**：多一个安装物；每个消费者 skill 要再复制一份 locate 脚本（现在两份 `browser_fetch_mcp_locate.py`，会再加同款的 `roster_locate.py`，共四份副本）。这是本仓库既有的跨 skill 共享模式，接受。

---

## 5. 命令与流程

### 5.1 manage-roster（新 skill）

名册的人机入口，唯一能写 `registry.json` 的一方。

| 子命令 | 行为 |
|---|---|
| `add <url>` | 解析出 platform + handle，自动建占位人（`display_name` 从 handle 推、`placeholder: true`），挂上渠道 |
| `merge <id-a> <id-b>` | 两个人合并成一个：保留 `<id-a>` 的 `id` 和 `display_name`，`<id-b>` 的 `id` 落入 `aliases`（旧引用仍可查到），渠道归并，两份画像的「观察」段按日期归并、「当前判断」置空待重算 |
| `rename <id> <display_name>` | 填正式名字，清 `placeholder` 标记 |
| `remove <id>` \| `remove <platform>:<handle>` | 删人或只删一个渠道。**画像不删，移到 `profiles/archived/`** |
| `list` | join 三份文件展示：人 → 渠道 → 游标状态 → 画像是否存在 |

**`add` 自动建占位人，不要求指定归属。** 加关注是高频动作，合并是低频动作，摩擦放在低频那一侧。

**代价**：名册里会攒下一批 `placeholder: true` 的半成品实体等着收拾。`list` 需要把它们标出来，否则会一直被忽略。

**`remove` 不删画像**：删人只从 `registry.json` 摘掉条目，画像移入 `profiles/archived/`。理由是第 1.2 节——画像是全套数据里唯一不可重建的部分，一个日常操作不该能永久销毁它。真要清掉，用户自己删那个目录。代价是取关又重新关注同一个人时，会捡回一份可能已经过时的旧画像，`list` 需要提示这种情况。

### 5.2 sync-xtimeline / sync-ytchannel（改造）

- `add` / `remove` / `list` 三个子命令**从这两个 skill 移除**，迁到 `manage-roster`。它们退化成纯执行器，只剩 `run`（`sync-xtimeline` 另保留 `view`）。
- `watchlist.py` 拆成两半：读 `registry.json` 取本平台渠道列表（只读）、读写 `state.json` 的游标（只写自己那部分）。`compute_update` 原样保留。
- `run` 的对外契约不变：无交互、`EMPTY` / `WRITTEN: <path>`、写盘成功才推进游标。这是后续调度层要依赖的接口，本次不动它。

**代价**：`/sync-xtimeline add` 的肌肉记忆作废。这是一次性的。

---

## 6. 迁移

现有两份 `watchlist.json` 各在各的 `DATA_DIR`，合并成一份。

一次性脚本，读旧写新：

| 旧字段 | 去向 |
|---|---|
| X `{handle, profile_url, last_seen_tweet_id}` | creator（slug 自 handle，`placeholder: true`）+ channel `x:<handle>` + `state.json` 里 `cursor.type = last_seen_id` |
| YT `{handle, channel_url, seen_urls}` | creator（同上）+ channel `youtube:<handle>` + `state.json` 里 `cursor.type = seen_urls` |

迁移后每个 handle 各自成一个人，需要用户手动跑一轮 `merge` 把同一个人的 X 和 YT 合到一起。这一步无法自动化——判断"这两个 handle 是同一个人"正是第 1.2 节说的判断类信息。

**要改的测试**：`sync-xtimeline/tests/test_watchlist.py`、`sync-ytchannel/tests/test_watchlist.py`（存储层改了）。`test_digest.py` / `test_render_digest.py` / `test_archive_tweets.py` / `test_render_view.py` 不受影响（它们吃的是 report 结构，没变）。

**迁移的代价**：迁移脚本本身是一次性代码，跑完就该删。保留它会让 `registry.json` 出现"可能被旧格式覆盖"的第二个写入方。约定：迁移脚本随 `manage-roster` 首次运行执行一次，之后不再暴露。

---

## 7. 边界（本设计明确不做）

- **不合并跨渠道输出**。一份 digest 里不会把同一个人的推文和视频并到一节。人是判断的宿主，不是输出的聚合单位。
- **不做调度**。`run` 的接口保持不变，谁来定时触发是另一个设计。
- **不做判断的执行权**。认知层只产出画像文件，不驱动 `learn-video` / `clip-url` 等任何下游动作。
- **不实现认知 skill**。本设计只定死 `profiles/` 的契约和它的写入权边界；那个 skill 自己是下一份 spec。
- **不做插件化抓取策略**。加新平台仍然是新写一个 sync skill。名册这一层不为此提供抽象——需求没有出现过。
- **不与 Video-Learner 打通**。那边只有每个视频上一个自由文本的 `uploader` 显示名，要 join 到本名册只能做模糊字符串匹配。等它先有稳定创作者身份再说。

---

## 8. 替代方案与为什么没选

| 方案 | 为什么没选 |
|---|---|
| 人只作分组标签，不存画像 | 用户明确要在人身上挂 agent 分析出的判断信息。标签模型承不住带出处的累积观察。 |
| 渠道可以不属于人 | 用户选择强制归属。少一个分支，代价是机构号被当人处理。 |
| 名册合并进 `browser-fetch-mcp` | 见第 4 节：不可重建的数据不能托管在删掉重装属于正常操作的组件下。 |
| 只定数据契约，不做 tool，每 skill 自带读写副本 | 消费者数量会从 3 涨（用户已说明后续要围绕这几个 skill 建 agent）。schema 改漏会静默读到错字段，不报错，画像里悄悄少一段。 |
| 名册 CRUD 留在现有 sync skill 里加参数 | 同一份 `registry.json` 会有两个平级写入方，第 2.2 节的规则当场破掉；跨平台的 `merge` 放在任何单平台 skill 里都不对位。 |
| 游标统一成一种语义 | X 的 snowflake id 可比大小，统一会逼它退化成 URL 集合，白丢一个更省的表示。 |

---

## 9. 未确认项

| 项 | 状态 |
|---|---|
| ~~Video-Learner 是否已有人/渠道名册~~ | **已查证：没有。** 只有 `tasks.uploader` 一个自由文本显示名（`core/orchestrator/db.js`），无稳定创作者身份。不存在主键对齐问题 |
| skill 之间直接互调对方 `scripts/` 是否可靠 | 判断为不可靠（安装后路径能算但脆），未实测。本设计走 tool 路线绕开了这个问题 |
| 命名 | `roster` / `manage-roster` / `creator` / `channel` 均为提议，可替换。`manage-roster` 对齐现有 `manage-dir` / `manage-docs` 的动词-名词约定 |
| 认知层 skill 的名字与触发方式 | 下一份 spec |

---

## 10. 源码锚点

| 位置 | 与本设计的关系 |
|---|---|
| `skills/research/sync-xtimeline/scripts/watchlist.py` | 待拆：CRUD 迁走，`compute_update`（第 60 行起）保留 |
| `skills/research/sync-ytchannel/scripts/watchlist.py` | 同上，`compute_update` 在第 100 行起；`handle_from_url` 的 URL 解析逻辑迁到 `manage-roster` |
| `skills/research/*/scripts/config.py` | 现有 `DATA_DIR` 配置模式，`roster` tool 沿用 |
| `skills/research/*/scripts/browser_fetch_mcp_locate.py` | locate 脚本的既有形态，`roster_locate.py` 照此复制 |
| `tools/hub/tool.json` | 非 MCP server 的 CLI tool 形态先例 |
| `tools/browser-fetch-mcp/tool.json` | `uninstallPaths` / `configPaths` 的写法；也是第 4 节不合并的证据来源 |
| `lib/installer.js:133-162` | tool 的安装落点与 `extraPaths` 处理 |

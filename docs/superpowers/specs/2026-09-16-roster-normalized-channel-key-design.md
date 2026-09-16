# 名册渠道键归一化设计

## 元信息

- **设计日期**：2026-09-16
- **状态**：待实现
- **涉及组件**：改造 `roster` tool（主体）；`scholia` 的 registry join 改精确比较；`manage-creators` / `sync-*` 的 SKILL.md 文档层面跟进。`learn-video` 的 `build_creator_index.py` **零改动**。
- **代码基线**：`harveyz-skill` @ `staging` (`7fbd706`)；`scholia` v0.5.0
- **本文范围**：只定"渠道的归一键存在哪、谁算、游标键怎么迁"。**修订** `2026-08-26-creator-channel-registry-design.md` §1.4 的渠道主键定义。不改抓取契约、不改画像层、不改 `creators.json` 的 schema、不改人的主键（creator `id`）。

---

## 0. 主线

> **归一这件事，在事实进入名册的那一刻做一次；读的人只做字符串比较。**

这句可证伪：只要能指出某个消费者**仍然必须实现归一规则才能完成 join**，主线即被推翻。

由它直接推出：`key` 存进 `registry.json`（§2）、`find_channel` 改按 `key` 查（§3.1）、游标键换成 `key`（§3.2）、scholia 的 join 不再依赖规则（§4）。

**一处诚实的例外**：scholia 仍保留一个归一函数，用来清洗 `/api/creator/:key` 的路由入参。那不是 join 的一部分——它错了只会让手输的怪大小写 URL 404，不会让 `watched` 静默算错。详见 §4.2。

---

## 1. 这是个现行缺陷，不是预防性改动

### 1.1 实测复现

隔离环境（`HSKILL_ROSTER_CONFIG` 指向临时目录）跑 `roster registry add` 两次，同一个 YouTube 频道、URL 大小写不同：

```
add https://www.youtube.com/@TingHu888   →  OK tinghu888    youtube:TingHu888
add https://www.youtube.com/@tinghu888   →  OK tinghu888-2  youtube:tinghu888
```

**变成了两个人。** 而且 `_free_slug` 的防撞逻辑给第二个编了号，所以输出看起来像"正确识别出两个重名的人"——掩盖了它其实是同一个。

成因两处，都在代码里读得到：`urls.py:42` 的 `parse_channel_url` 原样返回 URL 里的 handle，不做小写化；`registry.py:43` 的 `find_channel` 做的是精确 `ch["handle"] == handle`。

**可达性**：YouTube handle 大小写不敏感（Google 官方文档，见 `2026-09-15-video-creator-index-design.md` §7.1），从两个地方复制同一个频道的链接就能踩到。

### 1.2 后果会传导

重复的人不只是名册难看：`sync-ytchannel` 会把这个频道当成两个渠道各抓一遍，各持一套独立游标，同一批新视频在摘要里出现两次。用户看到的是"这个博主怎么每条都发两遍"。

### 1.3 为什么现在做

归一规则目前有两份实现，且**已经不一致**：

| 输入 | `build_creator_index.py`（Python） | `creator-source.js`（JS） |
|---|---|---|
| `@@Foo` | `foo` | `@foo` |
| `@@@bar` | `bar` | `@@bar` |

实践中触发不到（yt-dlp 只给单个 `@`），所以这是**潜在分歧、不是现行 bug**。但没有任何测试把两边绑在一起。

决定性的是使用侧已确认：**将来会有 skill 读 `creators.json` 做同样的 join**（用户 2026-09-16 确认）。因为主线要求 `watched` 不落盘（见 `2026-09-15` 那份的 §0），每个想知道"他是不是我关注的人"的消费者都得自己做 registry join。规则实现数随消费者线性增长，而没有任何机制让它们一致。

**被否掉的替代**：共享测试向量（一份语言无关的 `输入 → 期望输出` 夹具，各实现都跑）。成本更低，但规则仍是 N 份实现，靠"记得让新消费者也跑这份夹具"维持，没有强制力。风险随消费者数量增长；本方案的风险归零。

---

## 2. 数据契约变更

### 2.1 `registry.json`

渠道对象新增 `key` 字段：

```json
{
  "platform": "youtube",
  "handle": "TingHu888",
  "key": "tinghu888",
  "url": "https://www.youtube.com/@TingHu888"
}
```

- **`handle`** 保留原始大小写，**降级为展示字段**。这是对 `2026-08-26` §1.4"渠道用 `(platform, handle)` 复合键定位"的修订。
- **`key`** 是归一后的形态，**join 与内部查找的唯一依据**。
- 归一规则不变：去前导 `@`、`strip`、转小写。规则本身在本文里不重新定义——它已经在 `2026-09-15` 那份的 §2.3。

`schema_version` 1 → 2。

### 2.2 为什么不直接把 `handle` 存成小写

那样会丢掉原始大小写。`TingHu888` 是用户在平台上看到的样子，名册的 `list` 输出要显示它。把展示值和匹配值合并成一个，等于用数据损失换一个字段——**代价比多一个字段大**。

---

## 3. roster 的改动（主体）

### 3.0 归一发生在 roster 的每一个查询入口

**这是本节最重要的一条，漏了会让三个 skill 当场全断。**

`sync-xtimeline` / `sync-ytchannel` / `sync-website` 都不直接读 `state.json`（实测 grep 确认，全部经 roster CLI），但它们调的是：

```
roster state get   <platform>:<handle>
roster state set   <platform>:<handle> ...
roster state fail  <platform>:<handle> ...
```

传进去的是从 `registry channels` 拿到的**原始 handle**。所以只改存储键而不改查询入口，`state get youtube:TingHu888` 就会查不到那条已经被改名为 `youtube:tinghu888` 的游标——表现为该频道被当成新渠道，刷一次基线、漏报一批。

**要求**：roster 在**所有**接受 `<platform>:<handle>` 的入口处先归一一次——`registry` 的查找与删除、`state` 的 `get`/`set`/`fail`/`drop`。归一是幂等的，所以调用方传原始 handle 还是传 `key` 都对。

**由此得到的收益**：`sync-*` 三个 skill **零代码改动**。它们可以继续传 handle；日后想改成传 `key` 也不会出错。这是把归一收进 roster 边界、而不是让调用方各自归一的直接结果——跟 §0 主线是同一个动作。

### 3.1 渠道查找改按 `key`

`find_channel(reg, platform, handle)` 的比较从 `ch["handle"] == handle` 改为比 `key`（入参按 §3.0 先归一）。

§1.1 那个 bug 由此消失：第二次 `add` 会命中已有渠道，报"已在名册中"，而不是建第二个人。

`add` 在写入时算 `key`；`merge` / `rename` / `remove` 保持 `key` 与 `handle` 一致。

**`channels` 子命令的输出要带上 `key`**——`sync-*` 和未来的消费者从这里取。

### 3.2 游标键：换成 `key`，迁移里一并改写

`state.json` 按 `channel_key(platform, handle)` 索引，形如 `"youtube:mattpocockuk"`（`state.py:37`）。改成按归一 key 索引。

**这一节曾被判定为本方案唯一可能真出事的地方**（游标键一变 → 频道被当成新渠道 → 重刷基线 → 漏报一批）。实测把它消解了：

| | 条数 |
|---|---|
| `state.json` 现有渠道条目 | 8 |
| 归一后键会变的 | **1**（`x:TingHu888` → `x:tinghu888`） |
| `registry.json` 现有渠道 | 8 |
| 归一后 `key ≠ handle` 的 | 2（`x:TingHu888`、`youtube:PlatoStone`；后者在 `state.json` 里没有游标条目） |

**迁移做的是重命名，不是丢弃**，所以那些游标值原样保留 → **漏报为零**。

**更正（2026-09-16 实跑真实数据后）**：上表"归一后键会变的"一栏原写 1 条，实测是 **2 条**——`youtube:PlatoStone` 在 `state.json` 里其实**有**游标条目（22 条 `seen_urls`），跟本节原表述"后者在 state.json 里没有游标条目"不符。真实迁移跑出来是 `channels_updated=8`（8 条渠道全部回填 `key`，因为这是从 schema v1 首次升级）、`cursors_renamed=2`（`x:TingHu888`→`x:tinghu888`、`youtube:PlatoStone`→`youtube:platostone`）。迁移逻辑本身不受影响——它对所有需要归一的键一视同仁，不是只处理"预计的那 1 条"——只是这张表当初的实测数字要更正。两条游标的值都逐字节保留，验证见 `docs/commute/2026-09-16-roster-normalized-key-handoff.md` 的自测记录。

**顺带发现（本文范围外）**：`state.json` 里有一条 `x:fanli1688`，`registry.json` 里没有对应渠道——孤儿游标，渠道删了游标没删。不在本次范围，但 `remove_channel` 可能有漏。结论见 §7。

### 3.3 迁移

**新增一个独立子命令 `roster migrate-schema`**，不复用现有的 `migrate`——后者的用途是"从旧 `watchlist.json` 导入"，跟 schema 升版是两件事，混进一个子命令会让"我该跑哪个"变成需要读代码才能回答的问题。

三件事，必须在同一次操作里完成：

1. 给 `registry.json` 每条渠道回填 `key`，`schema_version` → 2。
2. 把 `state.json` 的渠道键重写为归一形态（**重命名，保留 cursor 值**）。
3. 幂等：重复跑安全。

**两个文件必须一起迁**。只迁一个，名册按 `key` 查而游标按 `handle` 存，就是新的不一致源头——比迁移前更糟。

---

## 4. scholia 的改动

### 4.1 join 改成精确比较

`creator-source.js` 的 `resolveRegistryMatch` 现在的做法是：把 registry 里每个渠道的 `handle` 归一一遍，再跟索引的 `key` 比。改成直接比 `registry` 的 `key` 与 `creators.json` 的 `key`——**两边都是已归一的值，纯字符串相等**。

它现有的 `channel_id` 回退分支（渠道是用 `/channel/UC.../` 这类 URL 加进来的、`handle` 里存的不是 `@handle`）保留，那条路径本来就不走归一。

### 4.2 归一函数删不掉，这是风险降级不是消除

`/api/creator/:key` 的路由入参可能被手输成任意大小写，scholia 仍需清洗一次。

**但它退出了 join 路径**，所以两边规则若不一致，最坏后果从"`watched` 静默算错"变成"手输的怪大小写 URL 404"。前者无症状，后者你当场看得见。

**这是本方案的真实边界，不粉饰成"只剩一份实现"。**

---

## 5. 明确接受的代价

### 5.1 反规范化：`key` 可能与 `handle` 漂移

`key` 是 `handle` 的纯函数，却和它存在同一个文件里。有人手改 `registry.json` 的 `handle` 而不改 `key`，join 就用了个陈旧的 key，**而且没有症状**。

缓解是"只有 roster 写它、每次写都重算"。

**这不违反主线**——`key` 是事实的纯函数，不是判断（对照 `2026-09-15` §0 那条"判断不落盘在事实旁边"）。但它确实是反规范化，漂移风险真实存在。可选的加固：`registry list` 时校验 `key == normalize(handle)`，不一致就报警。本次不做，记在这里。

### 5.2 动的是三个 skill 共用的数据契约

`registry.json` 与 `state.json` 是 `manage-creators`、`sync-xtimeline`、`sync-ytchannel` 共同依赖的文件。本次改动规模不大（roster 是主体，scholia 是小改），但**影响面比行数大**。

### 5.3 `website` 平台的 handle 未必该归一

现有 `website:simonwillison-net`、`website:claude-com` 的 handle 是从域名推出来的 slug，本来就是小写，归一对它们是恒等变换。但"网站的 handle 大小写不敏感"这个假设没有依据——它不像 YouTube handle 那样有平台文档背书。本次按统一规则处理（恒等，无风险），但若日后 `website` 的 handle 生成规则改变，这里要重新评估。

---

## 6. 验收标准

1. 同一个 YouTube 频道用不同大小写的 URL `add` 两次，第二次报"已在名册中"，`registry.json` 里仍是 1 个人 1 条渠道。
2. `registry.json` 每条渠道都有 `key`，且 `key == normalize(handle)`；`schema_version == 2`。
3. 迁移后 `state.json` 里 `x:TingHu888` 变成 `x:tinghu888`，**且 cursor 的 value 与迁移前逐字节相同**。
4. 迁移幂等：连跑两次，两个文件的内容不变。
5. 迁移后跑一次 `sync-ytchannel run`，**没有任何频道刷新基线**（即没有频道被当成新渠道）。
6. scholia 的 `watched` 在迁移前后对同一批 creator 给出相同结果（名册上 4 人为真、其余为假）。
7. `roster registry channels` 的输出含 `key`。
8. `merge` / `rename` 之后，被改动渠道的 `key` 仍等于 `normalize(handle)`。
9. **`roster state get youtube:TingHu888` 与 `roster state get youtube:tinghu888` 返回同一条游标**（§3.0 的归一入口生效）。这一条守的是"`sync-*` 零代码改动"这个承诺。

---

## 7. 未验证项

| 项 | 所在 | 风险 |
|---|---|---|
| `state.json` 里的孤儿游标 `x:fanli1688` 是怎么来的——`remove_channel` 是否有漏 | §3.2 | **结论（2026-09-16）**：`registry.py` 的 `remove_channel` 本身只改 `registry.json`，从不碰 `state.json`——真正调用 `state.drop_channel` 的是 `__main__.py` 的 `_cmd_registry_remove`（CLI 层，删渠道和删游标在同一个命令里一起做）。这条孤儿游标若真是被 `remove` 产生的，说明当时走的不是这条 CLI 路径（比如手工编辑过 `registry.json`，或用的是本次改动之前更早版本的代码）。本次不修，迁移会把它原样带进新 schema——已验证：迁移后 `x:fanli1688` 仍在 `state.json` 里，未被处理。 |
| ~~`sync-*` 是否直接读 `state.json`~~ **已实测（2026-09-16）**：全部经 roster CLI，无一例外。但它们传的是原始 handle —— 由此推出 §3.0 | §3.0 | 已消解，且转化成了一条硬要求 |
| `website` 平台 handle 的大小写敏感性 | §5.3 | 当前恒等变换，无实际风险 |
| `roster` 的 `profile` 层是否按 handle 索引 | §3 | **结论（2026-09-16）**：`tools/roster/roster/profiles.py` 全部函数（`profile_path`/`read`/`_write`/`append_observation`/`set_summary`/`archive`/`merge`）都按 `creator_id` 索引，完全不读 `handle` 或 `key`。本次改动对画像层零影响，已确认不是"预期无影响"，而是代码里查得到、确认无影响。 |

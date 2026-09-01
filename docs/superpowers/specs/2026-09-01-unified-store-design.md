# 统一存储契约设计

## 元信息

- **设计日期**：2026-09-01
- **状态**：待实现
- **涉及组件**：改造 `clip-url`、`learn-video`、`sync-xtimeline`、`sync-ytchannel`；新增迁移脚本。`roster` 保留名册与游标职责，交出产物目录职责。`vdl`（Video-Learner 仓库）零改动。
- **代码基线**：`staging`
- **本文范围**：只定"长期产物落在哪、目录怎么排、根怎么解析、历史怎么迁"。不改任何 skill 的抓取契约、翻译流程、去重算法、游标语义，不改 skill 数量与边界。`learn-paper`、`fetch-paper`、`pdf-math-translate`、`learn-skill`、`survey-skillrepo` 本次不动。

---

## 0. 主线

> **一个 skill 存东西，只需要决定"我是什么类型、什么形态"，不需要决定"存哪儿"。**

这句可证伪：只要能指出某个入范围 skill 仍然自持一份存储根配置、或者两个同类型产物落在两个不同的根下，主线即被推翻。

本文所有决定都是这条线的直接推论。目录布局、`meta.json` 字段、`store_config.py` 的函数签名，都只服务于"把'存哪儿'从 skill 里拿走"这一件事。

---

## 1. 现状问题

仓库里六个会长期存东西的 skill，有五个互不相干的存储根和五份互不相干的配置：

| Skill | 配置 | 根目录 | 产物 |
|---|---|---|---|
| clip-url | `~/.hskill/url-extract/config.json` → `VAULT_PATH` | Obsidian vault | `<hash8>/{meta.json, Origin/, Translation/}` |
| learn-video | `~/.config/vdl/settings.conf` → `WORK_ROOT`（vdl 自持） | `~/vdl-work/work/<task_id>/` | `transcript/`、`writing/`、`media/` |
| learn-paper | `~/.hskill/read-paper/config.json` | `~/Documents/papers` | 三遍笔记 |
| sync-xtimeline | roster 的 `DATA_DIR` | `DATA_DIR/tweets/` | `digest/*.md` + `creators/<handle>.json` |
| sync-ytchannel | 同上 | `DATA_DIR/youtube/` | 同上 |
| learn-skill / survey-skillrepo | `~/.hskill/config.json` → `skillDir` | `~/Documents/skill-library` | 分析报告 |

三个具体后果：

1. **没有全量视图。** 想知道"我一共存了多少东西"，得知道这五个根分别在哪，且每个根的布局都不一样。
2. **语义错位。** `sync-*` 的产物目录挂在 `roster` 名下。`roster` 是"我关注哪些人"的名册，兼任存储根持有者纯属历史巧合——想单独换掉名册就换不动了。
3. **clip-url 的产物寄居在 Obsidian vault 里。** vault 同时装着用户手写的笔记，skill 产物与人写内容混在同一个目录树下。

---

## 2. 资源模型

用户确认的模型是**类型 × 形态**二维矩阵：

|  | 实体（有正文） | 清单（只有指针） |
|---|---|---|
| **文章** | clip-url | — |
| **视频** | learn-video | sync-ytchannel |
| **推文** | —（见下） | sync-xtimeline |

**实体**是抓下来带正文/转写/笔记的东西，一个实体对应一个目录。**清单**是"谁发了什么"的聚合，只有标题、时间、URL，没有正文。同一个 YouTube 视频，走 sync-ytchannel 只留一行；走 learn-video 才落成实体。

"推文 × 实体"格为空：clip-url 的产物一律算文章实体，不按来源分流。x.com 的 URL 抓下来也进 `articles/`。这样 clip-url 的去重索引保持单一，不需要"先判类型再决定扫哪个目录"。

---

## 3. 存储契约

### 3.1 目录布局

```
<ROOT>/                              # 默认 ~/Documents/knowledge
  articles/<hash8>/                  # clip-url
    meta.json
    Origin/<标题>.md
    Translation/<标题>.md
  videos/<task_id>/                  # learn-video
    meta.json
    transcript/original.md
    writing/article.md
    writing/summary.md
  feeds/
    tweets/                          # sync-xtimeline
      digest/digest-<TS>.md
      creators/<handle>.json
    youtube/                         # sync-ytchannel
      digest/digest-<TS>.md
      creators/<handle>.json
```

三条规则，仅此三条：

1. **第一层是类型。** 实体类型各占一个顶层目录（`articles/`、`videos/`）。清单形态全部收进 `feeds/`，渠道名在下一层。这样"实体 vs 清单"这个形态维度在路径第一段就能读出来。
2. **一个实体一个目录，目录名是该类型的天然主键。** 文章用 URL 的 md5 前 8 位（`clip-url` 现行规则，不变），视频用 vdl 的 `task_id`。不引入新的 ID 体系。
3. **每个实体目录根上一份 `meta.json`；目录内部结构各 skill 自治。** 统一只做到这一层——`Origin/` + `Translation/` 与 `transcript/` + `writing/` 的差异保留，不强行归一。

### 3.2 meta.json

只规定三个必填字段：

```json
{
  "source_url": "https://...",
  "title": "...",
  "fetched_at": "2026-09-01"
}
```

其余字段各 skill 自由添加。`clip-url` 现在写的是 `{source_url, title, category, fetched_at, issues}`，已经是这三个的超集，字段层面零改动。

定这三个字段的唯一目的：`find <ROOT> -name meta.json` 就是全量实体清单。这也是为什么本设计不需要额外的索引文件——目录结构本身就是索引。

清单形态没有 `meta.json`。它本来就是聚合产物，`creators/<handle>.json` 自己就是索引。

---

## 4. 根的解析

### 4.1 配置

`~/.hskill/config.json` 新增 `knowledgeRoot` 字段，与已有的 `skillDir` 平级：

```json
{
  "skillDir": "/Users/xxx/Documents/skill-library",
  "knowledgeRoot": "/Users/xxx/Documents/knowledge"
}
```

存绝对路径（与 `skillDir` 一致）。写入时展开 `~`。

### 4.2 store_config.py

四个 skill 各带一份相同的 `scripts/store_config.py`，约 30 行。这是本仓库的既定模式——`browser_fetch_locate.py` 现在就在 `clip-url`、`sync-xtimeline`、`sync-ytchannel` 三处各存一份副本。

接口：

| 函数 | 返回 | 说明 |
|---|---|---|
| `get_root()` | `Path` | 读 `knowledgeRoot`。config 不存在或缺字段时抛异常，异常信息里带初始化引导语 |
| `articles_dir()` | `Path` | `<ROOT>/articles` |
| `videos_dir()` | `Path` | `<ROOT>/videos` |
| `feeds_dir(channel)` | `Path` | `<ROOT>/feeds/<channel>` |
| `main()` | — | `check` 子命令，打印 `OK: <root>` 或 `MISSING: <原因>`（exit 1），供 SKILL.md 的初始化步骤调用 |

支持 `HSKILL_CONFIG` 环境变量覆盖 config 路径，供测试注入临时根。

不做目录创建——各 skill 在真正写文件时自己 `mkdir -p`，保持"读路径"与"建目录"分离。

### 4.3 初始化

任一入范围 skill 首次运行时跑 `python3 scripts/store_config.py check`。若输出 `MISSING`，问用户：

> 抓取产物统一存到哪个目录？（直接回车使用默认：`~/Documents/knowledge`）

拿到答案后展开为绝对路径写回 `~/.hskill/config.json`（文件不存在则新建，存在则只增改 `knowledgeRoot` 字段，不覆盖 `skillDir`）。

**为什么不选方案 A（新建 store tool）：** `roster` 和 `browser-fetch` 配得上 tool 形态，是因为它们各自有名册增删改查、游标推进、URL 解析、浏览器会话管理这些真实逻辑。本契约的全部逻辑是"读一个字符串再拼一层固定的子目录名"，没有分支。为一个常量立一个必装依赖，会把 `clip-url` 和 `learn-video` 的安装门槛抬上去，换不回等价的东西。

**为什么不选方案 C（roster 的 DATA_DIR 升格）：** 那是在把第 1 节的问题 2 固化下来，而不是修掉它。

---

## 5. 各 skill 改动

### 5.1 clip-url

`scripts/vault_config.py` 里 `get_vault_path()` 改为委托 `store_config.articles_dir()`。`VAULT_PATH` 配置项退休（`~/.hskill/url-extract/config.json` 保留，因为 `fixed_tags.txt` 还住在同一目录；只是不再读 `VAULT_PATH`）。

`dedup_check.py` / `article_meta.py` / `write_meta_and_separate.py` 全部经由 `vault_config` 拿路径，一行不用改。`get_article_paths()` 的返回结构不变。

SKILL.md 的「初始化」小节把 vault 路径引导改成 `knowledgeRoot` 引导；「边界」小节改写存储布局描述。

### 5.2 learn-video

在拿到 vdl 终态 JSON 的 `transcript`/`article`/`summary` 三个路径之后，新增一步"归档"：

1. `mkdir -p <ROOT>/videos/<task_id>/{transcript,writing}`
2. 复制三个文件到对应位置（`transcript/original.md`、`writing/article.md`、`writing/summary.md`）
3. 写 `meta.json`：`source_url` 取用户给的视频 URL，`title` 取视频标题，`fetched_at` 取当天日期
4. 向用户报告的产物路径改成 `<ROOT>/videos/<task_id>/` 下的路径

**vdl 侧零改动。** `WORK_ROOT` 保持默认 `~/vdl-work`，其 `work/` 退化成流水线暂存区。不把 `WORK_ROOT` 直接指向新根，原因有二：`work/<task_id>/` 下还有 `media/`（下载的音视频，体积大）和 `work/database.sqlite`、`work/index.jsonl`，这些是 vdl 的运行时状态，不是知识产物；且 vdl 的布局多一层 `work/`，指过去会得到 `<ROOT>/videos/work/<task_id>/`。

复制而非移动——`rerun` 需要 vdl 的工作目录还在。同一 `task_id` 重复归档时覆盖，幂等。

### 5.3 sync-xtimeline / sync-ytchannel

两者的 `scripts/config.py` 现在是 `return roster_client.data_dir()`，改为 `return store_config.feeds_dir('tweets')` / `store_config.feeds_dir('youtube')`。

注意语义变化：改之前 `get_data_dir()` 返回的是**共用根**，各脚本自己再拼 `tweets/` 或 `youtube/`；改之后返回的直接是**本渠道目录**，中间那一段要去掉。全部四个调用点：

| 文件 | 行 | 现在 | 改成 |
|---|---|---|---|
| `sync-xtimeline/scripts/archive_tweets.py` | 25 | `get_data_dir() / "tweets" / "creators" / f"{handle}.json"` | `get_data_dir() / "creators" / f"{handle}.json"` |
| `sync-xtimeline/scripts/render_digest.py` | 85 | `get_data_dir() / "tweets" / "digest"` | `get_data_dir() / "digest"` |
| `sync-ytchannel/scripts/archive_videos.py` | 25 | `get_data_dir() / "youtube" / "creators" / f"{handle}.json"` | `get_data_dir() / "creators" / f"{handle}.json"` |
| `sync-ytchannel/scripts/digest.py` | 67 | `get_data_dir() / "youtube" / "digest"` | `get_data_dir() / "digest"` |

`roster_client.py` 保留——它还承担 `channels()` / `get_cursor()` / `set_cursor()` / `set_error()`，被 `fetch_new_tweets.py`、`fetch_new_videos.py`、`archive_*.py` 广泛调用。只有其中的 `data_dir()` 变成无调用方，随之删除；对应地 `roster` tool 的 `data-dir` 子命令也不再有 skill 侧消费者（tool 自身保留该子命令，名册仍需要它）。

`roster` 保持不变：继续持有 `registry.json`、`state.json`（游标）和 `DATA_DIR` 配置项。`DATA_DIR` 在本次之后只剩名册自身用，不再有 skill 往里写产物。

---

## 6. 迁移

`scripts/migrate-store.sh`，两段式：默认 dry-run 打印计划，`--apply` 才执行。幂等，可重跑。

**搬三处：**

| 来源 | 目标 |
|---|---|
| `<VAULT_PATH>/<hash8>/` | `<ROOT>/articles/<hash8>/` |
| `<DATA_DIR>/tweets/` | `<ROOT>/feeds/tweets/` |
| `<DATA_DIR>/youtube/` | `<ROOT>/feeds/youtube/` |

`roster` 的 `registry.json` 和 `state.json` 留原地。`~/vdl-work` 留原地（历史视频不回填——vdl 的 work 目录是暂存区，本来就不保证长期留存）。

**关键风险与约束：** `VAULT_PATH` 指向的是用户的 Obsidian vault 根，里面混着用户手写的笔记。脚本**禁止整目录 mv**，只搬同时满足两个条件的子目录：目录名匹配 `^[0-9a-f]{8}$`，且目录内含 `meta.json`。其余一律不碰，并在 dry-run 输出里列出"跳过的目录"让用户核对。

**验证两条：**

1. 迁移前后 `meta.json` 计数一致（`find <VAULT> -maxdepth 2 -name meta.json | wc -l` 对比 `find <ROOT>/articles -maxdepth 2 -name meta.json | wc -l`）。
2. 拿一个已抓过的 URL 跑一次 `dedup_check.py`，应输出 `ALREADY_FETCHED`。

`sync-*` 的游标存在 `roster` 的 `state.json` 里、不随迁移变动，所以搬完归档后下一轮增量抓取的行为不受影响——这是"游标不搬"能成立的前提。

---

## 7. 测试

| 对象 | 用例 |
|---|---|
| `store_config` | config 缺失 → 抛异常且信息含引导语；缺 `knowledgeRoot` 字段 → 同上；`~` 展开正确；四个路径拼接正确；`HSKILL_CONFIG` 覆盖生效 |
| `clip-url` | 临时根下 `dedup_check` 对已存在的 `articles/<hash8>/meta.json` 命中；`get_article_paths` 返回 `articles/` 下的路径 |
| `migrate-store.sh` | 只搬 hash8 目录；旁边的手写笔记目录原封不动且出现在跳过列表；`--apply` 重跑幂等；dry-run 不产生副作用 |
| `sync-*` | 现有测试的 `DATA_DIR` fixture 换成 store fixture；断言 digest 和 creators 落在 `feeds/<channel>/` 下 |
| `learn-video` | 归档步骤把三个文件复制到 `videos/<task_id>/` 并写出合法 `meta.json`；同 task_id 重跑幂等 |

---

## 8. 明确不做

- 不新增索引文件（`index.jsonl` 之类）。`find -name meta.json` 够用。
- 不统一实体目录内部结构。`Origin/` 与 `transcript/` 的差异保留。
- 不改 skill 数量与边界。合并 skill 是独立的后续议题。
- 不动 `learn-paper` / `fetch-paper` / `pdf-math-translate` / `learn-skill` / `survey-skillrepo`。
- 不改 `vdl`（Video-Learner 是另一个仓库）。
- 不做 clip-url 的来源分流。
- 不为 Obsidian 保留兼容层（软链、双写都不做）。想在 Obsidian 里看新根，由用户自己配置，不归 skill 管。

# 统一存储契约设计

## 元信息

- **设计日期**：2026-09-01
- **状态**：实施中（2026-09-02 按用户决定修订：vdl 重指到统一根、无 title 的视频任务不索引、孤儿目录进 `_orphans/`、迁移全程只复制不删除、新增六阶段迁移策略见 §6.0）
- **涉及组件**：改造 `clip-url`、`learn-video`、`sync-xtimeline`、`sync-ytchannel`；新增迁移脚本。`roster` 保留名册与游标职责，交出产物目录职责。`vdl`（Video-Learner 仓库）**源码零改动，但其 `WORK_ROOT` 配置要重指到 `<ROOT>/videos`**（用它自带的 `vdl config set work-root`）。
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
  videos/                            # learn-video；= vdl 的 WORK_ROOT
    work/<task_id>/                  # work/ 这层是 vdl 的布局，不是我们的
      meta.json
      media/                         # vdl 下载的音视频
      transcript/original_{zh,en}.md
      writing/{article,summary}.md
    work/database.sqlite             # vdl 运行时状态
    work/index.jsonl
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
2. **一个实体一个目录，目录名是该类型的天然主键。** 文章用 URL 的 md5 前 8 位（`clip-url` 现行规则，不变），视频用 vdl 的 `task_id`。不引入新的 ID 体系。视频实体目录比文章深一层（`videos/work/<task_id>/`），因为 vdl 把 `work` 段写死在 `WORK_ROOT` 之下——§3.2 的索引承诺不关心深度，所以这一层不影响契约，只影响观感。
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

**vdl 的 `WORK_ROOT` 直接指向 `<ROOT>/videos`**，用 vdl 自带的 `vdl config set work-root <ROOT>/videos`（`cli/commands/config.js`，交互式确认后连带迁移旧任务，有测试覆盖）。vdl 源码零改动。

于是 vdl 的产物**一开始就写在最终位置**，归档不搬任何文件，只补一份 `meta.json` 把目录标成实体：

1. `video_dir = <ROOT>/videos/work/<task_id>`
2. 该目录不存在则报错退出——不 `mkdir`。`meta.json` 是索引的唯一凭据，凭空建一个指向空气的实体比没有更糟
3. 写 `meta.json`：`source_url` 取用户给的视频 URL，`title` 取视频标题，`fetched_at` 取当天日期
4. 向用户报告的产物路径改成 `<ROOT>/videos/work/<task_id>/`

**曾经考虑并否决的方案：** 让 `WORK_ROOT` 留在原处、由 learn-video 把三个文件复制进 `<ROOT>/videos/<task_id>/`。否决理由是那会产生两份物理副本，且"下游程序还写在老路径"违背了本设计"一条路径到底"的初衷。当时反对重指的理由是 `media/` 体积大不该进知识根——该理由不成立：那 9 GB 今天已经在用户的 Vault 里，重指只是换位置，不新增。

**代价，明确记下来：** `knowledgeRoot`（`~/.hskill/config.json`）与 `WORK_ROOT`（`~/.config/vdl/settings.conf`）分居两个文件，无机制保证同步。缓解是两道，都不是自动修复：SKILL.md 的初始化小节要求核对两者；`archive.py` 在任务目录缺失时报错并打印 `vdl config set work-root` 的修复命令。skill **不代改** vdl 的配置文件——那是另一个程序的配置。

`work` 这一段是 vdl 写死的（`core/paths.js:68`，`getDbPath` / `getIndexPath` / `getTaskDirs` / `getArticleDirs` 全建在其上，`config set work-root` 的迁移逻辑和 8 个测试文件也假设它存在）。为了少一层目录去改下游的路径契约，代价远大于收益，故接受 `<ROOT>/videos/work/<task_id>/` 这个形状。

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

### 6.0 总策略（六个阶段，按序执行）

**贯穿始终的铁律：只复制，不删除。** 迁移期间原始数据一个字节都不动，新旧两套并存。是否清除原件是**最后一步单独的人工判断**，不由任何脚本代做。这条铁律的作用是让整个迁移可回退——任一阶段发现不对，把配置改回去就行，不需要恢复备份。

| 阶段 | 做什么 | 完成判据 |
|---|---|---|
| 1. 装 | 安装最新 skill（`hskill`）与全部下游配套程序（含 vdl `npm link`） | `which vdl`；`hskill status` 无 outdated |
| 2. 配 | 写 `~/.hskill/config.json` 的 `knowledgeRoot`；`vdl config set work-root <ROOT>/videos`（该命令同时完成视频数据的复制） | `store_config.py check` 输出 `OK:`；`vdl config get` 的 work root 等于 `<ROOT>/videos` |
| 3. 搬 | `migrate-store.sh --apply` 复制其余五处 | 退出码 0 |
| 4. 校 | 校验迁移数据完整性 | `migrate-store.sh --verify` 退出码 0 |
| 5. 跑 | 用最新 skill 和脚本把**每条路径各跑一遍真实任务**，确认新产物落在新根 | 见 6.3 |
| 6. 清 | 询问用户是否完成、是否清除原始数据 | 人工决定；脚本不代做 |

**配必须早于搬，这是工具的硬约束，不是偏好。** `knowledgeRoot` 既是"目标在哪"又是"开关"——没有第二个开关可拨，`migrate-store.sh` 也要读它才知道往哪复制。`vdl config set work-root` 同理：一条命令既改配置又搬数据。

代价是阶段 2 到阶段 4 之间存在一个窗口：配置已指向新根，但数据还没复制完。**期间不要运行任何入范围的 skill**——此时 `dedup_check.py` 在新根上查不到历史文章，会把已抓过的 URL 判成新的。因为全程只复制、原件都在，这个窗口最坏的后果是重复抓一篇，不会丢东西。整个窗口是一次性的、分钟级的。

阶段 5 不能省。阶段 4 只证明**旧数据搬对了**，不证明**新数据会写对**——后者只有真跑一遍才知道。

### 6.1 阶段 2：视频交给 vdl（配 + 搬一步完成）

```bash
vdl config set work-root ~/Documents/knowledge/videos
```

交互式确认后**复制**整个 work 目录（vdl 自己也是复制不删旧，与本策略一致），双边都有数据时按 task id + url 合并 SQLite。`migrate-store.sh` 不碰这块，只在之后补 `meta.json`。

`meta.json` 的 `source_url` / `title` 从同目录 `database.sqlite` 的 `tasks` 表取，`title` 为空时回退到 `writing/article.md` 的首个 H1，`fetched_at` 取 `tasks.ts`。

**拿不到 title 的任务不写 `meta.json`，因此不进索引。** 用户 2026-09-02 明确决定抛弃这批。它们的目录和转录稿留在磁盘上——删除不可逆，属于阶段 6，不由迁移脚本代做。现状：229 个目录里 54 个有 title（53 个来自 sqlite、1 个来自 H1），恰好等于有 `writing/article.md` 的那 54 个；其余 174 个只有转录稿、sqlite 的 `title` 为 null、`media/` 为空、无 `.info.json`，本地无从恢复标题。

### 6.2 阶段 3：其余五处交给 `migrate-store.sh`

脚本三种模式：默认 dry-run 打印计划、`--apply` 执行复制、`--verify` 核对（阶段 4 用）。幂等——目标已存在就跳过，可重跑。

| 来源 | 目标 | 说明 |
|---|---|---|
| `<VAULT_PATH>/<hash8>/` | `<ROOT>/articles/<hash8>/` | 仅限含 `meta.json` 的目录 |
| `<DATA_DIR>/tweets/` | `<ROOT>/feeds/tweets/` | 整段复制 |
| `<DATA_DIR>/youtube/` | `<ROOT>/feeds/youtube/` | 整段复制 |
| `~/.hskill/sync-xtimeline/{digests,tweets}/` | `<ROOT>/feeds/tweets/{digest,creators}/` | roster 化之前的旧布局，逐文件并入 |
| `<VAULT_PATH>/{Origin,Image}/` | `<ROOT>/articles/_orphans/` | 见下 |

`roster` 的 `registry.json`、`state.json` 留原地。`<VAULT_PATH>/url-index.db` 留原地——0 行，全仓库只有 `skills/archived/extract-url/` 的测试引用它，是死文件。

**孤儿的处理。** `<VAULT_PATH>` 顶层的 `Origin/`（9 篇原文）、根目录下的 5 篇译文、以及 `Image/`（58 张图）是更早版本 clip-url 的扁平布局遗留：译文放 vault 根、原文放 `Origin/`、图片放 `Image/<前缀>_img_N.ext`，引用写成 vault 根相对的 `Image/...`。`migrate-store.sh` 原样复制进 `<ROOT>/articles/_orphans/{Origin,Translation,Image}/`，**不代造 `meta.json`**。译文的识别靠 frontmatter 里有没有 `source_url`——用户手写的笔记没有这一行，天然被排除，不需要维护文件名白名单。

**孤儿重建（`scripts/rebuild-orphan-articles.py`，单独一步）。** 这批文件的 frontmatter 其实带着 `source_url` / `origin_title` / `fetch_date`，所以 `meta.json` 可以**推导**而非编造——这是本脚本获准往索引里写东西的全部理由。只在无歧义时重建：`hash8 = md5(source_url)[:8]` 尚无对应实体，**且**恰好只有一个 `Origin/*.md` 映射到它。多个文件共用同一个 `source_url` 意味着同一篇被抓了多次，选哪个是人工判断，一律跳过并报告。重建时把 `Image/<前缀>_img_N` 复制成 `<hash8>/Image/img_N` 并把引用改写为 `../Image/img_N`，以匹配嵌套布局。

本机实跑结果：9 篇里 2 篇已是正式实体、3 篇共用一个 `source_url`（Anthropic Economic Index，`e19bdeb4`，待人工三选一）、4 篇重建成功。

**关键风险与约束：** `VAULT_PATH` 指向的是用户的 Obsidian vault 根，里面混着用户手写的笔记。脚本**禁止整目录操作**，只复制同时满足两个条件的子目录：目录名匹配 `^[0-9a-f]{8}$`，且目录内含 `meta.json`。其余一律不碰（`Origin/`、`Image/` 是上面显式点名的例外），并在 dry-run 输出里列出"跳过的目录"让用户核对。

**实现注记：** 脚本必须兼容 macOS 自带的 bash 3.2，它在解析 `$var（中文）` 时会把全角字符吞进变量名，触发 `unbound variable`。凡是变量后面紧跟非 ASCII 字符的地方一律写成 `${var}`。

### 6.3 阶段 5：逐路径实跑

四条路径各跑一次真实任务，断言新产物落在新根：

| 路径 | 跑什么 | 断言 |
|---|---|---|
| clip-url | 抓一篇没抓过的文章 | 新目录出现在 `<ROOT>/articles/<hash8>/`，含 `meta.json` |
| learn-video | 处理一个短视频 | 产物在 `<ROOT>/videos/work/<task_id>/`，`archive.py` 写出 `meta.json` |
| sync-xtimeline | 跑一次增量同步 | digest 落在 `<ROOT>/feeds/tweets/digest/`，游标推进 |
| sync-ytchannel | 跑一次增量同步 | digest 落在 `<ROOT>/feeds/youtube/digest/` |

另外拿一个**迁移过来的**已抓 URL 跑 `dedup_check.py`，应输出 `ALREADY_FETCHED`——这条证明新根上的历史数据是活的，不只是躺在那里的文件。

### 6.4 阶段 6：清理

`--verify` 全绿且阶段 5 四条路径都跑通之后，才谈清理。候选清理对象及其体积：

| 对象 | 体积 | 备注 |
|---|---|---|
| `<VAULT_PATH>/<hash8>/` × 375 | 193 MB | 已有副本 |
| `Vault/VL/`（vdl 旧 work 根） | 9.1 GB | vdl 自己复制留下的 |
| `~/Projects/Video-Learner/work/` | 5.3 GB | 更早的遗留，28/32 与主根重复且内容一致，独有的 4 个无 writing |
| `~/.hskill/roster/{tweets,youtube}/` | 56 KB | 已有副本 |
| `~/.hskill/sync-xtimeline/{digests,tweets}/` | 56 KB | 已有副本 |

**由用户逐项决定，脚本不提供 `--clean`。** 删除是唯一不可回退的操作，不值得为省几次手打命令而把它自动化。

---

## 7. 测试

| 对象 | 用例 |
|---|---|
| `store_config` | config 缺失 → 抛异常且信息含引导语；缺 `knowledgeRoot` 字段 → 同上；`~` 展开正确；四个路径拼接正确；`HSKILL_CONFIG` 覆盖生效 |
| `clip-url` | 临时根下 `dedup_check` 对已存在的 `articles/<hash8>/meta.json` 命中；`get_article_paths` 返回 `articles/` 下的路径 |
| `migrate-store.sh` | 只复制 hash8 目录且**源目录仍在原处**；旁边的手写笔记原封不动且出现在跳过列表；`Origin/`、`Image/` 进 `_orphans/` 且不生成 `meta.json`；旧 `sync-xtimeline` 布局并入 `feeds/tweets/`；视频回填只覆盖有 title 的任务；`--apply` 重跑幂等；dry-run 不产生副作用；`--verify` 在迁移前退出非 0、迁移后退出 0 |
| `sync-*` | 现有测试的 `DATA_DIR` fixture 换成 store fixture；断言 digest 和 creators 落在 `feeds/<channel>/` 下 |
| `learn-video` | 归档步骤往已存在的 `videos/work/<task_id>/` 写出合法 `meta.json` 且不动 vdl 产物；同 task_id 重跑幂等；任务目录缺失时报错退出、不建目录、错误信息含 `vdl config set work-root` |

---

## 8. 明确不做

- 不新增索引文件（`index.jsonl` 之类）。`find -name meta.json` 够用。
- 不统一实体目录内部结构。`Origin/` 与 `transcript/` 的差异保留。
- 不改 skill 数量与边界。合并 skill 是独立的后续议题。
- 不动 `learn-paper` / `fetch-paper` / `pdf-math-translate` / `learn-skill` / `survey-skillrepo`。
- 不改 `vdl` 的源码（Video-Learner 是另一个仓库）。只改它的 `WORK_ROOT` 配置值，且用它自己提供的 `config set work-root` 命令改，不手动编辑它的配置文件。
- 不做 clip-url 的来源分流。
- 不为 Obsidian 保留兼容层（软链、双写都不做）。想在 Obsidian 里看新根，由用户自己配置，不归 skill 管。

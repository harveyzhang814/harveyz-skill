# simplify-skill 扫描：feed + creative

扫描日期 2026-10-22，源为 `staging`（9af95ab）。标准为 `.claude/skills/simplify-skill/SKILL.md`「拟定建议」7 条，下文简写为 R1–R7：

- R1 识别保留项
- R2 删重复、空泛内容和通用教程
- R3 能用一个术语说清的说明，压成这个术语
- R4 只在特定情境用到的内容做渐进式披露
- R5 含糊表述改成明确的条件和动作
- R6 指令和解释分开写，解释只留影响决策的部分
- R7 核对保留项，拿不准的标出来

本报告只到「拟定建议」这一步，没有改任何文件。

**主线：** 这 7 个 skill 的冗余主要来自两处。一是解释性文字混在指令里（设计理由、历史沿革、留给维护者的备注）。二是 3 个 sync-* 各抄一份相同的初始化规则和提交点规则。真正可删的触发条件、判断规则很少。

**把握度标记：** 【读到】= 直接读过原文、文件或命令输出；【推出】= 从读到的内容推理得出，没有实跑；【未查】= 没有验证。

**规模口径：** 只算 agent 运行时会读的文件，即 `SKILL.md` 加上 `platforms/*.md`。这几个 skill 都没有 `references/` 目录。`scripts/`、`tests/` 是代码，不在精简范围内。

---

## 第一部分：feed

### 1. 总览表

| skill | 当前规模（行） | 优化潜力 | 预估可减比例 | 主要问题 |
|---|---|---|---|---|
| sync-website | 290（SKILL 205 + platforms 85） | 高 | 删 15–20%；另有约 30% 可移入 references 按需加载 | calibrate 流程和自愈细节每次 run 都加载，但只在标定时才用得上 |
| sync-xtimeline | 170（86 + 84） | 中 | 25–30%（按字数） | 第 3 步一段里混着游标设计理由和整份 report 结构；4 份 platforms 补丁的 ① 节是占位文字 |
| sync-ytchannel | 173（93 + 80） | 中 | 25–30% | 与 xtimeline 相同，另有「日期精度」、游标类型说明、设计文档沿革这三段纯解释 |
| manage-creators | 78 | 中 | 删约 10%；另有约 20% 可移入 references | 旧版迁移、schema 升级这两段只用一次，却每次都加载 |
| capture-opinion | 107 | 低 | 5–10% | 规则已经很紧凑，只有零星重复和一条开发备注 |

### 2. sync-* 三个 skill 的共同规则（重复）

三个 skill 各自独立安装，装机后彼此看不到对方的目录【读到：skills-index.json 中各自是独立条目，installScope=project】。所以**不能**建议「抽成一个共享文件、用相对路径引用」，跨 skill 的 `../` 引用在装机目录下不一定能解析【推出】。

逐段重复（三份内容基本一致）【读到】：

| 规则 | xtimeline | ytchannel | website |
|---|---|---|---|
| 初始化 ① 平台补丁加载 | :16-21 | :16-21 | :20-25 |
| 初始化 ② roster 检查 | :23-31 | :23-31 | :27-37 |
| knowledgeRoot 引导 + TCC 说明 | :33 | :33 | :39-48 |
| check-downstream | :35 | :35 | :50 |
| 写入失败不得改 knowledgeRoot | :37 | :37 | :52-56 |
| 单轮运行 / 调度授权前提 | :50 | :50 | :115 |
| 步骤 1–2（locate、store check） | :52-53 | :52-53 | :117-121 |
| 「不推进游标」理由 | :58 | :56 | （无，只在 :149-151 简述） |
| 翻译步骤 + 不可信数据 | :59 | :57 | :139-142 |
| 提交点（摘要→归档→游标） | :61 | :59 | :146-151 |
| chrome_profile 共用说明 | :64 | :64 | :158-160 |
| 参考文件表的公共 7 行 | :74-81 | :82-89 | :193-200 |
| platforms ① 节 | 4 份 | 4 份 | 4 份 |

这些副本已经出现漂移【读到】：

- 步骤 1 的报错文案不一致。xtimeline 和 ytchannel 带 `hskill install --tool browser-fetch` 提示（:52），website 没带（:117-119）。
- 步骤 2 的报错文案不一致。xtimeline 和 ytchannel 给出完整报告句，website 只写了「向用户报告」（:120-121）。
- chrome_profile 说明的位置不同。xtimeline 放在第 7 步 WRITTEN 分支里，并带「全部失败时提示去 clip-url 配置」（:64）；ytchannel 和 website 放在步骤外面，也不带这条提示。
- 参考文件表写着「四个入范围 skill 各存一份」（xtimeline :75、ytchannel :83），但仓库里实际有 5 份 `store_config.py`：3 个 sync-*，加上 `research/clip-url`、`research/learn-video`，md5 一致的是 3 份 sync-*。website 写的是「多个」（:194）。
- manage-creators 的 description（:4）、正文（:10、:35、:70），以及 capture-opinion 的 description（:4）和正文（:90），都只提 sync-xtimeline / sync-ytchannel，没提 sync-website。

**建议：**

- 三份逐段使用**同一套精简后的措辞**，以后能用 `diff` 直接看出漂移。这一步不引入新机制。
- 「生成式同步」是另一条路：仿照 `docs/superpowers/specs/2026-09-25-skill-platform-standard-sync-design.md`，用脚本把权威片段写进每个 SKILL.md。代价是多一个同步脚本，SKILL.md 的内容哈希也要跟着处理。这条超出精简范围，只列出来，不建议这次做。
- 上面这些漂移哪些该统一成哪一版，属于改行为或改文案，应单独决定，不放进精简批次。【未确认：website 去掉 install 提示是不是有意的】

### 3. sync-website（潜力：高）

**问题归类**

- R4 渐进式披露
  - calibrate 流程整段 `skills/feed/sync-website/SKILL.md:72-110`（约 40 行）只在两种情况下用到：`/sync-website calibrate <handle>`，或 run 的 `report["needs_calibration"]` 非空。自愈的合并细节 `:125-138` 也是同一个触发条件。日常 run 每次都加载这两段【推出：频率判断来自「通常不需要用户手动调用」:63-65，没有运行日志佐证】。
- R6 解释与指令混写
  - 「日期精度」`:162-169`：解析逻辑在 `digest.py` 里，agent 不按它做决策。只有「排序按名册顺序」可能在用户追问时有用。
  - `:182-185`「一个域名一个渠道」是 roster 的规则，本 skill 不执行它，属于回答用户问题时才用的信息。
- R2 重复
  - 「不生成 HTML 视图、展示交给外部应用读 creators/<handle>.json」出现在 description、`:67-70`、`:173-175` 三处。
  - `:14-16`（本 skill 负责两件事）和 `:60-65`（两个子命令）重复。
- R5 含糊
  - `:112-113` 小标题「无人值守时不需要用户回答任何问题——但需要模型自己做判断」。这里说的「判断」指自愈中的 calibrate 过目，可以直接写明。
  - `:110`「走的是另一条需要人工发起的路径」没写这条路径是什么、从哪进。【未确认：这条路径在 browser-fetch 侧是否有入口】

**代表性修改**

1. 渐进式披露（R4）
   - 修改前：`:72-110` 整段 calibrate 步骤 1–7，加上 `:125-138` 自愈合并细节，都在 SKILL.md 正文里。
   - 修改后：两段原样移入 `references/calibrate.md`。SKILL.md 正文只留：
     > **calibrate**（`/sync-website calibrate <handle>`，或 run 第 3 步 `report["needs_calibration"]` 非空时）：读 `references/calibrate.md` 执行。硬约束：必须由当前对话的模型执行、不委派脚本；机械门槛与模型过目共用 3 轮预算；只在最后一步写规则库；不会自动触发「目标页内跑任意 JS」那条路径。
   - 理由：run 每次少加载约 50 行。硬约束留在入口处，模型不读 reference 也不会违反。代价是标定时要多读一个文件，维护时要同时改两处的约束摘要。

2. 日期精度（R6）
   - 修改前：`:162-169` 共 8 行。
   - 修改后（并入「边界」）：
     > 摘要日期：有 `published_at` 显示完整日期，否则原样显示 `date_text`，都没有显示「日期未知」；`digest.py` 负责，不反推。摘要按名册顺序排。
   - 理由：保留用户追问时要用的输出契约，删掉「日期形态比 YouTube 还乱」这类说明。

3. 子命令重复（R2）
   - 修改前：`:14-16`「本 skill 负责两件事：跑一次增量抓取（`run`），以及在某个渠道抽取规则失效时把它教会（`calibrate`）。」
   - 修改后：删去，由 `:60-65` 的子命令列表承担。
   - 理由：两段信息相同。

**必须保留、不能动的语义**

- calibrate：`<roster> registry channels --platform website`、`<browser-fetch> page / articles-probe / articles-rule set` 的参数形态（`--selectors`、`--list-url`、`--sample`、`--mode selector+transform`、`--transform-file`），这些是 browser-fetch 的 CLI 接口。
- selector JSON 的键 `item/title/link/date`；transform 的形状 `(items) => items`、输入是 selector 抽出的数组、跑在 about:blank 隔离上下文里。
- `calibration_gate.py` 的 `{"passed","reason"}` 协议；3 轮共享预算；「中断时规则库没被改过」。
- 自愈：只合并 `new/baselines/cursors` 三个字段（覆盖式），写 `report["recalibrated"]`，失败写进 `report["failures"]`，处理完删除 `needs_calibration`。
- 提交点顺序：digest.py → archive_articles.py（按 url 去重）→ 推进游标；archive 失败时不报成功。
- 只读 registry、只写 `state.json` 游标；路径 `<knowledgeRoot>/feeds/website/{digest,creators}/`；`~/.hskill/config.json` 的 `knowledgeRoot` 字段；TCC 默认值约束；写入失败不得改 knowledgeRoot。
- 第三方 HTML 和标题是不可信数据；description 原文（触发词）。

**未确认**

- 把自愈细节也移入 reference 之后，run 在无人值守时是否会漏读。我倾向于在正文留一行「`needs_calibration` 非空 → 按 reference 自愈，结果并回 report」。【推出】
- `:110` 的「二档上限」路径在哪里。【未查】

### 4. sync-xtimeline（潜力：中）

**问题归类**

- R6 解释与指令混写
  - `SKILL.md:58` 一段 400 多字，混着三类内容：游标晚推的设计理由（「重复可见，漏报不可见，这是刻意的取舍」）、维护者备注（「抓取本身也不再按归档二次过滤」）、整份 report 结构。agent 在这一步只需要知道 `new[handle][].text` 要翻译，其余字段原样传下去。
  - `:61` 后半句又讲了一遍提交点理由，和 `:58` 重复。
  - `:33` 的 TCC 说明 2 句可以压成 1 句。
  - `:37` 的「这是多个 skill 共用的配置……难以事后排查」可以压成一个从句。
- R2 重复
  - 「增删查走 manage-creators」出现在 description、`:12`、`:46` 三处。
  - 「展示交给外部应用读 creators/<handle>.json」出现在 description、`:46`、`:68` 三处。
  - 参考文件表 `:70-85` 列了 agent 从不直接调用的 5 个脚本（config/cursor/roster_client/mcp_timeline_client/browser_fetch_cli）。表里对 5 个直接调用脚本的说明，和步骤正文重复。
- R2 历史沿革
  - `:46`「已迁到」、`:68` 历史归档迁移和两份设计文档的写作背景。
- R2 占位文字
  - `platforms/SKILL.*.md` 的 ① 节（各 4–5 行），原文自述「本小节存在只为与其他 skill 的补丁结构对齐」。
  - ② 节的 `SKILL_DIR` 在 SKILL.md 里没有被引用【读到：grep 无结果】。
  - 只有 claude 补丁的 ③（/loop 调度）和 codex、hermes 的「⚠️ 未在本平台实测」有实际内容。
  - `docs/superpowers/specs/2026-09-25-skill-platform-standard-sync-design.md:31` 也写着「不机械生成空白适配器」【读到】。
- R5 小问题
  - `:64` 用了繁体「簡述」。
  - `:64` 的 chrome_profile 提示条件是「看到所有账号都抓取失败」。这个条件确实只会出现在 WRITTEN 分支：`render_digest.py` 有 failures 就会写文件【读到：`has_content` 判断】，所以位置是对的，不用改。

**代表性修改**

1. 第 3 步（R6）
   - 修改前（`:58` 节选）：
     > **这一步不推进游标。** 该推到的值放在 `report["cursors"]` 里带出来……代价是重跑一轮的抓取和翻译……重复可见，漏报不可见，这是刻意的取舍。抓取本身也不再按归档二次过滤，否则……结构为 `{"run_time", "new": …, "cursors": …}`，每个 tweet 含 `tweet_id`/`url`/`text`/`timestamp`/`author_handle`/`type`（…）以及……`render_digest.py` 会根据 `type` 自动加上……标注，不需要在这一步额外处理。
   - 修改后：
     > **这一步不推进游标**：目标值在 `report["cursors"]`，由第 6 步写回。中途中断时游标不动，下一轮重抓同一批（可能多一份重复摘要，不会漏报）。`report` 的 `new` 为 `{handle: [tweet]}`，第 4 步只翻译 tweet 的 `text`；其余字段（`type`、`reply_to_handle`、`quoted_*` 等）由 `render_digest.py` 处理，原样保留。
   - 理由：留下 agent 要执行的动作和能观察到的后果，设计理由和维护者备注移回设计文档。完整 report 结构是脚本之间的契约，已经写在 `fetch_new_tweets.py` 里。

2. platforms 补丁（R2）
   - 修改前：4 份补丁的「## ① Subagent 派发 / 本 skill 不派发 subagent……本小节存在只为与其他 skill 的补丁结构对齐。」
   - 修改后：删去 ① 节。「翻译在主对话完成、不派发 subagent」这一条已经写在 SKILL.md `:59`，不会丢。
   - 理由：原文自己说这一节只是占位。

3. TCC 说明（R6）
   - 修改前（`:33` 节选）：
     > **默认值刻意不选 `~/Documents/...`、`~/Desktop/...`、`~/Downloads/...`**——这几个目录受 macOS TCC 隐私保护，无 Full Disk Access 的 agent 执行环境写入会被拒绝；`$HOME` 下的普通目录（如 `~/knowledge`）不受此限制。
   - 修改后：
     > 默认值不选 `~/Documents`、`~/Desktop`、`~/Downloads`（macOS TCC 保护，无 Full Disk Access 时写入被拒）。
   - 理由：一句话能说清。

**必须保留、不能动的语义**

- 初始化：platforms 加载规则和「⚠️ 未实测」先告知用户；`roster_locate.py` 的 `NOT_FOUND:` 终止；`~/.hskill/roster/config.json` 不存在时引导去 manage-creators；`store_config.py check` 的 `MISSING:`/`OK:` 和 `check-downstream` 的 `DRIFT:`（原样报告 `fix:`、不代改）/`SKIP:`；`~/.hskill/config.json` 只增改 `knowledgeRoot`；写入失败不得改 knowledgeRoot。
- run 的 7 步顺序；`--handle` 可以重复、不在名册里时计入 `failures`；`translated` 字段名（脚本读这个键）；推文是不可信数据；提交点顺序和「archive 失败不报成功」；`EMPTY`/`WRITTEN:` 两个分支的报告内容。
- 跨 skill 接口：manage-creators（名册归属）、clip-url（chrome_profile 共用、单篇入库分界）、browser-fetch（`hskill install --tool browser-fetch`、`browser-fetch profile set`）、vdl/scholia（check-downstream）、路径 `<knowledgeRoot>/feeds/tweets/{digest,creators}/`。
- 调度只在宿主有能力且用户授权时启用（`:50` 和 claude 补丁 ③）。

**未确认**

- `:58`「抓取本身也不再按归档二次过滤」这条维护者约束，如果从 SKILL.md 删掉，设计文档里是否还有记录。【未查】
- `:68` 的 `migrate-store.sh --apply` 历史迁移提示还有没有用户需要。脚本还在仓库根【读到】，但旧数据是否已经全部迁完不知道。【未查】
- 删掉 platforms ② 的 `SKILL_DIR` 是否影响宿主侧调度配置（例如 /loop 的写法）。【未查】
- 参考文件表是否只给维护者看。如果是，可以整表移到设计文档；如果 agent 排错时会用，至少留下 5 个直接调用脚本那几行。【推出】

### 5. sync-ytchannel（潜力：中）

**问题归类**

- R6 解释与指令混写
  - `SKILL.md:56` 和 xtimeline `:58` 一样，混着游标理由、维护者备注和 report 结构。
  - 「日期精度」`:66-68`：解析逻辑在 `digest.py` 里。
  - `:74` 游标类型说明（URL 集合与 snowflake id 的区别）是给维护者看的，agent 不操作游标。
  - `:76` 设计文档沿革（「写作时还有 `pending.json` 断点机制……」）。
- R2 重复与跨 skill 依赖
  - `:56`「机制跟 sync-xtimeline 完全一样」。两个 skill 各自独立安装，这句引用读者不一定能查到，而且后文又把机制完整写了一遍。
  - 其余重复同 xtimeline：`:12/:46/:72`，参考文件表 `:78-93`，platforms ① 节。

**代表性修改**

1. 跨 skill 引用（R2）
   - 修改前（`:56`）：「**这一步不推进游标**，机制跟 sync-xtimeline 完全一样：该推到的值……」
   - 修改后：采用与 xtimeline 同一版精简措辞（见 4-1），把 `text` 换成 `title`，去掉「跟 sync-xtimeline 完全一样」。
   - 理由：独立安装后，这句引用找不到对象；同一版措辞也方便以后 diff。

2. 日期精度（R6）
   - 修改前：`:66-68` 一整节。
   - 修改后（并入「边界」）：
     > 摘要日期：Atom feed 覆盖到的（约最近 15 个上传）显示 ISO 时刻，否则原样显示相对日期，不反推。
   - 理由：保留用户追问时要用的输出契约。

3. 游标说明与沿革（R6）
   - 修改前：`:74`（游标是 URL 集合……）加上 `:76`（历史文档，写作时还有 `pending.json`……）。
   - 修改后：`:74` 删去；`:76` 只留「设计文档：`docs/superpowers/specs/2026-08-30-sync-timeline-output-alignment-design.md`」。
   - 理由：agent 不读写游标格式，游标由 `archive_videos.py` 推进。

**必须保留：** 与 xtimeline 相同的初始化、run 和接口约束，其中渠道相关项换成 `fetch_new_videos.py`、`digest.py`、`archive_videos.py`（按 video_id 去重）和 `feeds/youtube/`。另外保留 learn-video、clip-url 的分界，以及「频道页公开，没配 chrome_profile 也能跑」(`:64`)。

**未确认：** 同 xtimeline 的前三条；另外 `:74` 删掉之后，用户问「为什么 YouTube 不按 id 比大小」时要去设计文档里找，设计文档是否写了这一点。【未查】

### 6. manage-creators（潜力：中）

**问题归类**

- R4 渐进式披露
  - `SKILL.md:35-43`（从旧 sync-* 的 watchlist 迁移，带两条内联 python 单行命令）和 `:45-51`（`migrate-schema`），都只在特定历史状态下才用得上，却每次初始化都加载。
- R5 含糊
  - `:35`「若用户此前用过 sync-xtimeline / sync-ytchannel」没有给出判断方法。可以改成可检查的条件：`~/.hskill/sync-xtimeline/config.json` 或 `~/.hskill/sync-ytchannel/config.json` 存在。:39-40 的命令本来就读这两个文件。【推出】
- R2 历史措辞
  - `:59`「`add` 现在也吃网站文章列表页 URL」里的「现在」。
- 事实漂移（不属于精简，只标出来）
  - description `:4`、正文 `:10/:70` 没提 sync-website。

**代表性修改**

1. 迁移段落（R4）
   - 修改前：`:35-51` 两段迁移说明和命令。
   - 修改后：两段原样移入 `references/migration.md`，正文只留：
     > 初始化后若 `~/.hskill/sync-xtimeline/config.json` 或 `~/.hskill/sync-ytchannel/config.json` 存在（旧版关注列表），或 `registry.json` 的渠道缺 `key` 字段（旧 schema），读 `references/migration.md` 处理。迁移后不得自行 `merge`，只列候选对给用户确认。
   - 理由：正文约少 15 行，「不得自行合并」这条授权边界留在正文。

2. 表格单元（R2）
   - 修改前（`:59`）：「…`add` 现在也吃网站文章列表页 URL（`platform` 会是 `website`）。渠道按归一后的 key（去 `@`、trim、转小写）去重——同一个频道换个大小写的链接再 `add` 一次会报"已在名册中"，不会建出第二个人」
   - 修改后：「…支持 X、YouTube、网站列表页 URL（`platform` 为 `website`）。渠道按归一 key（去 `@`、trim、小写）去重，重复时报"已在名册中"。」
   - 理由：去掉历史措辞和重复举例，保留去重规则。

**必须保留：** 只写 `registry.json`；`DATA_DIR` 必须由用户提供、不得猜测，以及画像不可重建的提醒；`<roster_path> init/migrate/migrate-schema` 和 `registry add/list/merge/rename/remove` 的命令形态；`--from-xtimeline/--from-ytchannel` 参数；`remove` 输出里的画像归档路径必须转告用户；所有失败原样报 stderr、不重试；clip-url、learn-video 的分界。

**未确认：**

- 旧版迁移是否已经没有用户需要。如果是，可以整段删除，而不只是移走。【未查】
- description 是否补上 sync-website。这会改 description 文本，虽然不改触发词，仍建议单独决定。【推出】
- 把 `:35` 改成按文件存在来判断，算澄清还是算改行为：原文是「问一次」，改后是「检测到才问」。【未确认】

### 7. 潜力低 / 无

- **capture-opinion（低）**：「只写 profiles、确认后才落盘、不发明不加依据」这些硬规则已经各写一句。可删的只有三处：`:88-90` 与 description、`:15` 重复的边界列表；`:94`「当前判断还没有入口」这条开发备注；`:72` 的 stdin 理由（可以压成从句）。跨 skill 接口（`profile append --date`、`--source`、依据默认值「人工」、与 capture-insight 的分界）都要保留。

### 8. 范围外发现

- `skills/feed/record-observation/` 只剩 `scripts/__pycache__`，没进 git，也不在 skills-index.json 里【读到】。这是遗留目录，没有扫描。
- 3 个 sync-* 和 manage-creators 目录下有 `.pytest_cache/`、`__pycache__/`，都没进 git【读到：`git ls-files` 计数为 0】，不影响发布包。【未查：hskill 打包时是否过滤这两个目录】

---

## 第二部分：creative

### 1. 总览表

| skill | 当前规模（行） | 优化潜力 | 预估可减比例 | 主要问题 |
|---|---|---|---|---|
| capture-insight | 194 | 高 | 25–35% | 「设计要点」整节是解释，和「核心原则」「注意事项」三处重复；配置写入命令把默认路径写死 |
| capture-todo | 176 | 中 | 15–20% | 「核心原则」与开头、阶段一重复；工具教程式措辞；「高置信匹配」没有定义 |

### 2. capture-insight（潜力：高）

**问题归类**

- R6 解释与指令混写
  - 「设计要点」整节 `skills/creative/capture-insight/SKILL.md:20-32`（13 行）都是设计理由。其中影响决策的只有一条：不确定性措辞不升格。这一条在 `:181` 已经作为指令写过。
- R2 重复
  - 「一次只问一个问题」出现在 `:16`、`:22-23`、`:74` 三处。
  - 「保留不确定性」出现在 `:28-29`、`:180-181`（两条说的是同一件事）。
  - 「简洁、快速固定核心」出现在 `:14`、`:182`。
  - 五段结构的解释 `:31-32` 和模板 `:102-120` 里各段的说明重复。
  - 「从任意项目触发都写入 Writing Agent」出现在 `:61`、`:183`。
- R5 含糊或有缺陷
  - `:55-59`「用户确认后」接着执行 `echo '{"writing_agent_path": "/Users/harveyzhang96/Projects/writing-agent"}'`，写入的是**写死的默认值**。用户回答的是别的路径时，按字面执行会写错【读到】。
  - `:193`「如果发现这个 insight 与现有文章方向相关」没有说要不要去查 writing-agent 里的文章，也没说查哪里。
  - `:87`「按以下步骤写入」之后先插了「文件格式」一节，再到 Git 节。实际顺序是：先切分支，再写文件（`:129-157`）。顺序隐含在后文里，第三步没有点明。
- R3：`:65-70` 的「复述确认」是这个 skill 自己的动作，保留；示例可以只留一句。

**代表性修改**

1. 设计要点（R6 + R2）
   - 修改前：`:20-32` 整节 4 个「为什么……？」问答。
   - 修改后：删去整节，「注意事项」`:180-183` 合并成：
     > - 不替用户升格判断：保留"感觉/好像/也许"等不确定措辞（摘要写"你观察到 XX 可能是趋势"，不写"XX 是重要趋势"）。
     > - insight 文件求短，目标是三个月后能找回当时的思路。
     > - 始终写入配置里的 `{project_path}`，不受当前工作目录影响。
   - 理由：设计理由不改变执行动作，影响决策的那条已经是指令。代价是以后维护者看不到「为什么一次只问一个」的论证，如果需要，可以挪进设计文档。

2. 配置写入（R5）
   - 修改前（`:51-59`）：
     > "没找到 Writing Agent 项目配置。请确认项目路径（默认：`/Users/harveyzhang96/Projects/writing-agent`）？" 用户确认后……`echo '{"writing_agent_path": "/Users/harveyzhang96/Projects/writing-agent"}' > ~/.hskill/capture-insight/config.json`
   - 修改后：
     > 配置不存在时，询问 Writing Agent 项目路径（默认 `/Users/harveyzhang96/Projects/writing-agent`），把**用户确认的路径**写入 `~/.hskill/capture-insight/config.json` 的 `writing_agent_path`（必要时先 `mkdir -p ~/.hskill/capture-insight`）。
   - 理由：消除「确认了别的路径，却写进默认值」的歧义。用户接受默认值时，结果和原文相同。

3. 第三步写入顺序（R5 / R6）
   - 修改前（`:86-87`）：「1. 给出一段 insight 摘要……2. 用户确认后，生成文件名，按以下步骤写入 `{project_path}/insights/`」
   - 修改后：「2. 用户确认后，生成文件名，按「写入 & Git 操作」依次执行：切到 `chore/insight` → 写文件 → 提交并合并 → 切回原分支。」
   - 理由：把顺序约束写在决策点上。先写文件再切分支，文件会落在原分支的工作区里【推出】。

**必须保留、不能动的语义**

- 配置文件 `~/.hskill/capture-insight/config.json` 和字段 `writing_agent_path`；写入目录 `{project_path}/insights/`；文件名 `YYYY-MM-DD-<slug>.md`（slug 用英文）。
- 文件模板的标题和五段：原始触发 / 核心观察 / 为什么有意思 / 潜在方向（用户没说就留空、不补）/ 关键词 2–4 个，加上 `> 记录于 YYYY-MM-DD`。
- 流程：先复述确认，再问 2–3 个澄清问题（按「触发、张力、方向（可选）」的顺序，已有答案的跳过），然后给 3–5 句摘要，用户确认后才写。
- Git：`chore/insight` 分支；BASE_BRANCH 选择逻辑；非 git 仓库跳过；commit `insight: add YYYY-MM-DD-<slug>`；`--no-ff` 合并；切回原分支；保存后的回报格式（`:189-191`）。
- description 原文，含「Distinct from 'I have an idea to execute' (that's a task)」这条与 capture-todo 的分界。capture-opinion `:92` 也把 capture-insight 当作分界对象。

**未确认**

- `:193`「与现有文章方向相关时顺带一提」是要求主动检索，还是只凭对话里已有的信息判断。【未确认】
- 范围外的行为问题：BASE_BRANCH 回退 `$(git symbolic-ref … | sed … || echo "main")`（`:141-142`，capture-todo `:105-106` 写法相同）。管道的退出码取的是 `sed` 的，`sed` 对空输入也返回 0，所以 `|| echo "main"` 不会生效。没有 `origin/HEAD` 时 BASE_BRANCH 为空【推出：按 shell 语义推断，未实跑】。不属于精简，应单独修。
- 范围外的行为问题：合并用 `git merge --no-ff chore/insight -m "Merge chore/insight: …"`（`:170`）。capture-todo 为了同时过 pre-commit 和 commit-msg 两个 hook，改成了 `--no-commit` 加 Conventional Commits（`:163-168`）。writing-agent 仓库有 `.githooks/commit-msg`，但 `core.hooksPath` 当前指向 `.git/hooks`，而那里没有启用的 hook【读到】，所以现在不会触发。将来启用 hooks 后，这个合并提交可能被拒【推出】。

### 3. capture-todo（潜力：中）

**问题归类**

- R2 重复
  - `skills/creative/capture-todo/SKILL.md:10`、「核心原则」`:12-14` 和 `:29` 都在说「先需求后项目、问题聚焦需求、够了就停」。
  - `:59` 的「谨慎原则」和 `:57` 表格行「无匹配或不确定 → 展示完整项目列表」意思重合。保留它也只需一句。
- R2 / R3 工具教程式措辞
  - `:35`「用 Read 工具读取」、`:41`「用 Bash 运行 `pwd` 获取当前目录」，可以压成「读取注册表、取当前工作目录」。
- R5 含糊
  - `:55`「唯一高置信匹配」没有和 `:47-49` 的强、中、弱信号对应起来。没写清：只有强信号（`pwd` 命中 `local_path`）算高置信，还是中信号指向唯一项目也算。
  - `:47`「项目 `local_path`」：注册表 `~/.hskill/todo-tool/PROJECTS.md` 里的条目实际格式是 `- **名称** \`路径\``，没有名为 `local_path` 的字段【读到】。这个名字是概念名，可以注明「即注册表条目里的路径」。
- R6 生成标题的规则
  - `:65-68` 4 条可以压成 2 条。示例 `:73` 用了已经改名的「add-todo skill」，不影响规则。

**代表性修改**

1. 开头与核心原则（R2）
   - 修改前：`:10`「快速捕获需求：先用 2-3 个问题把需求说清楚，再根据完整的需求信息匹配项目、生成标题，最后写入 TODO.md。」加上 `:12-14`「## 核心原则 / **先把需求说清楚，再定项目归属。** 完整的需求描述是项目匹配最好的材料。问题只聚焦需求本身，不聚焦方案。够写一条清晰的任务条目就停，不要拖长。」
   - 修改后：
     > 快速捕获需求：先用 2-3 个问题澄清需求（只问需求、不问方案，够写一条清晰条目即停），再据此匹配项目、生成标题，最后写入 TODO.md。顺序不能反：完整需求是项目匹配的依据。
   - 理由：三处合成一处，「先需求后项目」的顺序约束和理由保留成一句。

2. 读注册表（R2/R3）
   - 修改前（`:35-41`）：「需求收集完毕后，用 Read 工具读取项目注册表：```~/.hskill/todo-tool/PROJECTS.md``` 同时用 Bash 运行 `pwd` 获取当前目录。」
   - 修改后：「需求收集完毕后，读取项目注册表 `~/.hskill/todo-tool/PROJECTS.md`（每条含项目名、本地路径 `local_path`、描述），并取当前工作目录。」
   - 理由：删掉工具名教程，同时补上 `local_path` 和注册表格式的对应关系。补充内容来自读到的文件格式。

3. 标题规则（R6）
   - 修改前（`:65-68`）：「祈使句，动词开头……/ ≤20 字……/ 足够具体……避免泛泛的"优化"、"修复" / 不堆砌细节，只抓最关键的区分点」
   - 修改后：「祈使句、动词开头、≤20 字（超出则去修饰语）；写出关键区分点，不用"优化""修复"这类泛词，也不堆细节。」
   - 理由：4 条合成 1 条，约束不变，示例保留。

**必须保留、不能动的语义**

- 阶段一：一次只问一个问题、优先给选项、默认 P2、已明确的跳过。
- 阶段二：三档信号和确认策略表；用户确认「项目 — 标题，优先级」之后才写。
- 阶段三：`{local_path}/TODO.md`；没有 `local_path` 时询问，并提示 `todo project set-path [项目名] [本地路径]`（todo CLI 接口）；`chore/todo` 分支的创建和切换逻辑，BASE_BRANCH 优先 staging；BRANCH_GUARD 相似分支警告直接确认；非 git 仓库跳过；重复检查的三个选项（跳过 / 替换 / 独立写入）。
- 写入格式：追加到 `## 🚧 待开发` 末尾；条目模板 `### 标题` / `**优先级**: P? | **日期**: YYYY-MM-DD` / 描述（只写做什么、为什么，不写怎么做）/ `---`；新文件的初始结构（含 `## ✅ 已完成`）。这些 emoji 标题是输出契约，其他工具可能按标题解析。【未查是否有解析方】
- 提交：`todo: add [标题]`；`git merge --no-ff --no-commit` 再 `git commit -m "chore(todo): add [标题]"`，这样拆成两步是为了同时过两个 hook。`:163-165` 的注释可以压短，但两步结构不能合并。最后切回原分支，并按 `:176` 格式回报。
- description 原文（含各种随口说法的触发词）。

**未确认**

- `:55`「高置信」按哪一档信号算。改成明确规则会影响「直接确认」和「列候选」的分界，算行为调整，需要你定。【未确认】
- `todo project set-path` 当前在本机跑不起来：`/opt/homebrew/bin/todo` 报 `ModuleNotFoundError: No module named 'todo'`【读到】。不属于精简，提示文案先保留。
- BRANCH_GUARD hook 的来源。仓库里只有这个 SKILL.md 提到它【读到：grep】，没查到是哪个工具生成的。【未查】
- BASE_BRANCH 回退无效（同 capture-insight 未确认第 2 条）。【推出】

---

## 未确认项汇总

| # | skill | 事项 | 把握度 |
|---|---|---|---|
| 1 | sync-* | 三份副本已经出现的文案漂移（install 提示、chrome_profile 位置、「四个」与实际 5 份）以哪版为准 | 读到漂移；是否有意未查 |
| 2 | sync-xtimeline / ytchannel | 「抓取不按归档二次过滤」等维护者备注移出后，设计文档里是否还有记录 | 未查 |
| 3 | sync-xtimeline / ytchannel / website | `migrate-store.sh` 历史迁移提示是否还需要 | 未查 |
| 4 | sync-* | 删去 platforms ② 的 `SKILL_DIR` 是否影响调度配置 | 未查 |
| 5 | sync-website | 自愈细节移入 reference 后，无人值守 run 会不会漏读 | 推出 |
| 6 | sync-website | `:110`「二档上限」所说的人工路径在哪 | 未查 |
| 7 | manage-creators | 旧版迁移能否整段删除；description 是否补上 sync-website；「用过旧版」改成按文件存在判断，算不算行为变化 | 未查 / 推出 |
| 8 | capture-insight | `:193` 是否要求主动检索已有文章 | 未确认 |
| 9 | capture-insight / todo | BASE_BRANCH 的 `echo "main"` 回退无效 | 推出（未实跑） |
| 10 | capture-insight | 合并提交将来遇到 commit-msg hook 可能被拒 | 读到 hooks 现在未启用；后果推出 |
| 11 | capture-todo | 「高置信匹配」的判定档位 | 未确认 |
| 12 | capture-todo | `todo` CLI 当前不可用；BRANCH_GUARD 来源 | 读到 / 未查 |
| 13 | capture-todo | `🚧 待开发` 等标题是否有下游解析方 | 未查 |

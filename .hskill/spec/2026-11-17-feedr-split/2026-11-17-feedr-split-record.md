# 决定记录：browser-fetch + roster 拆为独立产品 feedr

建档日期：2026-11-17
分支：`feature/feedr-split`

**需求批准：** 用户 2026-11-17 确认 question-me 需求摘要（补充“仓库目录放在Projects路径下”，并答复“可以，按照全新仓库来设置，不需要保留之前的git”），批准 D1–D20；D21–D23 为未决，状态“已提出”。D24 于方案审查中由用户选择批准（答复“A”）。

**Spec 批准：** `2026-11-17-feedr-split-spec.md` v0.1 于 2026-11-17 获用户批准（答复“可以，批准，写plan”），覆盖当前决定 D1–D20、D24 及 Spec 第 11 节次要决定 S1–S15；D21–D23 仍为未决。

## 当前决定

### D1 把 browser-fetch 做成独立产品

- **决定：** `tools/browser-fetch` 从 harveyz-skill 拆出，成为独立维护的产品。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“现在我想把这个仓库做成一个独立的产品。”（承接“能够独立出一个单独的仓库，进行维护？”）

### D2 给多个 agent 直接调用，hskill 只管 skill

- **决定：** 产品供多个 agent 宿主直接调用，不经 hskill；hskill 定位收窄为独立的 skill 管理仓库，独立工具迁出。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“给多个agent去调用，不经过hskill，hskill的定位要变成独立skill管理仓库，独立的工具要独立出去，而且我要进一步加强browser-fetch的功能”。

### D3 本轮迁出 browser-fetch 与 roster，融合成一个产品概念

- **决定：** 本轮一起迁出 browser-fetch 与 roster，并融合成一个产品，而非两个并列工具。`hub`、`sync-agent`、`skill-harness` 不在本轮。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“这一轮先迁出哪些工具？”选项：A 只迁 browser-fetch / B 加 roster / C 全部。答复：“B，但需要注意这两个怎么融合成产品概念”。

### D4 产品边界含「按名册增量追更」

- **决定：** 产品 = 名册 + 抓取 + 按名册增量追更（含存档与游标推进）；sync-* skill 只留翻译、摘要与交互。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“产品的边界划在哪里？”选项：A 连追更收进产品 / B 只提供两块原料。答复：“A”。
- **依据：** 追更编排现分散在 `skills/feed/sync-*/scripts/fetch_new_*.py`、`cursor.py`、`archive_*.py`，三份各一套。

### D5 一个仓库、一个包、一个 CLI，命令组 fetch / roster / sync

- **决定：** 产品形态为单仓库、单 Python 包、单 CLI，下设 `fetch`、`roster`、`sync` 三个命令组。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“产品对外是什么形态？”选项：A 一个 CLI 多组命令 / B 一个仓库多个 CLI。答复：“A”。

### D6 产品名 feedr

- **决定：** 产品名 `feedr`，同时是仓库名、CLI 命令名与数据目录名（`~/.feedr`）。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“产品叫什么？”选项：tailer / feedr / trawl。答复：“B”。

### D7 本轮只做拆分，行为不变

- **决定：** 本轮只做拆分，现有 skill 的对用户可见行为不变；收藏夹同步另立需求。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“收藏夹同步和拆分放同一轮吗？”选项：A 分两阶段同一份 Spec / B 一轮做完 / C 只做拆分。答复：“C”。

### D8 名册的渠道模型须能扩展收藏夹类渠道

- **决定：** 本轮不实现收藏夹同步，但名册与追更的结构须允许以后加入“我的收藏夹”这类渠道，而不推翻现有模型。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：用户原始需求要“加强 browser-fetch 的功能”，并描述了收藏夹同步（见 D21），D7 将其推后。

### D9 产品自有数据目录，初始化时同步旧数据

- **决定：** 产品使用自有数据目录；存档根由产品配置，默认取 `~/.hskill/config.json` 的 `knowledgeRoot`；初始化时把旧数据（browser-fetch 登录态、roster 数据、`knowledgeRoot`）同步过去。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“产品独立后，数据和配置放在哪？”选项：A 自有目录并迁移 / B 留在 `~/.hskill`。答复：“A，初始化的时候同步过去”。
- **依据：** 现状 `~/.hskill/browser-fetch/contexts/`、`~/.hskill/roster/`（`config.json` 的 `DATA_DIR`）、`knowledgeRoot=~/knowledge`；`knowledgeRoot` 另被 clip-url、learn-video 读取。

### D10 迁移只复制不删除

- **决定：** 初始化同步只复制，不删除 `~/.hskill` 下的旧数据。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：画像文件不可重建（`skills/feed/manage-creators/SKILL.md`），可逆优先。

### D11 存档位置与 JSON 格式不变

- **决定：** `<knowledgeRoot>/feeds/` 下的存档位置与 JSON 格式保持不变。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：D7 要求行为不变；外部工具直接读存档 JSON（sync-* SKILL.md「边界」节）。

### D12 GitHub 公开仓库，暂不发 PyPI

- **决定：** GitHub 公开仓库；暂不发布 PyPI，以后再发。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“这个产品打算公开吗？”选项：A 公开并发 PyPI / B 公开不发 PyPI / C 私有。答复：“B，以后再发布pypI”。

### D13 安装方式 uv tool install git+

- **决定：** 安装命令为 `uv tool install git+https://…`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——随 D12 的答复确定。

### D14 hskill 不管 feedr 依赖

- **决定：** hskill 不检测、不提示、不代装 feedr；skill 运行时找不到 feedr 就报错并给出安装命令。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“hskill 怎么处理 feedr 依赖？”选项：A 检测提示 / B 代装 / C 完全不管。答复：“C”。

### D15 只提供 CLI + JSON stdout，不做 MCP

- **决定：** 对外接口只有 CLI，机器可读输出为 stdout 上的 JSON；不提供 MCP。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：仓库已从 `browser-fetch-mcp` 迁到 CLI；CLI 任何宿主都能调。

### D16 单条失败记 state，下次重试

- **决定：** 渠道抓取失败记入 state，下次运行重试。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：roster 已有 `state fail`。

### D17 本地仓库 ~/Projects/feedr，全新 git 仓库

- **决定：** 新仓库位于 `~/Projects/feedr`，全新 `git init`，不保留 harveyz-skill 中的历史。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“仓库目录放在Projects路径下”；“按照全新仓库来设置，不需要保留之前的git”。

### D18 旧命令名不保留兼容入口

- **决定：** 不保留 `browser-fetch`、`roster` 命令名；所有调用方同轮改为 `feedr`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：调用方全部在本仓库内，可同轮改完。

### D19 hskill 移除两个工具及其登记

- **决定：** harveyz-skill 移除 `tools/browser-fetch`、`tools/roster`，以及 `package.json` 的 `files` 条目和 `skills-index.json` 中 `research-tools` 的工具条目与 bundle 说明。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——依据：D2、D3。

### D20 YouTube 收藏可指定某个自建播放列表

- **决定：** 将来的收藏夹同步要能指定某个自建播放列表。稍后观看、点赞列表一并支持；X 侧收藏指书签，不含点赞。
- **状态：** 已批准（question-me 摘要确认），仅约束 D21 的未来需求
- **来源：** 用户选择——问题：“YouTube 的收藏指哪些？”答复：“可以指定某个自建列表”；其余为 Agent 推断。

### D24 追更采用两段式命令 sync fetch / sync commit

- **决定：** `feedr sync fetch <platform>` 输出报告 JSON、不动游标；agent 翻译并生成摘要后，`feedr sync commit <platform>` 读报告、写存档并推进游标（本轮提交点）。报告结构沿用现有 `fetch_new_*.py` 的输出。
- **状态：** 已批准
- **来源：** 用户选择——问题：“追更命令怎么容纳中间的翻译？”选项：A 两段式 fetch/commit / B 一条命令跑完、翻译事后回填。答复：“A”。
- **依据：** 现有设计游标晚推、中断不漏报（`skills/feed/sync-xtimeline/scripts/archive_tweets.py`）；B 会让游标先于摘要推进，违反 D7、D11。

## 未决

### D21 收藏夹同步

- **决定：** 盯住自己 X / YouTube 账号的收藏，增量抓取元数据与完整内容存入产品存档；默认从现在起，另有可选回填命令；只做增量，不对账。另立需求，不在本 Spec 范围。
- **状态：** 已提出
- **来源：** 用户原始需求——“盯着我某个X账号或者YouTube账号的收藏夹，然后做批量的抓取和核对……”；细节为用户选择（产物 A、核对 C、首次同步 C）。

### D22 发布 PyPI

- **决定：** 以后再发。
- **状态：** 已提出
- **来源：** 用户选择（D12 的答复）。

### D23 feedr 名称占用

- **决定：** GitHub / PyPI 上 `feedr` 是否被占用未查。
- **状态：** 已提出
- **来源：** Agent 推断——需访问外网，待用户同意。

## 已否定与已失效

（无）

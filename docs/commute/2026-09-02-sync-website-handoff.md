# 交接：实现 sync-website —— 把网站接进 creator/channel 追更体系

**日期**：2026-09-02
**author 模型**：Claude Opus 5
**状态**：执行中 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：设计稿已经过用户逐项决策并评审通过，接手方从 spec 出发拆实施计划并完成实现——本次交接不重开设计讨论。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，若文档里有「工作流约定」章节按其开工，没有就直接开工。**完成后把上面的状态置为「待验收」并停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。你的自测结果写成独立小节，别写进原 session 的验收记录里。

---

## 最小验收锚点

硬判据，逐条对/错，全绿才算达成：

1. `cd tools/browser-fetch && .venv/bin/pytest -q` → **≥ 141 passed，且原有 141 条一条都没被修改**（`git diff` 在 `tools/browser-fetch/tests/` 下只有新增文件或新增用例，没有对已有用例断言的修改）。
2. `cd tools/roster && .venv/bin/pytest -q` → **≥ 131 passed**，且新增用例覆盖：`parse_channel_url("https://simonwillison.net/")` 返回 `("website", "simonwillison-net")`；`parse_channel_url("https://www.youtube.com/watch?v=abc")` **仍然抛 `ValueError`**（不得掉进 website 兜底）；`parse_channel_url("https://x.com/a/b/c")` 仍然抛 `ValueError`。
3. `npm test` → **fail 0**（原 session 实跑基线：328 tests / 321 pass / 0 fail / 7 skipped），且 `skills/feed/sync-website/SKILL.md` 通过格式校验。
4. `grep -n "dispatch_site" tools/browser-fetch/browser_fetch/extractors.py tools/browser-fetch/browser_fetch/core.py` 的输出与实现前**逐行相同**——`dispatch_site()` 的定义和它的两个调用点一个字都没动。
5. `grep -rn "import\|^from" skills/feed/sync-website/scripts/*.py` 的结果里**只有标准库和同目录模块**，没有任何第三方包。
6. `skills-index.json` 里存在 `sync-website` 条目，`path` 与 `bundle` 填写正确，`npm test` 的索引校验通过。
7. 端到端手测一个真实站点（建议 `https://simonwillison.net/`）：`calibrate` 能固化出规则，`run` 第一次建立基线、第二次报告 `EMPTY`，`<knowledgeRoot>/feeds/website/creators/simonwillison-net.json` 有内容。**这一条是手测，把实际命令和输出贴进你的自测小节。**

---

## 背景与现状

仓库里已经有两个同构的追更 skill：`sync-xtimeline`（X）和 `sync-ytchannel`（YouTube）。它们共用一份 roster 名册（`tools/roster`，持有 creator/channel 定义和游标）和一份 `knowledgeRoot` 配置，各自跑一次增量抓取，产出翻译过的 Markdown 摘要 + 按渠道分文件的 JSON 归档。

`sync-website` 是同体系的第三个渠道类型：跟一批**网站的文章列表页**，每次运行只报告上次运行之后新出现的文章（标题翻译成中文）。

**当前进度**：设计稿写完并提交，用户已评审通过。**代码一行未写。** 分支 `feature/sync-website`，其上两个 commit 都只动了 spec 文件：

```
f6a26f3 docs(spec): 补 browser-fetch 隔离约束，纠正 dispatch_site 措辞
7c2d735 docs(spec): sync-website 设计稿——网站接进追更体系
```

**下一步**：用 `superpowers:writing-plans` 从 spec 拆实施计划，再用 `superpowers:executing-plans` 执行。

**但拆计划之前，先花十分钟证伪一个假设。** spec §9 把「playwright 在页面内跑 CSS selector 抽列表」列为**推出来的、未实测**——依据只是 `evaluate_js` 子命令的存在，`articles` 这条具体形状没跑过。这条假设是整个设计的地基：不成立就不是改几行的事，是方案要重选（退回被否掉的「每次由模型现场抽」）。

最省的证伪办法是拿已有的 `eval` 子命令打一枪，不写任何新代码：

```bash
cd tools/browser-fetch
cat > /tmp/probe.js <<'EOF'
() => [...document.querySelectorAll('div.entry')].slice(0,5).map(el => ({
  title: el.querySelector('h3 a')?.textContent?.trim() || '',
  url:   el.querySelector('h3 a')?.href || '',
  date:  el.querySelector('p.date')?.textContent?.trim() || ''
}))
EOF
./browser-fetch.sh eval https://simonwillison.net/ --js-file /tmp/probe.js
```

（selector 是照 spec §3.2 示例写的，未必对得上该站当下的 DOM——抽不到就改 selector 再试，**要验的是"这条路能不能通"，不是这组 selector 准不准**。）

能拿回结构化条目 → 假设成立，照 spec 拆计划。
拿不回来 → **停下来回报原 session**，不要自行改设计。

---

## 关键决定（别改动）

以下五条是用户在设计阶段**逐个明确选定**的，不是默认值，不要重新纠结或推翻。每条附上被否掉的选项，免得你以为那些还是开放的。

| 决定 | 否掉了什么 |
|---|---|
| **走浏览器抓 HTML，不做 RSS/Atom** | 否掉了「RSS 优先 + 浏览器兜底」和「只做 RSS」。不要因为"很多站有 feed"就顺手加一条 RSS 路径 |
| **首次生成 selector 并固化，之后机械执行** | 否掉了「每次 run 都由模型现场抽」和「先试通用启发式」。运行期不做任何模型抽取，模型只翻译标题 |
| **规则的所有权在 browser-fetch，不在 skill** | 否掉了「skill 持有 selector 每次传进去」和「复用 `eval` 子命令每站存一段 JS」。`articles` 在生产路径上**不接受 selector 参数** |
| **一个域名 = 一个渠道** | 否掉了「一个列表页 = 一个渠道」和「撞了反问用户要 handle」。handle 是域名 slug（去 `www.`、点换连字符），同域第二个列表页会被 roster 判重拒绝，这是接受的代价 |
| **标定验收 = 机械门槛 + 模型过目** | 否掉了「只要机械门槛」和「机械门槛 + 人工确认」。人工确认被否是因为 run 在 `/loop` 里无人值守、问不了人 |

另外两条来自设计推导，同样已定：

- **游标晚推**：`fetch_new_articles.py` 不写游标，把该推到的值放进 `report["cursors"]`，由 `archive_articles.py` 在摘要和归档都落盘之后才写回。这是本轮唯一的提交点。
- **自愈必须可见**：run 内重新标定成功的渠道，digest 里必须显式标注一行。没有这个标注，「改版 → 自愈换规则 → 抽出导航链接 → 摘要看起来正常」这条路径完全隐形。

---

## 范围铁律

### IN

- `tools/roster/roster/urls.py`：新增 website 兜底匹配 + 已知平台域名拦截
- `tools/browser-fetch`：新增规则库 + `articles` / `articles-probe` / `articles-rule` 三个子命令 + `fetch_articles` 一个 core 函数
- `skills/feed/sync-website/`：新 skill，脚本与 `sync-ytchannel` 一一对应
- `skills-index.json`：登记新 skill
- `skills/feed/manage-creators/SKILL.md`：补一句 `add` 现在也吃网站列表页 URL
- `skills/feed/sync-ytchannel/SKILL.md` 与 `sync-xtimeline/SKILL.md` 的「边界」小节：补第三个同体系 skill 的交叉引用

### OUT —— 碰了就是超范围

- **`dispatch_site()` 一行不动。** 它在 `extractors.py:20`，被 `fetch_article`（`core.py:383`，clip-url 主路径）和 `fetch_user_timeline`（`core.py:549`，sync-xtimeline 的 X 守卫）调用。规则库走独立查表，跟它零调用关系。
- **不重构 core 里任何已有函数。** `fetch_page` / `fetch_article` / `fetch_user_timeline` / `fetch_channel_videos` / `evaluate_js` 是互不调用的平级 async 函数，`fetch_articles` 是第六个同级函数，不为它动前五个。
- **不改共享设施的签名或语义。** 只允许只读复用这四样：`_get_context(key)`、`_profile_key()`（`core.py:56,69`）、`config.get_default_chrome_profile(_data_dir())`、`extract_cookies()`。**任何一处需要改它们才能实现，说明设计走偏了——停下来回报，不要顺手改。**
- **不碰 pacing 状态。** `timeline_pace.json` 只被 `fetch_user_timeline` 读写（`core.py:570,612`）。第一版不给 `articles` 加冷却。
- **不改 browser-fetch 已有的任何测试用例。** 见验收锚点第 1 条。
- **不删 `tools/browser-fetch-mcp/`。** 它源码已空、只剩 `__pycache__`，是遗留死代码。已知，本次不处理。
- 不抓正文、不进 Obsidian、不打标、不生成 HTML 视图。单篇入库归 `clip-url`。
- **不写 `registry.json`。** 渠道增删归 `manage-creators`，本 skill 只读渠道列表、只写 `state.json` 的游标。

---

## 相关文档索引

| 路径 | 是什么 |
|---|---|
| `docs/superpowers/specs/2026-09-02-sync-website-design.md` | **本次实现的唯一权威依据。** §3.4 是 browser-fetch 隔离约束八条，§7 是代价汇总，§9 是把握度分级（哪些是读过代码确认的、哪些是推的、哪些没查） |
| `skills/feed/sync-ytchannel/` | **一比一参照实现。** SKILL.md 的结构、scripts 的分工、tests 的组织方式都照抄，只改渠道相关的部分 |
| `skills/feed/sync-xtimeline/SKILL.md` | 游标晚推机制的另一份表述，措辞可复用 |
| `skills/feed/manage-creators/SKILL.md` | 名册写入方。理解「谁能写 registry.json」的边界 |
| `docs/reference/testing-guide.md` | **写新测试前必读** |
| `docs/reference/git-workflow.md` | 分支规范全文（自动生成，勿手改） |
| `CLAUDE.md` | 仓库定位、skill 结构约定、发布新 skill 的步骤 |

---

## 受影响文件/落点

| 文件 | 动作 |
|---|---|
| `tools/roster/roster/urls.py` | 改 `parse_channel_url()`：已知平台域名拦截 + website 兜底 |
| `tools/roster/tests/test_urls.py` | 加用例，见验收锚点第 2 条 |
| `tools/browser-fetch/browser_fetch/site_rules.py` | **新增**，规则库读写（纯 I/O，参照 `config.py` 的写法） |
| `tools/browser-fetch/browser_fetch/extractors.py` | **只追加** `articles` 的求值 JS 常量。`dispatch_site()` 不动 |
| `tools/browser-fetch/browser_fetch/core.py` | **只追加** `fetch_articles()` 等新函数 |
| `tools/browser-fetch/browser_fetch/cli.py` | 在 `build_parser()`（`cli.py:29`）**末尾追加**三段 subparser。已有 subparser 定义不动 |
| `tools/browser-fetch/tests/` | 新增测试文件 |
| `skills/feed/sync-website/SKILL.md` | **新增** |
| `skills/feed/sync-website/platforms/` | **新增**四份平台补丁，照抄 sync-ytchannel |
| `skills/feed/sync-website/scripts/` | **新增**。`roster_locate` / `browser_fetch_locate` / `browser_fetch_cli` / `store_config` / `cursor` 是独立副本直接照抄；`roster_client`（改 `PLATFORM`）、`config`（改 `feeds_dir`）微调；`articles_client` / `fetch_new_articles` / `digest` / `archive_articles` 新写 |
| `skills/feed/sync-website/tests/` | **新增**，照 sync-ytchannel 的组织方式 |
| `skills-index.json` | 加 `sync-website` 条目；按 CLAUDE.md 更新 `contentHash` / `contentVersion` |
| `skills/feed/manage-creators/SKILL.md` | 补一句 |
| `skills/feed/sync-ytchannel/SKILL.md`、`sync-xtimeline/SKILL.md` | 「边界」小节补交叉引用 |

---

## 工作流约定

- 在**已存在的 `feature/sync-website` 分支**上继续，不要另开分支。一个迭代一个分支，累积所有改动。
- `main` / `staging` 由 `.githooks/pre-commit` 禁止直接提交。
- **只在用户明确说「合并/完成」时才 merge 到 staging**，合并一律 `--no-ff`。
- commit-msg hook 强制 Conventional Commits，类型限 `feat | fix | chore | docs | refactor | test | style | perf`。**注意是 `docs` 不是 `doc`——写 `doc(...)` 会被 hook 拒绝**（原 session 踩过）。首行 ≤ 80 字符，也是 hook 强制的。
- 拆计划用 `superpowers:writing-plans`，执行用 `superpowers:executing-plans`。

---

## 验证步骤

三个测试套，**动手前先各跑一遍拿到你自己的基线**，别直接信下面的数字：

```bash
cd tools/browser-fetch && .venv/bin/pytest -q      # 原 session 实跑：141 passed
cd tools/roster        && .venv/bin/pytest -q      # 原 session 实跑：131 passed
npm test                                            # 仓库根；原 session 实跑：328 tests / 321 pass / 0 fail / 7 skipped
```

`npm test` 覆盖 hskill CLI 行为和所有 skill 的 SKILL.md 格式校验。新增 skill 后它会校验 `sync-website/SKILL.md` 的 frontmatter（`name` 与目录名一致、semver `version`、`description`、`user_invocable`）。

端到端手测（验收锚点第 7 条）需要 browser-fetch 和 roster 都已安装、`knowledgeRoot` 已配置。若本机没配过，先按 `sync-ytchannel/SKILL.md` 的「初始化」小节走一遍。

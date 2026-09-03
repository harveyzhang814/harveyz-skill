# 交接：实现 site_rules 三档抽取（selector / +transform / 全 JS）

**日期**：2026-09-03
**author 模型**：Claude Opus 5
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：设计与实施计划都已写完并经用户确认，接手方按计划逐任务执行到**阶段一结束为止**——本次交接不重开设计讨论，也不自行推进到阶段二。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，若文档里有「工作流约定」章节按其开工，没有就直接开工。**完成后把上面的状态置为「待验收」并停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。你的自测结果写成独立小节，别写进原 session 的验收记录里。

---

## 最小验收锚点

硬判据，逐条对/错，全绿才算达成。**范围只到阶段一（计划 Task 1–8.5）。**

1. `cd tools/browser-fetch && .venv/bin/pytest -q` → **≥ 175 passed**（原 session 实跑基线 175），且 `git diff` 在 `tools/browser-fetch/tests/` 下**只有新增文件、新增用例，以及第 6 条点名的那一处改写**。
2. `cd skills/feed/sync-website && python3 -m pytest tests -q` → **≥ 80 passed**（基线 80），已有用例零改动。
3. `cd tools/roster && .venv/bin/pytest -q` → **140 passed**（基线 140，本阶段不该碰 roster，数字必须一模一样）。
4. `npm test` → **fail 0**（基线 328 tests / 321 pass / 0 fail / 7 skipped）。
5. `grep -rn "^import \|^from " skills/feed/sync-website/scripts/*.py` → 只有标准库和同目录模块，无任何第三方包。
6. **唯一被许可修改的已有测试**：`tools/browser-fetch/tests/test_site_rules.py` 里的 `test_rule_file_written_under_site_rules_subdir`（它断言扁平路径 `site_rules/example.com.json`）。`git diff` 显示除它之外**没有任何已有测试被改**。
7. 一档行为逐字不变，实测确认：

```bash
cd tools/browser-fetch
./browser-fetch.sh articles https://claude.com/blog | python3 -c "import json,sys;d=json.load(sys.stdin);a=d['articles'];print(len(a));print(a[0])"
```

→ 15 条；第一条形如 `{'title': 'A guide to the anatomy of effective commerce agents', 'url': 'https://claude.com/blog/the-anatomy-of-effective-commerce-agents', 'date_text': 'Sep 2, 2026'}`。**URL 必须是绝对的，`date_text` 必须非空。**（站点可能已更新内容，条数和标题可以变；形状不能变。）

这条依赖本机规则库里已有 `claude.com` 的规则（原 session 标定过，落在 `~/.hskill/browser-fetch/contexts/site_rules/`）。若 `./browser-fetch.sh articles-rule get claude.com` 报 `NO_RULE`，用这组 selector 重新固化再验：

```
{"item": ".blog_cms_grid .blog_cms_item", "title": ".card_blog_title",
 "link": "a.clickable_link", "date": ".u-text-style-caption.u-foreground-tertiary"}
```

8. 二档隔离成立，`pytest tests/test_cli_articles_transform.py -k "cookies or target_page"` 两条通过——transform 读不到目标站 cookie、`location.href` 是 `about:blank`。**这是整套分级的支点，这两条挂了就等于二档白做。**

9. 迁移真的发生（计划 Task 8.5 Step 3）：对某个已有域名重跑一次 `articles-rule set` 后，`ls ~/.hskill/browser-fetch/contexts/site_rules/` 显示出现了 `<domain>/` 目录且同名 `.json` 已消失。**把实际命令与输出贴进你的自测小节。**

10. **阶段二（Task 9–14）一行代码都没动。** `git diff` 里不存在 `static_scan.py`、`allow_script`、`extract.js`、`review.md` 相关改动。

---

## 背景与现状

`sync-website` 已经上线并在用：它跟一批网站的文章列表页，靠 browser-fetch 的 `articles` 子命令抽取，抽取规则存在 browser-fetch 的规则库里（一域名一份 JSON，存的是 CSS selector）。

**本次要解决的问题**：selector 这一档表达力有上限。它抽不了"字段要拼接或清洗"（日期只在 URL 路径里）、"条目要过滤"（跳过 sponsored/置顶）、"数据在全局变量里不在 DOM 里"、"需要点加载更多"、"shadow DOM"这几类站。

上限比原设计估的低——现有两个标定过的站里已经有一个逼近它：`claude.com/blog` 把同一批文章渲染两遍（网格版可见、列表版藏在 `hidden` tabpanel 里），靠"把 item 限定到某个容器内"才绕过去。更硬的反证：**browser-fetch 自己已有的四个抽取器（generic / wechat / arxiv / youtube）没有一个能用 selector 表达**，全是手写 JS。

**当前进度**：设计稿和实施计划都已写完并经用户确认。**代码一行未写。** 分支 `doc/site-rules-tiers`，其上三个 commit 全是文档：

```
b1b972f docs(plan): site_rules 三档实施计划，分两阶段
646075e docs(spec): site_rules 三档抽取设计
（外加本交接文档）
```

**下一步**：按 `docs/superpowers/plans/2026-09-03-site-rules-tiers.md` 逐任务执行 Task 1 到 Task 8.5，然后停。

---

## 关键决定（别改动）

以下是用户在设计阶段**逐个明确选定**的，不要重新纠结或推翻。每条附上被否掉的选项，免得你以为那些还是开放的。完整论证在 spec，这里只列不可动摇的结论。

| 决定 | 否掉了什么 |
|---|---|
| **三档全要，selector 是默认** | 否掉了"只做 selector"和"直接全上 JS"。selector 能做的站就必须用 selector |
| **JS 存成独立 .js 文件，一条规则一个目录** | 否掉了"内联进 JSON 字符串"和"单文件混合格式"。内联的代码读不了、diff 不了、linter 跑不了 |
| **二档 transform 在 `about:blank` 隔离上下文求值** | 否掉了"在目标页面里跑"。**这是分级的支点**——若 transform 在目标页面跑，它能力等同全 JS，"二档可自动、三档要人批"就只是输入变干净了、能力没变 |
| **三档只能由人发起，自愈上限是二档** | 否掉了"全交给 Agent 管"和"自动生成但标 pending"。自愈是无人值守的（`/loop`、`schedule`），不能让它在没人看着时写 JS 并执行 |
| **三档评审由独立 subagent 做，用户批准的是评估意见不是代码** | 否掉了"用户逐行审 JS"和"命令发起即算批准"。**写 JS 的 Agent 不能给自己签字**——理由同 handoff 里"`已验收` 只能由第二方写" |
| **归一化挪到 Python 侧，在 JS 边界之外** | 否掉了"注入 helper 让 JS 调用"这种约定式做法。约定绕得过，位置绕不过 |

两条来自设计推导，同样已定：

- **`mode` 显式存在 rule.json 里，不靠"有没有那个 .js 文件"隐式判定。** 不一致就报规则损坏，**不静默降级**——静默降级意味着删掉一个 `.js` 就能让高档规则悄悄退成低档继续跑，而摘要上看不出异常。
- **归一化里的 `urljoin` 是为了兜住相对 URL。** 游标（`seen_urls`）和归档去重都拿 URL 当主键，一批相对 URL 会被当成全新条目、永远去不了重，且摘要上完全正常。这是会静默破坏增量语义的正确性陷阱，不是风格问题。

---

## 范围铁律

### IN（阶段一 = 计划 Task 1–8.5）

- `browser_fetch/normalize.py`（新增）、`site_rules.py`（改写）、`core.py`（局部）、`cli.py`（追加参数）
- `skills/feed/sync-website/scripts/articles_client.py`、`SKILL.md`（calibrate 小节）
- 对应测试

逐文件的职责与逐步骤的代码在计划的 **File Structure** 表和各 Task 里，本文档不重抄。

### OUT —— 碰了就是超范围

- **阶段二（Task 9–14）不做。** 计划 Task 8.5 Step 4 是硬停：交付阶段一后**停下来报告，不要自动开始阶段二**。理由是 spec §10 的产品判断——目前 2 个站、0 个真的需要三档，样本量支撑不了现在就做。是否继续由用户决定。
- **不改 `dispatch_site()`**，不改 browser-fetch 已有的四个抽取器。
- **不改 `core.py` 里 `fetch_page` / `fetch_article` / `fetch_user_timeline` / `fetch_channel_videos` / `evaluate_js` 的签名或行为。**
- **不改共享设施的签名或语义**：`_get_context(key)`、`_profile_key()`、`config.get_default_chrome_profile(_data_dir())`、`extract_cookies()`。**需要改它们才能实现 = 设计走偏，停下来回报，不要顺手改。**
- **一档抽取结果必须逐字不变。** 一档模板里的 `linkEl.href` 保留不动（`urljoin` 对绝对 URL 幂等，所以无条件跑它不改变一档行为）。
- **除第 6 条锚点点名的那一处外，不改任何已有测试。** 其余已有测试若失败，是隔离被破坏，**停下来回报，不要改测试去迁就实现**。
- **skill 的 `scripts/*.py` 只能 import 标准库和同目录模块**，不得引入第三方包。browser-fetch 侧不受此限。
- 不碰 `roster`、不碰 pacing（`timeline_pace.json`）、不动 `tools/browser-fetch-mcp/`（已知是源码已空的遗留死代码）。

---

## 相关文档索引

| 路径 | 是什么 |
|---|---|
| `docs/superpowers/plans/2026-09-03-site-rules-tiers.md` | **逐任务执行依据。** 14 个任务含完整测试代码与实现代码。开头的 Global Constraints 与 File Structure 先读 |
| `docs/superpowers/specs/2026-09-03-site-rules-tiers-design.md` | **设计权威。** §2 三档与执行环境、§3 存储 schema、§7 复用边界（登录态 vs 归一化）、§9 代价、§10 判断、§11 把握度 |
| `docs/superpowers/specs/2026-09-02-sync-website-design.md` | 前置设计。其 §3.2 被本次取代，**其余小节仍然有效**（游标晚推、digest、归档、自愈可见性） |
| `docs/commute/2026-09-02-sync-website-handoff.md` | 上一轮交接与验收记录。看它了解 sync-website 现在为什么长这样 |
| `docs/reference/testing-guide.md` | **写新测试前必读** |
| `docs/reference/git-workflow.md` | 分支规范全文（自动生成，勿手改） |

计划 Self-Review 末尾列了**三条计划自身的弱点**，开工前扫一眼：Task 13 是唯一没给逐行代码的任务（属阶段二，本次不做）；`_swap_dir` 的中断点没有测试覆盖；Task 7 有条测试对 `conftest.py` 的数据目录布局有隐式依赖。

---

## 工作流约定

- **先从 `doc/site-rules-tiers` 切出 `feature/site-rules-tiers`，在它上面做。** spec、plan 和本文档都只在 `doc/site-rules-tiers` 上，还没合进 staging——从 staging 切会看不到它们。（想改成常规的"先合 staging 再切 feature"也行，但那需要用户点头，不要自己合。）
- `main` / `staging` 由 `.githooks/pre-commit` 禁止直接提交。
- **只在用户明确说「合并/完成」时才 merge 到 staging**，合并一律 `--no-ff`。
- commit-msg hook 强制 Conventional Commits，类型限 `feat | fix | chore | docs | refactor | test | style | perf`。**是 `docs` 不是 `doc`**——写 `doc(...)` 会被 hook 拒绝。首行 ≤ 80 字符，也是 hook 强制的。**分支前缀反过来是 `doc/` 不是 `docs/`**，两边不一致，原 session 两条都踩过。
- 计划里每个 Task 的最后一步都是 commit，按它给的 message 提交，不要攒成一个大 commit。
- 执行方式建议 `superpowers:subagent-driven-development`（每任务一个全新 subagent，任务间 review）；用 `superpowers:executing-plans` 批量执行也可以。
- `npm test` 耗时 > 2 分钟，`tools/browser-fetch` 的 pytest 约 2 分钟（含真实浏览器抓取）。别当成卡死。

---

## 开工前先做的一件事

**动手前先各跑一遍拿到你自己的基线，别直接信下面的数字**（原 session 2026-09-03 实跑）：

```bash
cd tools/browser-fetch          && .venv/bin/pytest -q   # 175 passed
cd skills/feed/sync-website     && python3 -m pytest tests -q   # 80 passed
cd tools/roster                 && .venv/bin/pytest -q   # 140 passed
npm test                                                  # 328 tests / 321 pass / 0 fail / 7 skipped
```

如果你拿到的数字跟这里对不上，**先停下来报告**再动手——那说明工作区状态跟交接时不一致，后面所有"只增不减"的判据都会失去意义。

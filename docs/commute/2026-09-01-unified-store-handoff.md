# 交接：统一四个 skill 的存储契约（设计已定稿，待拆计划并实现）

**日期**：2026-09-01
**author 模型**：Opus 5
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：设计已经跟用户逐项敲定并写成 spec 提交，接手方从这里往下走完剩余流程——请用户过一遍 spec，然后用 writing-plans 拆实施计划并落地实现。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」章节开工。**完成后把上面的状态置为「待验收」并停在这里**——`已验收` / `打回` 由原 session 按「最小验收锚点」判定后写，不要代填。你的自测结果写成独立小节，别写进原 session 的验收记录里。

---

## 最小验收锚点

实现完成后，下面每条都必须实跑通过。逐条对/错，无中间态。

1. `npm test` 全绿。
2. 四个 skill 目录下都有 `scripts/store_config.py`，且各自 `python3 scripts/store_config.py check` 在 `knowledgeRoot` 缺失时打印 `MISSING:` 开头的信息并 exit 1，配置齐全时打印 `OK: <绝对路径>` 并 exit 0。
3. `grep -rn "VAULT_PATH" skills/research/clip-url/` 只命中注释、文档或迁移路径说明，**不再有任何读取该字段并据此拼产物路径的代码**。
4. `grep -rn 'get_data_dir() / "tweets"\|get_data_dir() / "youtube"' skills/feed/` 无结果（spec §5.3 的四个调用点全部改完）。
5. `grep -n "def data_dir" skills/feed/sync-xtimeline/scripts/roster_client.py skills/feed/sync-ytchannel/scripts/roster_client.py` 无结果，同时 `grep -n "def channels\|def get_cursor\|def set_cursor\|def set_error"` 两个文件各命中 4 处（只删 `data_dir()`，其余保留）。
6. `bash scripts/migrate-store.sh` 默认 dry-run 且不产生任何文件系统副作用；在一个同时含 `deadbeef/`（内有 `meta.json`）和 `我的笔记/`（无 `meta.json`）的临时 vault fixture 上，前者出现在"将搬"列表、后者出现在"跳过"列表。
7. `skills-index.json` 中被改动的四个 skill，其 `contentHash` 与 `contentVersion` 已更新。

第 6 条是本次风险最高的一条，单独实跑，不要只靠单测覆盖。

---

## 背景与现状

仓库里六个会长期存东西的 skill，有五个互不相干的存储根和五份互不相干的配置（清单见 spec §1）。结果是没有全量视图、`sync-*` 的产物目录语义错位地挂在 `roster`（名册）名下、`clip-url` 的产物寄居在用户的 Obsidian vault 里跟手写笔记混住。

本次要做的事一句话：**让 skill 只决定"我是什么类型、什么形态"，不再决定"存哪儿"。**

设计已完整写成 spec 并提交（commit `d18a8d7`，分支 `doc/unified-store-design`）。**spec 是唯一权威，本文档不重抄它**——目录布局看 spec §3，根解析看 §4，逐 skill 改动看 §5，迁移看 §6，测试看 §7。

**开工前第一件事**：spec 处于"待用户 review"状态，用户尚未确认通过。先请用户过一遍，重点是 spec §4.2（`store_config.py` 用四份副本而不是新建 tool）、§5.2（learn-video 复制产物而非重指 `WORK_ROOT`）、§6（迁移的目录名过滤规则）。用户确认后再进 writing-plans。

---

## 关键决定（别改动）

这七条都是用户在设计对话里逐项选定的，不是我推导出来的默认值。接手方若不知道，很可能会重新纠结甚至推翻——**要改必须先回问用户**。

| 决定 | 用户的选择 | 被否掉的选项及原因 |
|---|---|---|
| 资源模型 | 类型 × 形态二维矩阵（文章/视频/推文 × 实体/清单） | — |
| 简化的层次 | 只统一存储契约；**skill 数量与内部流程一律不动** | 合并 skill 是独立后续议题，本次不碰 |
| 根目录 | 独立普通文件夹，**跟 Obsidian 无关**，默认 `~/Documents/knowledge` | 否掉了"根就是 vault"和"根是 `~/.hskill/data`" |
| clip-url 去向 | 整体迁出 vault，`VAULT_PATH` 退休 | 否掉了"留软链"和"clip-url 不动" |
| 实体目录内部 | **保留各自现有结构**，不统一阶段命名 | 否掉了"拍平"和"统一 raw/derived" |
| clip-url 分流 | **不分流**，产物一律算文章实体，x.com 的 URL 也进 `articles/` | 矩阵的"推文 × 实体"格因此为空，这是有意的 |
| 范围 | 只做矩阵里的四个 skill | `learn-paper` / `fetch-paper` / `pdf-math-translate` / `learn-skill` / `survey-skillrepo` 明确不动 |
| 根解析机制 | 方案 B：`~/.hskill/config.json` 加 `knowledgeRoot`，四份 `store_config.py` 副本 | 否掉了方案 A（新建 store tool，抬高安装门槛）和方案 C（roster 的 `DATA_DIR` 升格，固化语义错位） |
| 历史数据 | 一次性全部搬过去，去重索引和归档跟着走 | 否掉了"只搬 clip-url"和"只对新数据生效" |

---

## 范围铁律

**In**：`clip-url`、`learn-video`、`sync-xtimeline`、`sync-ytchannel` 四个 skill 的存储落点改造；新增 `scripts/migrate-store.sh`；`~/.hskill/config.json` 新增 `knowledgeRoot`。

**Out**（spec §8 有完整清单，这里点名最容易被顺手做掉的几条）：

- 不动 `learn-paper` / `fetch-paper` / `pdf-math-translate` / `learn-skill` / `survey-skillrepo`——它们各自的根保持原样，**即使你觉得顺手就能一起收进来**。
- 不改 `vdl`。它在 `~/Projects/Video-Learner`，是**另一个仓库**，本次零改动。learn-video 走"跑完复制产物出来"，不要去改 `WORK_ROOT`。
- 不新增索引文件（`index.jsonl` 之类）。`find <ROOT> -name meta.json` 就是全量清单，这是有意的设计。
- 不统一实体目录内部结构。`Origin/` 与 `transcript/` 的差异保留。
- 不为 Obsidian 保留兼容层——软链、双写都不做。
- 不改任何 skill 的抓取契约、翻译流程、去重算法、游标语义。

---

## 相关文档索引

| 路径 | 作用 |
|---|---|
| `docs/superpowers/specs/2026-09-01-unified-store-design.md` | **本次唯一权威设计依据**，八节完整 |
| `docs/superpowers/specs/2026-08-30-sync-timeline-output-alignment-design.md` | 两个 sync skill 现行输出格式的由来，改 `digest`/`archive` 前先看 |
| `docs/superpowers/specs/2026-08-26-creator-channel-registry-design.md` | `registry.json` / `state.json` 契约，本次不改但会读到 |
| `CLAUDE.md` | 仓库定位、skill 结构约定、`skills-index.json` 的登记要求 |
| `docs/reference/git-workflow.md` | 分支模型全文（自动生成，勿手改） |
| `docs/reference/testing-guide.md` | **写新测试前必读** |
| `scripts/migrate-data-dir.sh` | 本仓库既有的一次性迁移脚本（57 行），`migrate-store.sh` 照它的形状写：`set -euo pipefail` + `ok/info/warn` 三个输出函数 + 逐项幂等判断 |

---

## 受影响文件/落点

spec §5 有逐 skill 的改动说明，这里只给动手前的影响面清单。

**新增（四份内容相同的副本）**
- `skills/research/clip-url/scripts/store_config.py`
- `skills/research/learn-video/scripts/store_config.py` ← 注意：learn-video 目前**没有** `scripts/` 目录，需要新建
- `skills/feed/sync-xtimeline/scripts/store_config.py`
- `skills/feed/sync-ytchannel/scripts/store_config.py`
- `scripts/migrate-store.sh`

**改动**
- `skills/research/clip-url/scripts/vault_config.py` — `get_vault_path()` 改为委托 `store_config.articles_dir()`。下游 `dedup_check.py` / `article_meta.py` / `write_meta_and_separate.py` 全部经由它拿路径，**一行不用改**。
- `skills/feed/sync-{xtimeline,ytchannel}/scripts/config.py` — 改为向 `store_config` 要本渠道目录。
- 四个调用点去掉中间那段渠道名，逐处见 spec §5.3 的表：`sync-xtimeline/scripts/archive_tweets.py:25`、`render_digest.py:85`、`sync-ytchannel/scripts/archive_videos.py:25`、`digest.py:67`。
- 两份 `roster_client.py` 各删 `data_dir()`，**其余四个函数保留**（`channels` / `get_cursor` / `set_cursor` / `set_error` 被 `fetch_new_*.py` 和 `archive_*.py` 广泛调用）。
- 四个 `SKILL.md` 的「初始化」「边界」「参考文件」小节。
- `skills-index.json` 四个条目的 `contentHash` / `contentVersion`。

**learn-video 特别说明**：它现在完全没有自己的脚本，全靠调 `vdl` CLI 再从终态 JSON 读路径。本次要给它加第一段真正的本地逻辑（归档 + 写 `meta.json`），这是四个 skill 里改动形态最不一样的一个，拆计划时单独成组。

---

## 工作流约定

- 分支模型 `main <- staging <- {feature,fix,chore,doc}/*`。`main` / `staging` 由 `.githooks/pre-commit` 禁止直接提交。
- **commit-msg hook 强制 Conventional Commits，有效类型只有 `feat|fix|chore|docs|refactor|test|style|perf`。** 注意是 `docs` 不是 `doc`——我第一次提交就被这条拒了一次。
- 合并一律 `--no-ff`。
- 一个迭代用一个分支累积所有改动，**只在用户明确说"合并/完成"时才 merge 到 staging**。
- **本次分支建议**：spec 在 `doc/unified-store-design`（已提交，未合并）。实现代码不该落在 `doc/*` 分支上，建议从它拉出 `feature/unified-store` 承载实现，最终两条一并合进 staging。这是建议不是既定事实，**开工前跟用户确认一句**。
- 拆计划用 `superpowers:writing-plans`，执行用 `superpowers:executing-plans`。

---

## 验证步骤

1. `npm test` —— 覆盖 hskill CLI 行为与所有 `SKILL.md` 的格式校验。改了 `SKILL.md` 就一定会被这条覆盖到。
2. 写新测试前先读 `docs/reference/testing-guide.md`，不要凭现有测试的样子推测约定。
3. spec §7 有逐对象的用例表（`store_config` / `clip-url` / `migrate-store.sh` / `sync-*` / `learn-video`），按它写。
4. 迁移脚本必须在**临时 fixture 目录**上验证，不要拿用户真实的 vault 试——这是不可逆操作。

---

## author 冷读核对

- 交接目的、最小验收锚点：均在。
- 「相关文档索引」7 条路径逐个 `ls` 核对存在，无死链。
- 附带发现（**不在本次范围内，仅记录**）：`CLAUDE.md` 提到的 `scripts/git/install-git-hooks.sh` 实际不存在，`scripts/` 下只有 `generate-npmignore.js` / `migrate-data-dir.sh` / `run-skill-tests.sh`。这是一条已有的文档陈旧问题，跟本次改造无关，别顺手修。
- 最小验收锚点 7 条均为可证伪的命令级判据，无"让它工作"式软标准。
- 反向检查：唯一犹豫过要不要写的是「资源模型矩阵」本身。最终没有单开章节——它完整躺在 spec §2，而「关键决定」表首行已经点明它是既定前提，接手方不会因此走错。

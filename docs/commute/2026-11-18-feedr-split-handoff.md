---
status: 已验收
date: 2026-11-18
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/feedr-split
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+feedr-split
source_node: bff513bf-17b1-42fc-9f98-318247cfa724
target_node: 36bcaf49-36d9-43ae-abad-411a1c3ab274
---

# 交接：按已批准的计划把 browser-fetch + roster 拆成独立产品 feedr

**交接目的**：接手方在全新会话中执行已获用户确认的实施计划（Task 1–13，以及 Task 14 中不依赖合并的步骤），交出方据此验收。

---

## 背景与现状

- 用户要把 harveyz-skill（hskill）收窄为只管理 skill 的仓库，把工具迁出去。本轮迁出 browser-fetch 和 roster，再加上三个 sync-* skill 里的追更编排，合成独立产品 **feedr**，单仓库、单 CLI。
- Spec 与计划都已由用户批准，并提交在本分支上（计划提交为 `e112766`）。
- 新仓库 `/Users/harveyzhang96/Projects/feedr` **尚不存在**，由计划 Task 1 创建。
- 交接工作区目前只有 Spec、决定记录、计划和本文档，还没有任何代码改动。

## 关键决定（别改动）

执行技能：**`superpowers:subagent-driven-development`**，已写在计划开头的 `REQUIRED SUB-SKILL`。
- 选择理由：执行方是全新会话；计划有 14 个可以单独审查的任务，各自有测试周期，适合逐任务派子代理并做两阶段审查。

权威依据是 Spec 和计划，下列内容都以它们为准：
- **不得修改：** 接口签名、测试名称与断言、计划中的 `Global Constraints`。
- **可以自行决定：** 函数内部怎么实现。
- **冲突就打回：** 计划与代码库现状冲突或无法照做时，停下来打回交出方。任务审查者提出的意见如果涉及上述不可修改项，同样打回，不要自行裁决。

已定方案的要点（细节见 Spec，不要重新讨论）：
- 一个 CLI，五组命令：`fetch`、`roster`、`sync`、`init`、`config`。
- 追更是两段式：`sync fetch` 不推进游标；`sync commit` 写存档后再推进游标。
- 数据放在 `~/.feedr/`，只从 `~/.hskill` 复制，不删除。
- 存档的位置和格式与旧实现逐字节一致。

## 范围铁律

**做：**
- 计划中的 Task 1–13。
- Task 14 的 Step 1、2、3、4、6。这几步在真实 HOME 上运行 `feedr init`，只复制、不删除，计划允许在这一步做。

**不做：**
- **Task 7 Step 7（在 GitHub 公开建仓并推送）：** 不要自己执行。停下来告诉用户，由用户确认后才做；用户没回应时，在自测记录里写明「未执行，待用户确认」。
- **Task 14 Step 5、Step 7：** 要先合并、部署才能做，由交出方在验收合并后完成。
- **合并到 `staging`：** 不做，只有交出方能合并。
- **任何删除工作区或分支的命令：** 不做。
- **feedr 仓库也不合并：** 所有工作留在 `feature/initial-split` 分支上，不并回 `main`。
- **收藏夹同步、PyPI 发布：** 不做，属于未决的 D21、D22。
- **本地残留的 `tools/browser-fetch-mcp/`：** 未被 git 跟踪，不要动它。

## 相关文档索引

所有路径都相对于交接工作区：
- Spec（v0.1，已批准）：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-spec.md`
- 计划（用户已确认）：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-plan.md`
- 决定记录：`.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-record.md`
- 仓库规则：`AGENTS.md`、`docs/reference/git-workflow.md`、`docs/reference/testing-guide.md`

## 工作流约定

本仓库的 handoff 约定见 `.hskill/handoff/config.md` 的 `workflow` 段，按那里的规则进入工作区并核对。

**一个工作区，两个仓库：**
- Task 8–13 在交接工作区里做，提交到 `feature/feedr-split`。提交类型用 `feat`、`chore`、`docs`、`test`、`refactor`，hook 不接受 `doc`。
- Task 1–7 在 `/Users/harveyzhang96/Projects/feedr` 里做。feedr 是全新仓库，没有 hooks。

**在 Claude Code 中跨仓库操作 git：** 进入 worktree 后，宿主会拒绝路径在运行时才确定的跨仓库 git 命令（例如 `git -C ~/Projects/feedr`、带变量的 `cd`）。对 feedr 执行 git 一律写字面绝对路径：
```
git -C /Users/harveyzhang96/Projects/feedr <命令>
```
交出方实测过：对另一个仓库用字面绝对路径执行 `git -C` 可以通过。如果仍被拒绝，先用 `ExitWorktree(action: "keep")` 离开 worktree，做完 Task 1–7，再按 `manage-worktree` 的「进入」回到交接工作区做 Task 8–13。

**真实数据：** Task 14 之前，不得在真实 HOME 下执行 `feedr init` 或任何会读写浏览器数据的 `feedr fetch`。测试一律设置临时的 `FEEDR_HOME` 和 `HOME`。

## 最小验收锚点

以下各条全部为硬判据：

1. **各 Task 的测试：** 与计划写定的测试名称和断言一致，并全部通过。
   - feedr：`/Users/harveyzhang96/Projects/feedr/.venv/bin/pytest -q` 退出码为 0，没有 xfail 和 skip，只有依赖真实浏览器的用例按 conftest 跳过时例外。
   - harveyz-skill：交接工作区内 `npm test` 退出码为 0。
2. **Spec 第 12 节验收标准第 1–7 条和第 9–11 条逐条满足。** 其中第 6、7 条由 Task 14 Step 3、4 的记录证明，记录在 `.hskill/spec/2026-11-17-feedr-split/2026-11-17-feedr-split-cutover.md`。
3. **Spec 第 12 节第 8 条不在本次交接范围内**，由交出方在合并、部署之后完成。
4. **Task 13 Step 1 的 grep 没有输出；Task 13 Step 5 的 `npm pack --dry-run` 过滤结果为空。**
5. **feedr 仓库：** 首个提交在 `main` 上，只包含 `.gitignore`；其余提交都在 `feature/initial-split` 上；没有 harveyz-skill 的历史（`git -C /Users/harveyzhang96/Projects/feedr log --all --oneline` 中看不到 harveyz-skill 的提交）。
6. **Task 7 Step 7：** 要么没有执行，自测记录写明「待用户确认」；要么附上用户确认的原话后才执行。

---

## 接手方自测记录（2026-11-18）

被验代码：feedr `feature/initial-split` @ `2c379b3`；harveyz-skill `feature/feedr-split` @ `3895ec5`（自测前最后一个提交）。执行技能 `superpowers:subagent-driven-development`：每个 Task 一个实施子代理 + 一次任务审查（规格+质量），全部 Task 完成后一次全分支终审（opus）和一次范围受限的修补复审。逐锚点实跑如下，判成败的命令均未接管道。

### 锚点 1　各 Task 的测试

| 命令 | 结果 |
|---|---|
| `cd /Users/harveyzhang96/Projects/feedr && .venv/bin/pytest -q` | **pass**，退出码 0，`550 passed in 71.81s`，无 xfail、无 skip |
| `cd <交接工作区> && npm test` | **pass**，退出码 0，490 个测试：483 pass / 0 fail / 7 skipped（这 7 个是仓库既有的跳过，与本分支无关） |

### 锚点 2　Spec 第 12 节 AC1–AC7、AC9–AC11

| AC | 结论 | 证据 |
|---|---|---|
| 1 | pass，带说明 | feedr 为独立仓库，无 harveyz-skill 历史（见锚点 5）；pytest 全绿。**删减的用例不止 launcher 类**（roster 的 `test_migrate.py` 与 init 相关用例、sync 子进程/参数拼装断言、`probe_articles/set_rule` 模式白名单 4 例），理由与清单在 feedr `README.md`「迁移说明」；S12 要求的旧编排测试已逐个迁移或标注由 golden 覆盖（见各 Task 报告）。**这超出了 S11 只许删 launcher 测试的字面规定，需要交出方/用户签认。** |
| 2 | pass | `feedr --help` 列 init/config/fetch/roster/sync；`feedr fetch --help` 列 9 个旧子命令 + `install-browser`；`feedr --version` = 0.1.0（`tests/test_cli_surface.py`） |
| 3 | pass | §6.2 每条分支及 S13 两种情况、`NOT_INITIALIZED`、`MISSING_ARCHIVE_ROOT` 均有测试；init 测试带 `~/.hskill` 快照断言。遗留：roster/sync 的 `NOT_INITIALIZED` 门槛测试未加快照（只断言不建目录） |
| 4 | pass | 18 个 golden 场景（x 5、youtube 5、website 8）全部逐字段/逐字节通过。终审发现计划的 Task 4 清单漏了 website 的 `handle_not_on_roster`（Spec S15 要求每个平台都有），已补上，并用从 `a7bf7f8` 导出的旧脚本生成，原 17 个场景字节不变 |
| 5 | pass | 只执行 fetch 游标不动、重复 commit 幂等、存档写失败游标不动，均有测试；隔离环境下实测一遍 |
| 6 | pass | Task 14 Step 3：`registry list`、`profile get`、`articles-rule list` 与旧工具基线逐字节无差异，名册目录 `diff -rq` 无差异（记录见 cutover.md） |
| 7 | pass，带前置条件 | Task 14 Step 4：`feedr fetch timeline https://x.com/trq212 --max 5` 退出码 0，返回 5 条推文，没有要求重新登录。**未单独验证该账号有登录墙内容。** 另见下面「钥匙串授权」 |
| 9 | pass，带 4 处说明 | `npm test` 通过；残留检查见锚点 4 |
| 10 | pass | `npm pack --dry-run` 无 `tools/browser-fetch`、`tools/roster`；`skills-index.json` 无 `research-tools`；两个 tools 目录已删除，`tools/` 其余内容未动 |
| 11 | pass | 六个 skill（sync-xtimeline/ytchannel/website、clip-url、manage-creators、capture-opinion）的检查步骤都是 `command -v feedr`，找不到时给出 `feedr 未安装：uv tool install git+https://github.com/harveyzhang96/feedr && feedr fetch install-browser` 并终止；`env PATH=/usr/bin:/bin sh -c 'command -v feedr \|\| echo MISSING'` 输出 `MISSING` |

### 锚点 3　AC8

不在本次交接范围，未做。

### 锚点 4　Task 13 的 grep 与 `npm pack`

- **`npm pack --dry-run` 过滤结果为空：pass**（退出码 0，匹配数 0）。
- **Task 13 Step 1 的 grep 没有输出：未达成，带着这条红送验。** 用只扫已跟踪文件的 `git grep`（macOS 的 BSD grep 的 `--exclude-dir` 不可靠，会扫进 `.hskill/` 文档）复跑，共 6 行命中、分布在 4 个文件：
  - `skills/research/clip-url/scripts/store_config.py:4`、`skills/research/learn-video/scripts/store_config.py:4`：注释里提到 `browser_fetch_locate.py`（“四份内容相同的副本”那句历史说明）。
  - `tools/hub/tests/test_launcher_python_version.py:3,9`、`tools/sync-agent/tests/test_launcher_python_version.py:3,9`：文档字符串写“在 browser-fetch 上复现并修复”。
  - **归因证据：** 这 4 个文件在分叉点 `a7bf7f8` 上同样命中同样的行（`git grep` 两边结果逐行相同），不是本分支引入。
  - **为什么没改：** 计划 Task 12 明确写 `store_config.py` “不动”（Spec S5/§8 同），hub 与 sync-agent 不在迁出范围（D3）。这与 Task 13 Step 3 “没有输出”的预期在计划内部冲突；Spec AC9 允许“其他例外须逐条说明”，故逐条说明而不是改文件。**请交出方裁定是接受这 4 处例外，还是授权改注释。**
- 另：`scripts/migrate-store.sh`、`tests/migrate-store.bats`、`CHANGELOG.md` 按 S14 不动，按计划被排除在 grep 之外。

### 锚点 5　feedr 仓库结构

- `main` 只有一个提交 `6275064 chore: init repo`，只含 `.gitignore`；其余 14 个提交都在 `feature/initial-split` 上；没有 remote。
- 任何提交都没有 `skills/`、`tools/`、`docs/`、`.hskill/` 或 `SKILL.md` 路径，提交主题里的 `hskill` 字样只出现在 `~/.hskill` 目录名里：没有 harveyz-skill 的历史。

### 锚点 6　Task 7 Step 7

**未执行，待用户确认。** 没有运行 `gh`，没有 `git push`，feedr 没有 remote；README 里的 GitHub owner 与安装文案是占位，建仓时确认（S9、D23）。

### 需要交出方/用户知道或决定的事

1. **钥匙串授权会让命令卡住（Task 14 Step 4 发现，影响 AC8）。** 读 Chrome cookie 前，`pycookiecheat` 要读钥匙串 “Chrome Safe Storage”；新的 `~/.local/share/uv/tools/feedr/bin/python3` 是另一个可执行文件，需要重新授权。第二次抓取时进程在弹窗前挂住（已观察到 `SecurityAgent` 进程，CPU 0%，无子进程），第一次的约 16 分钟等待同因（推断）。我没有替用户点击弹窗，已结束测试进程。AC8 与任何定时运行之前，需要用户先手动跑一次 `feedr fetch timeline …` 并选「始终允许」；重装 feedr 是否再次触发**未核实**。系统里可能还留着一个钥匙串弹窗，取消即可。详见 cutover.md。
2. **产品决定 R7（超出 Spec 字面）：** clip-url 的自我优化流程原来改的是本仓库里的 browser-fetch 代码，现在代码在 feedr 仓库，所以主会话要向用户要一份本地 feedr checkout 路径（`<FEEDR_REPO>`），没有路径就放弃（`GAVE_UP`）；子代理只提交分支并回报，不重装全局 feedr；修复只在 editable 安装或用户重装后才对重试生效。需要确认这个产品行为。
3. **计划与 Spec 的偏差及处理（已写入各任务审查记录）：**
   - R1：计划要求提交署名 `Claude Opus 5.5`，实际执行模型是 Sonnet，署名改为 `Claude Sonnet 5.5`（含 Global Constraints 里这一条的改动，请确认）。
   - R3：补迁 golden 未覆盖的旧编排测试（Spec S12）。
   - R4：计划断言 `main(["roster","init","x"]) == 2`，起初实现是抛 `SystemExit`；按计划字面修成让 `feedr.cli.main` 总是返回 int。
   - R5：website 的坏游标/缺 `url` 条目现在按渠道记 `failures`（旧版会让整轮崩溃）；README「刻意的差异」已写。
   - R9：`tests/skill-portability.test.mjs` 钉死三个 sync-* 旧版本号，计划漏了，已更新三处。
   - R10：补 website `handle_not_on_roster` golden（Spec S15）。
4. **安全事件披露：** Task 8 的实施子代理在红灯阶段先删掉了测试隔离，导致一个测试摘要 `digest-20260815T090000.md` 被写进**真实**的 `~/knowledge/feeds/tweets/digest/`，随后它只删了这一个文件（文件名与测试夹具写死的 `run_time` 吻合，目录里其余 53 个真实摘要未动）。此后所有任务的测试都在临时 HOME 下运行。
5. **进程内追更与旧版的差异（自动测试覆盖不到，AC8 人工验收时留意）：** sync 现在在一个进程里依次跑所有渠道，共用同一个 Playwright persistent context；`run_fetch` 开头读一次 state，失败时整份写回，运行期间若有并发的名册修改可能被覆盖。
6. **全局 feedr 是非 editable 快照：** `~/.local/bin/feedr` 是 `2c379b3` 的构建，feedr 代码再改要 `uv tool install --force --reinstall /Users/harveyzhang96/Projects/feedr`（只 `--force` 会复用缓存的旧 wheel，已踩过）。
7. **过渡期风险（Spec §9）：** `~/.feedr` 已初始化；skill 部署前不要运行旧版 sync-*、manage-creators、capture-opinion，否则 `~/.hskill/roster` 与 `~/.feedr/roster` 的游标会分叉。
8. **留给交出方的步骤：** Task 14 Step 5 与 Step 7（合并、部署 6 个 skill、核对版本、手动跑一轮并记入 cutover.md）、AC8、合并到 `staging`、Task 7 Step 7；`tools/browser-fetch-mcp/`（未被跟踪，不在本工作区）未动。
9. **SDD 暂存目录保留：** `.superpowers/sdd/2026-11-17-feedr-split-plan/`（被 git 忽略）里有每个 Task 的简报、报告、审查包和账本（含全部裁定与推迟的 Minor）。验收前我没有删它，方便验收方查证；验收后可 `rm -rf`。

### 推迟未修的 Minor（终审分级为“可不修”，详见账本）

非 UTF-8/损坏之外的边角：`browser_dir()` 并发首次运行竞态、sync commit 先读 stdin 后过初始化门槛（stdin 非法 JSON 退出码 2）、golden 不比字段顺序、两个 init 之外的门槛测试没做 `~/.hskill` 快照、`bool` 被当作 int 退出码、clip-url `SKILL.md:178` 仍写“四份副本”、41efc5e 单独检出时 `npm test` 因版本钉未改而失败（86ce0bb 已修，仅影响 bisect）。

## 交出方验收记录（2026-11-18，第 1 轮，未完结）

在交接工作区（`feature/feedr-split` @ `2f69a7e`）与 feedr（`feature/initial-split` @ `2c379b3`）上逐条自己重跑，不采信自测结论。

| 锚点 | 结果 | 实跑 |
|---|---|---|
| 1 | pass | feedr `.venv/bin/pytest -q`：退出码 0，`550 passed`，无 xfail/skip；交接工作区 `npm test`：退出码 0，490 tests / 483 pass / 0 fail / 7 skipped（既有跳过）。计划写定的 10 个关键测试名逐个 grep 存在，`test_fetch_without_archive_root_calls_no_fetch` 断言 `stub_fetch.calls == []` |
| 2 | 部分完成：AC1–6、9–11 pass；AC7 待重跑 | AC2：全局 `feedr --version` 为 0.1.0，`--help` 列出 5 个命令组。AC4：golden 共 18 个场景（x 5 / youtube 5 / website 8），由 pytest 通过证明。AC6：在真实数据上用旧 `~/.local/bin/roster`、`browser-fetch` 与 `feedr` 对比 `registry list`、`profile get`、`articles-rule list`，三组 `diff` 均无差异；`diff -rq ~/.hskill/roster ~/.feedr/roster` 无差异。AC10：`npm pack --dry-run` 匹配数为 0，`tools/` 只剩 archived/hub/skill-harness/sync-agent，`skills-index.json` 无 `research-tools`。**AC7 未重跑**：重跑会触发钥匙串授权弹窗，需要用户在场，见下 |
| 3 | 不在范围 | — |
| 4 | 字面未达成，按例外接受 | `git grep` 有 6 行命中，分布在 4 个文件；在分叉点 `fd60ab4` 上同样命中同样的行（已实跑）。归因：计划要求 `store_config.py` 不动、hub 和 sync-agent 不在范围，这与「grep 无输出」冲突，是交出方写锚点时的遗漏，不是接手方的问题。按 Spec AC9「其他例外逐条说明」接受，不打回 |
| 5 | pass | `main` 上只有 `6275064`（仅 `.gitignore`）；`main..feature/initial-split` 共 14 个提交；没有 remote；全部历史中没有 `skills/`、`tools/`、`docs/`、`.hskill/`、`SKILL.md` 路径 |
| 6 | pass | 没有 remote，没有执行推送 |

**回归面：** 改动面是 `fd60ab4..HEAD` 共 17 个提交，涉及 6 个 skill、`tools/`、`skills-index.json`、`package.json`、`tests/`。`npm test`（含 `run-skill-tests.sh` 中各 skill 的 pytest、`skill-portability` 测试）已覆盖。hub、sync-agent 没有改动。未发现锚点以外的回归。

**交出方对接手方送验事项的裁定：**
- AC1 删减的测试超出了「只删 launcher 测试」的字面：被删的用例对应的层已按已批准的决定移除（S3 移除 `roster init`/`migrate`；D4、S6 去掉 subprocess 和 locate 层）。接受，不打回；Spec 写法过窄，责任在交出方。
- R1（提交署名改为 Sonnet）：接受，署名与实际执行模型一致。
- R5（website 遇到坏游标时改为按渠道记入失败，旧版会整轮崩溃）：接受，只影响失败路径，并已写入 README。
- R7（clip-url 自我优化流程需要本地 feedr checkout 路径）：**产品行为，交给用户裁定。**
- 误写真实摘要文件的事件：已核对，`~/knowledge/feeds/tweets/digest/` 现有 53 个文件，与接手方的陈述一致。

**未完结项（status 暂不改）：** AC7 重跑（需要用户在钥匙串弹窗中授权）；R7 由用户裁定。

### 第 1 轮补完（2026-11-18）

- **AC7：pass。** 用户在钥匙串弹窗中授权后，交出方重跑 `feedr fetch timeline https://x.com/trq212 --max 5`：退出码 0，返回 5 条推文（最新一条 id 为 `2122438328079524159`），stderr 为空，没有要求重新登录。
- **R7：** 用户选择「接受现状」。
- **结论：锚点 1、2、4、5、6 全部达成（锚点 4 按例外接受），锚点 3 不在范围。status 置「已验收」。**
- **留给交出方：** 合并到 `staging`、部署 6 个 skill、AC8（Task 14 Step 5、7）、Task 7 Step 7（GitHub 公开建仓，需用户确认）。

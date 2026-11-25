---
status: 已验收
date: 2026-11-24
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/capture-feature
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+capture-feature
base_commit: ad8c0438c9071b197dca2a2f3eee55fc7f96ee4d
source_node: 710f0c34-464f-41d2-a735-fac19dd73eb1
target_node: fbb207ec-66bf-47de-9d39-3e1dc31525ed
---

# 交接：按计划实现 capture-feature 与 capture-vocab 1.3.0（Task 1–6）

**交接目的**：接手方在本工作区按已确认的实施计划完成 Task 1–6（新 skill capture-feature 的脚本、文档、capture-vocab 联动、登记发布准备），交回原 session 验收；Task 7 不做。

---

## 关键决定（别改动）

全部决定以 Spec 与决定记录为准，以下是最容易被执行中“顺手改掉”的几条：

- 存储是一个对象一个 JSON 文件（D14），层级用固定字段 `parent`、单父（D12、D17）——不要改成单文件、SQLite 或通用关系列表。
- `aliases` 与 `avoid` 是两个字段，`avoid` 每项 `{name, note}`，都参与匹配（D18）。
- 有功能地图时 capture-vocab 每次 `query` 与 `add` 查重都 **invoke capture-feature skill**（D19），不是让 `vocab.py` 直接读 JSON，也不是调兄弟脚本。因此 capture-feature 的 `SKILL.md` 必须 ≤ 2641 字节、只留查词路径，写操作细节全部放 `references/`。
- 代码线索只记路径 + 可选符号名，不记行号（D13）；`check` 只报告不修复。
- 计划的 `Global Constraints` 里的输出文案、退出码、序列化键顺序、版本号（capture-feature `0.1.0`、capture-vocab `1.3.0`）是验收断言的一部分，逐字遵守。

## 范围铁律

- **in**：计划 Task 1–6。
- **out**：Task 7（合并到 staging、部署到 `~/.claude/skills/`、agent-canvas 试点迁移）——由原 session 在用户说“合并”后做。不碰 agent-canvas 仓库；不改 Spec、决定记录；不改计划中的接口签名、测试名、断言与 `Global Constraints`。计划与代码库现状冲突或无法照做 → 停下，打回原 session（见仓库 AGENTS.md「计划后交接给执行模型」第 3 条）。

## 相关文档索引

- 计划（执行依据，开头 `REQUIRED SUB-SKILL: superpowers:executing-plans`）：`.hskill/spec/2026-11-24-capture-feature/2026-11-24-capture-feature-plan.md`
- Spec v0.1（已批准，权威）：`.hskill/spec/2026-11-24-capture-feature/2026-11-24-capture-feature-spec.md`
- 决定记录：`.hskill/spec/2026-11-24-capture-feature/2026-11-24-capture-feature-record.md`
- 参照实现与测试风格：`skills/coding/capture-vocab/scripts/vocab.py`、`skills/coding/capture-vocab/tests/test_vocab.py`
- skill 格式规范：`docs/reference/skill-spec.md`；测试指南：`docs/reference/testing-guide.md`

## 受影响文件/落点

- 新建：`skills/coding/capture-feature/`（`SKILL.md`、`scripts/feature.py`、`references/manage.md`、`references/migrate.md`、`tests/conftest.py`、`tests/test_put.py`、`tests/test_query.py`、`tests/test_check.py`、`tests/test_skill_doc.py`）
- 修改：`skills/coding/capture-vocab/SKILL.md`、`references/manage.md`、`references/project-setup.md`，新建 `skills/coding/capture-vocab/tests/test_skill_doc.py`
- 修改：`skills-index.json`、`package.json`、`CHANGELOG.md`

## 工作流约定

见 `.hskill/handoff/config.md` 的 `workflow` 段。要点：不建 worktree、不建分支，用 `manage-worktree`「进入」本文 frontmatter 的 `worktree`；提交信息用 Conventional Commits（`docs` 不是 `doc`）；不合并、不 push；做完停手。执行技能若建议新建 worktree，跳过。

## 最小验收锚点

全部为硬判据，在本工作区运行：

1. 计划 Task 1–6 每个 Task 的测试文件存在，测试名与断言与计划写定的一致，且 `python3 -m pytest skills/coding/capture-feature/tests skills/coding/capture-vocab/tests -v` 全部通过（含 capture-vocab 原有 `test_vocab.py` 未被修改）。
2. `npm test` 退出码 0。
3. `wc -c < skills/coding/capture-feature/SKILL.md` ≤ 2641；`wc -l < skills/coding/capture-vocab/SKILL.md` ≤ 47。
4. `skills-index.json` 中 capture-feature 条目存在（`installScope: project`、`contentVersion: "0.1.0"`），capture-vocab `contentVersion` 为 `"1.3.0"`，两者 `contentHash` 等于计划 Task 6 Step 1 命令的输出；`package.json` 的 `files` 含 `skills/coding/capture-feature/`；`npm pack --dry-run` 列出 `skills/coding/capture-feature/SKILL.md` 与 `scripts/feature.py`。
5. Spec §11 第 1–9 条逐条满足（第 10–12 条属 Task 7，不在本次验收）。

## 接手方自测记录（2026-11-24）

在本工作区、分支 `feature/capture-feature` 实跑，判成败的命令均未接管道：

1. **锚点 1 PASS**：`python3 -m pytest skills/coding/capture-feature/tests skills/coding/capture-vocab/tests -v` → 74 passed。capture-vocab 原有 `test_vocab.py` 与 `scripts/` 相对 `ad8c043` 无改动。
2. **锚点 2 PASS**：`npm test` 退出码 0（node 483 pass / 0 fail；custom skill tests 23/23；capture-feature pytest 51 passed、capture-vocab 23 passed）。
3. **锚点 3 PASS**：capture-feature `SKILL.md` 1755 字节（≤2641）；capture-vocab `SKILL.md` 43 行（≤47）。
4. **锚点 4 PASS**：`skills-index.json` 中 capture-feature（`installScope: project`、`contentVersion: "0.1.0"`、hash `62af7656880313d9`）与 capture-vocab（`1.3.0`、`9b6632580ae311fb`）；两个 hash 均按计划公式重算一致；`package.json` `files` 含 `skills/coding/capture-feature/`；`npm pack --dry-run` 列出 `SKILL.md` 与 `scripts/feature.py`（共 15 个文件）。
5. **锚点 5 PASS**：Spec §11 第 1–9 条对应测试均存在并通过。

### 偏离与裁决（供验收方复核）

- **测试文件改名**：计划让两个 skill 各有一个 `test_skill_doc.py`，而锚点 1 把两个目录放进同一条 pytest 命令，pytest 报 `import file mismatch`。把 capture-vocab 的那份改名为 `tests/test_vocab_skill_doc.py`，测试名与断言未动。
- **`dupcheck` / `suggest-parent`**：数据目录不存在但有 `.git` 时按空图处理（`dupcheck` 仍查 vocab），不再 exit 2。原因：首次 `add` 与迁移时 vocab 查重不能失效。偏离 Spec §9 字面，仅这两个命令。
- **capture-vocab `manage.md` 的归属判断**插为「2b」，没有重编号，避免打乱对第 5/6 步的既有引用。
- **整分支审查**（独立 reviewer）发现的 1 条 Critical、4 条 Important 已用先红后绿的测试修复（`tests/test_review_fixes.py`）：损坏或缺字段 JSON 导致 Traceback、校验失败的 `put` 残留数据目录、`put --new` 覆盖文件名与 id 不一致的文件、版本号不可解析的对象写入后使 `list --at` 不可用。
- **延后的 Minor**：`tree --depth` 负数、`schema: 1.0` 通过校验、未知字段被静默丢弃、`code.path` 接受绝对路径或 `../`、别称自身重复不报、`project-version` 对数组型 `package.json` 崩溃与 `pyproject.toml` 取错段、并发写同一 id 共用 tmp 文件名。

无红，无带红送验项。

## 验收记录（交出方，2026-11-24，第 1 轮）

在本工作区、分支 `feature/capture-feature`（HEAD `4940c11`）逐条重跑，未采信自测结论：

1. 锚点 1 PASS：`python3 -m pytest skills/coding/capture-feature/tests skills/coding/capture-vocab/tests -q` → 74 passed；`git diff --stat ad8c043 -- skills/coding/capture-vocab/tests/test_vocab.py skills/coding/capture-vocab/scripts` 为空。
2. 锚点 2 PASS：`npm test` exit 0。
3. 锚点 3 PASS：1755 字节；43 行。
4. 锚点 4 PASS：按公式重算 `62af7656880313d9`、`9b6632580ae311fb`，与 `skills-index.json` 一致；`files`、`bundleMeta`、`npm pack --dry-run` 均符合。
5. 锚点 5 PASS：Spec §11 第 1–9 条均有对应测试且通过。

回归面核对：改动面为 `skills/coding/capture-feature/**`、`skills/coding/capture-vocab/**`、`skills-index.json`、`package.json`、`CHANGELOG.md`、本文档与 spec 目录；被波及组件的既有回归即 `npm test`（含 `tests/skills.bats` 与 `run-skill-tests.sh`），已在第 2 条跑过，绿。`npm pack` 含 `__pycache__` 为既有现象（capture-vocab 同样，已 gitignore），非本次引入。

偏离裁决：测试文件改名——接受；`dupcheck` / `suggest-parent` 无数据目录按空图——接受，交出方将在 Spec 补记次要决定 S16。

### 打回记录

**结论：打回。** 锚点 1–5 实跑均通过，但下列两处与计划 Task 5「Files」所写内容及 Spec §6.2 不符（锚点漏写了对这部分文案的判据，责任在交出方；用户决定按流程打回修正）：

1. **`skills/coding/capture-vocab/references/manage.md` 第 2b 步的触发条件。** 判据原文（计划 Task 5 / Spec §6.2）：在第 2 步后插入归属判断，归功能地图且用户确认 → 停止本流程并 invoke `capture-feature` 的 `add <term>`；无“项目已有功能地图”这一前提。实际：写成「（项目有功能地图时）」，导致尚无 `.hskill/capture-feature/` 的项目永远不会路由，功能地图建不起来。**修法**：条件改为「`capture-feature` 已安装时」（未安装则跳过本步，按原流程继续）；第 1 步“同时 invoke capture-feature 跑 query”的条件保持为“项目有 `.hskill/capture-feature/` 时”不变。
2. **同文件第 5 步三选一未覆盖功能候选。** 第 1 步把命中的功能并入第 5 步，但第 5 步「同一实体两个名字」只写了并进 vocab 的 `_Avoid_`。**修法**：补一句——候选是功能时，改为建议走 `capture-feature` 的 `update`，把新叫法并进该功能的 `aliases` 或 `avoid`。

**复修后重跑范围**：锚点全集 1–5（改动虽只在文档，`capture-vocab` 的 `contentHash` 不受影响但 `npm test` 仍需复跑；若改动波及 `SKILL.md` 须重算 hash）。不得改动已有测试的断言；可为这两处新增文档断言测试（可选）。

## 接手方复修自测记录（第 1 轮）

按打回记录修了 `capture-vocab/references/manage.md` 两处：第 2b 步触发条件改为「`capture-feature` 已安装时；未安装则跳过本步」（第 1 步查重的条件未动）；第 5 步「同一实体两个名字」补上候选是功能时建议走 `capture-feature` 的 `update`，并进 `aliases` 或 `avoid`。先加两条文档断言测试（`test_add_routing_does_not_require_existing_feature_map`、`test_add_three_way_choice_covers_feature_candidates`），确认红（2 failed）后改文案转绿。没有改动任何已有测试的断言。

范围：锚点全集 1–5 重跑（改动只在文档，`SKILL.md` 未动，hash 不变）：

1. **锚点 1 PASS**：两个 tests 目录合跑 `python3 -m pytest … -v` → 76 passed；`test_vocab.py` 与 `scripts/` 相对 `ad8c043` 无改动。
2. **锚点 2 PASS**：`npm test` 退出码 0（node 483 pass / 0 fail；custom skill tests 23/23）。
3. **锚点 3 PASS**：1755 字节 ≤ 2641；43 行 ≤ 47。
4. **锚点 4 PASS**：两个 `contentHash` 重算仍为 `62af7656880313d9`、`9b6632580ae311fb`，与 `skills-index.json` 一致；`npm pack --dry-run` 仍列出 `SKILL.md` 与 `scripts/feature.py`。
5. **锚点 5 PASS**：Spec §11 第 1–9 条对应测试均通过。

无红，无带红送验项。

## 验收记录（交出方，2026-11-24，第 2 轮）

在本工作区（HEAD `eea74c0`）逐条重跑：

1. 锚点 1 PASS：76 passed；`test_vocab.py` 与 `scripts/` 相对 `ad8c043` 无改动。新增两条文档断言测试与打回记录的修法一致。
2. 锚点 2 PASS：`npm test` exit 0。
3. 锚点 3 PASS：1755 字节；43 行。
4. 锚点 4 PASS：hash 重算 `62af7656880313d9`、`9b6632580ae311fb`，与 `skills-index.json` 一致；`npm pack --dry-run` 列出 `SKILL.md` 与 `scripts/feature.py`。
5. 锚点 5 PASS。

打回两处核对：`manage.md` 第 2b 步条件已为「`capture-feature` 已安装时；未安装则跳过本步」，第 1 步条件未动；第 5 步已覆盖功能候选走 `capture-feature` 的 `update`。回归面同第 1 轮，`npm test` 绿。

**结论：已验收。**

## 补充：合并前沙箱 E2E（交出方，2026-11-24）

用户要求合并前补 agent 层面的 E2E。夹具取 `~/Projects/route-work-e2e/fixture-template`（套件仓库只读），运行目录 `/tmp/capture-feature-e2e/run1/`（用后即弃）；两个 skill 取本分支 `HEAD` 的已提交内容装为夹具的项目级 skill；headless `claude -p`（2.1.311），环境按套件 `agentEnv` 去掉画布变量与 CLI，并加 `--setting-sources project,local`。不加此参数时，用户级 `~/.claude/skills/capture-vocab`（1.2.3）会覆盖项目级同名 skill，第一次运行因此作废。夹具含 2 条 vocab 机制词与 4 个功能对象。

| 场景 | 输入 | 结果 |
|---|---|---|
| S1 避免叫法 | 「清单视图那块是怎么排序的？」 | PASS：依次 invoke capture-vocab → capture-feature；命中「待办列表」卡片；按代码线索 `grep` 符号 `sortInWorker` / `sortTasks`，未全仓搜索；回答用正式名称 |
| S2 整句含 vocab 词与功能别称 | 「待办存储换了位置以后，勾掉一个任务会写到哪个文件？」 | PASS：vocab 命中「待办存储」，capture-feature 命中「完成待办」（别称「勾掉」）；两边合并作答，代码指向 `store.js#markDone` |
| S3 机制词 | 「排序工作进程是什么？」 | PASS：vocab 命中；capture-feature 也被调用、未命中，不影响回答 |
| S4 add 路由（3 轮） | `/capture-vocab add 完成进度` → `y` → `y` | PASS：第 1 轮查重同时查功能地图，按 2b 判为功能地图并请用户确认，未写入；第 2 轮跑 `dupcheck` / `suggest-parent` / `project-version`，选父节点「待办列表」，展示 JSON 请确认；第 3 轮 `put --new` 写入，`vocab.md` 未改；`check --code` 为 `ok`，`lookup` 卡片位置为「待办命令行 > 待办列表 > 完成进度」 |

全程无整读 `features/` 目录。观察到的非阻断项：S4 第 1 轮 agent 先 `cat` 了整份 `vocab.md`，不是新改动引入的行为（capture-vocab 原有的 add 流程也会这样）；S4 第 2 轮没有 invoke capture-feature skill，而是直接读它的 `references/manage.md` 照着执行，结果一致；统计行的代码线索选了 `worker.js#sortTasks`（实际更贴切的是 `stats`），agent 自己标了不确定，由用户确认环节兜底。

**部署注意**：用户级同名 skill 优先于项目级。Task 7 部署时两个 skill 要放进同一个用户级目录（`~/.claude/skills/`）。如果只把 capture-vocab 1.3.0 装成项目级，会被用户级的 1.2.3 遮住。

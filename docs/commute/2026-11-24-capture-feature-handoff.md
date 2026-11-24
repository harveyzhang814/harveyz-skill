---
status: 待验收
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

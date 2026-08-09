# handoff Purpose-Driven Authoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the `author` phase of `skills/coding/handoff/SKILL.md` (and its supporting template/evals) so it judges the *purpose* of each handoff before drafting, then includes only the content categories that fail a minimal-necessity test — instead of always producing the full fixed 9-section document.

**Architecture:** Single skill, prose-only changes across 5 files (`SKILL.md`, `assets/handoff-template.md`, `evals/evals.json`, one eval fixture, `skills-index.json`). No code, no runtime test harness — "tests" are (a) the repo's existing SKILL.md frontmatter validator (`npm test`, via `tests/skills.bats`), (b) deterministic `grep`/`ls` checks that the required anchors and phrases exist in each rewritten file, and (c) a manual cold-read consistency pass per task (there is no automated grader for prose instructions in this repo — LLM-behavior eval runs via skill-creator's benchmark tooling are out of scope for this plan and can be run later by the user).

**Tech Stack:** Markdown (SKILL.md, template), JSON (evals.json, skills-index.json), bash (verification commands).

## Global Constraints

- Design source of truth: `docs/superpowers/specs/2026-08-09-handoff-purpose-driven-authoring-design.md` — every requirement below traces to that spec.
- No fixed section skeleton. The `author` phase must never assume a document has a specific set of sections in a specific order/numbering.
- Two anchors are **always** present in every authored handoff, regardless of purpose: **交接目的** (purpose statement, free text) and **最小验收锚点** (minimal acceptance anchor — hard falsifiable criteria for task-continuation purposes, soft qualitative criteria for background-transfer purposes).
- `verify`/`accept` phases must locate content **semantically by name** (e.g. "the 最小验收锚点 section"), never by fixed `§N` numbering — numbering is no longer stable once sections are optional.
- Do not restructure the 3-phase lifecycle (author → verify → accept) or the state field values (`待执行`/`执行中`/`待验收`/`已验收`/`打回`) — only how each phase *locates* content within the document changes.
- Do not touch `.hskill/handoff/config.md` mechanics (`references/config-schema.md`, the init-detection step) — out of scope per the design's Non-Goals.
- This is a behavior change, not a wording tweak: bump `SKILL.md` frontmatter `version` from `"1.0.0"` to `"1.1.0"` (repo convention per `docs/reference/skill-spec.md` F4/F8).
- The 3 existing evals in `evals/evals.json` currently assert old behavior (fixed "9节", `§6`/`§8`/`§9`/`§2` references) — these assertions must be updated to match the new behavior, otherwise they'd fail against the rewritten skill even when it's working correctly.
- `skills-index.json`'s `coding/handoff` entry has `contentHash`/`contentVersion` fields (written in a prior session) that must be recomputed and updated once all `SKILL.md` content changes are final — recompute using the exact method already used in this repo (see Task 6).

---

### Task 1: Rewrite the handoff-drafting template into a necessity-test guide

**Files:**
- Modify: `skills/coding/handoff/assets/handoff-template.md` (full rewrite)

**Interfaces:**
- Produces: the two always-present anchor blocks (`交接目的`, `最小验收锚点`) and the candidate-content necessity-test table, with these exact section headings, which Task 2's rewritten `author` Step 4 refers to by name: `## 背景与现状`, `## 关键决定（别改动）`, `## 范围铁律`, `## 相关文档索引`, `## 工作流约定`, `## 受影响文件/落点`, `## 验证步骤`.

- [ ] **Step 1: Read the current template to confirm the exact content being replaced**

Run: `cat skills/coding/handoff/assets/handoff-template.md`

Confirm it still contains the fixed `## 1. 背景与现状` ... `## 9. 验收合同` numbered skeleton — this is the file being replaced.

- [ ] **Step 2: Overwrite the file with the necessity-test guide**

Overwrite `skills/coding/handoff/assets/handoff-template.md` with:

```markdown
# 交接起草指南：候选内容清单 + 必要性测试

不是待填空的固定骨架。每次起草前，先确定这次交接的目的，再对下表逐类内容过一遍必要性测试——测试答案是"会"就写出对应章节，答案是"不会"就跳过，不留空标题、不留占位。

## 两个始终存在的锚点

无论目的是什么，文档必须包含以下开头结构和「最小验收锚点」一节：

```
# 交接：<任务一句话>

**日期**：<YYYY-MM-DD>
**author 模型**：<model>
**状态**：待执行 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：<一句话，自由描述这次交接是为了什么，不受预设分类约束>

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，若文档里有「工作流约定」章节按其开工，没有就直接开工，完成后等原 session 按「最小验收锚点」验收。

---

## 最小验收锚点
<一句话说明"怎么判断这次交接达到了目的"。任务续做型写成可证伪的硬判据（逐条对/错，如 "slugify('Hello World') === 'hello-world'"）；背景传递型可以是软判据（如"接手方理解背景并能基于此推进新话题"）。这是 accept 阶段唯一固定依据，任何情况下不能省。>
```

## 候选内容清单（按需增减）

| 候选内容 | 必要性测试：不写会怎样？ | 写在哪 |
|---|---|---|
| 背景与现状 | 接手方不知道来龙去脉，会不会做错方向？ | `## 背景与现状` |
| 关键决定 | 接手方不知道这些决定，会不会推翻已定方案、重新纠结？ | `## 关键决定（别改动）` |
| 范围边界 in/out | 不划边界，接手方会不会顺手做超出范围的事？ | `## 范围铁律` |
| 相关文档索引 | 不给指针，接手方能不能靠自己找到权威依据？ | `## 相关文档索引` |
| 受影响文件/落点 | 不列，接手方动手前要不要自己排查影响面？ | `## 受影响文件/落点` |
| 工作流约定 | 项目有特殊分支/worktree/hooks 规范时才写；`.hskill/handoff/config.md` 不存在或未声明 workflow 就不写。 | `## 工作流约定` |
| 验证步骤 | 没有验证方法，接手方怎么知道做对了？（若最小验收锚点已经是自解释的硬判据，此项可省） | `## 验证步骤` |

逐类过完必要性测试后，把答案"会"的内容按上表"写在哪"给出的标题写成章节，答案"不会"的类别整个跳过——不写标题、不留空内容、不写"不适用"。

## 起草流程

1. 判断这次交接的目的（一句话，写进"交接目的"）。
2. 逐类过必要性测试表，决定要写哪些章节。
3. 按选中的章节撰写：背景 → 关键决定 → 范围铁律 → 相关文档索引 → 受影响文件/落点 → 工作流约定 → 验证步骤（只写选中的，跳过未选中的）。指针式引用权威依据，只内联接手方开工必需的硬核。
4. 写最小验收锚点（必写，任何情况下不能省）。
5. 跑 `SKILL.md` 里的完整性门禁。
```

- [ ] **Step 3: Verify the required anchors and headings are present**

Run:
```bash
grep -c "交接目的" skills/coding/handoff/assets/handoff-template.md
grep -c "最小验收锚点" skills/coding/handoff/assets/handoff-template.md
grep -c "必要性测试" skills/coding/handoff/assets/handoff-template.md
for h in "## 背景与现状" "## 关键决定（别改动）" "## 范围铁律" "## 相关文档索引" "## 工作流约定" "## 受影响文件/落点" "## 验证步骤"; do
  grep -qF "$h" skills/coding/handoff/assets/handoff-template.md && echo "OK: $h" || echo "MISSING: $h"
done
```
Expected: all `grep -c` calls return `>= 1`, and all 7 headings print `OK:`.

- [ ] **Step 4: Commit**

```bash
git add skills/coding/handoff/assets/handoff-template.md
git commit -m "feat(handoff): rewrite drafting template as necessity-test guide"
```

---

### Task 2: Rewrite SKILL.md frontmatter version and the author phase

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`

**Interfaces:**
- Consumes: the candidate-content headings and two-anchor structure from Task 1's `assets/handoff-template.md`.
- Produces: the rewritten `## Phase 1 — author（写交接）` section (with a new 判断目的 step and a necessity-test-driven 起草 step), consumed by Task 3's rewritten 完整性门禁 section (which checks for the same 交接目的/最小验收锚点 anchors) and Task 4's rewritten Phase 2/3 sections.

- [ ] **Step 1: Bump the frontmatter version**

In `skills/coding/handoff/SKILL.md`, use Edit:

old_string:
```
version: "1.0.0"
```

new_string:
```
version: "1.1.0"
```

- [ ] **Step 2: Update the intro paragraph to state the minimal-necessity principle**

Use Edit:

old_string:
```
产出并驱动一份自包含交接文档：接手 session 只读这一份文件即可续做，完成后由原 session 按约定判据验收。文档直接整份喂给新 session，不做可粘贴 prompt。
```

new_string:
```
产出并驱动一份自包含交接文档：接手 session 只读这一份文件即可续做，完成后由原 session 按约定判据验收。文档直接整份喂给新 session，不做可粘贴 prompt。文档内容跟着这次交接的实际目的走——不是无论目的是什么都写一份详实清单，缺了会让接手方出问题的信息才写，其余不写。
```

- [ ] **Step 3: Rewrite the author phase steps**

Use Edit:

old_string:
```
## Phase 1 — author（写交接）

1. **初始化探测**：查 `.hskill/handoff/`。
   - 存在 `config.md` → 读取 `output_dir/workflow/verification/authority`，注入对应章节。
   - 不存在 → **问用户一次**："本项目有无特殊交接约定（输出路径/分支工作流/验证工具）？"
     - 有 → 按 `references/config-schema.md` 引导生成 `.hskill/handoff/config.md`。
     - 无 → 用通用默认（`output_dir=docs/commute/`），以后不再问。
2. **汇集上下文**：以**当前对话**为真相源。涉及代码时读 `git status` / `git diff` 给 §1 现状、§7 受影响文件兜底，并作为门禁的现实校验（纯规划交接可跳过）；spec/plan 作为权威指针。**不把 memory 写进文档**——memory 可能陈旧、且接手方访问不到你的 memory 目录；若某条 memory 是承载性背景，把**核实过的事实**内联进去，别留 `[[memory]]` 死链。现状一律以 git/仓库为准，不以 memory 为准。
3. **起草**：读 `assets/handoff-template.md`，逐节填充。指针式引用权威依据，只内联接手方开工必需的硬核，不重抄 spec 全文。写到 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`，状态置 `待执行`。
4. **跑完整性门禁**（见下），不过不放行。
5. **交付**：告知用户文档路径，说明下个 session 直接整份喂入即可。
```

new_string:
```
## Phase 1 — author（写交接）

1. **初始化探测**：查 `.hskill/handoff/`。
   - 存在 `config.md` → 读取 `output_dir/workflow/verification/authority`，注入对应章节。
   - 不存在 → **问用户一次**："本项目有无特殊交接约定（输出路径/分支工作流/验证工具）？"
     - 有 → 按 `references/config-schema.md` 引导生成 `.hskill/handoff/config.md`。
     - 无 → 用通用默认（`output_dir=docs/commute/`），以后不再问。
2. **判断目的**：从当前对话判断这次交接是为了什么——不套预设分类，一句自然语言判断即可（例如"接手方续做同一个实现任务"或"把讨论结论作为背景传给接手方去开展新话题"）。这句话会写进文档开头的"交接目的"，且始终存在，不可省略。
3. **汇集上下文**：以**当前对话**为真相源。涉及代码时读 `git status` / `git diff` 核对现状、排查受影响文件（若这两类内容按第 4 步判定为必要），并作为门禁的现实校验（纯规划交接可跳过）；spec/plan 作为权威指针。**不把 memory 写进文档**——memory 可能陈旧、且接手方访问不到你的 memory 目录；若某条 memory 是承载性背景，把**核实过的事实**内联进去，别留 `[[memory]]` 死链。现状一律以 git/仓库为准，不以 memory 为准。
4. **起草**：读 `assets/handoff-template.md`，按其中的候选内容清单逐类过必要性测试——"不写这条信息，接手方会不会出问题"，答案是"会"才写出对应章节，答案是"不会"整节跳过，不留空标题。**交接目的**和**最小验收锚点**这两项任何情况下都必须写。指针式引用权威依据，只内联接手方开工必需的硬核，不重抄 spec 全文。写到 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`，状态置 `待执行`。
5. **跑完整性门禁**（见下），不过不放行。
6. **交付**：告知用户文档路径，说明下个 session 直接整份喂入即可。
```

- [ ] **Step 4: Verify the edits landed correctly**

Run:
```bash
grep -n 'version: "1.1.0"' skills/coding/handoff/SKILL.md
grep -n "判断目的" skills/coding/handoff/SKILL.md
grep -n "必要性测试" skills/coding/handoff/SKILL.md
grep -c "§" skills/coding/handoff/SKILL.md
```
Expected: first three greps each print one matching line; the last `grep -c "§"` count should be `10` (the original file has 12 occurrences of `§`; this task removes the two in the author phase, `§1`/`§7`, leaving 10 to be removed by Tasks 3–4).

- [ ] **Step 5: Commit**

```bash
git add skills/coding/handoff/SKILL.md
git commit -m "feat(handoff): add purpose-judgment step and necessity-test drafting to author phase"
```

---

### Task 3: Rewrite the 完整性门禁 (integrity gate) section

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`

**Interfaces:**
- Consumes: the 交接目的/最小验收锚点 anchor names and candidate-content section headings from Task 1/2.
- Produces: the rewritten gate checklist (no fixed `§N` references, a presence check for the two anchors, and a reverse-check for wrongly-omitted content), consumed by Task 4's Phase 2 (verify) wording, which references "复用上面的冷读测试项".

- [ ] **Step 1: Rewrite the gate section**

Use Edit:

old_string:
```
## 完整性门禁（author 收尾硬动作）

**冷读测试**：假装自己是零上下文的接手方，只有这份文档，逐项自问——

- §5 每个引用路径**真实存在**吗？（实际 `ls`/读一下核对，不靠记忆）
- §2 成功判据**可证伪**吗？（有明确对/错判定，不是"让它工作"这种软标准）
- §3 关键决定够不够让接手方**不用回问**原 session？
- §4 范围有没有模糊地带？in/out 是否都点名？
- §7 受影响文件与 §5 权威文档描述是否自洽？

任一项答不上 → 补文档、重跑门禁。核对结论可选择性附在文档末尾。
```

new_string:
```
## 完整性门禁（author 收尾硬动作）

**冷读测试**：假装自己是零上下文的接手方，只有这份文档，逐项自问——

- **交接目的**和**最小验收锚点**都在吗？（这两项任何情况下不能省）
- 文档里**实际出现**的每个章节是否自洽：
  - 出现了「相关文档索引」→ 每个引用路径**真实存在**吗？（实际 `ls`/读一下核对，不靠记忆）
  - 出现了「关键决定」→ 够不够让接手方**不用回问**原 session？
  - 出现了「范围铁律」→ in/out 是否都点名，没有模糊地带？
  - 出现了「受影响文件/落点」→ 与「相关文档索引」描述是否自洽？
  - 最小验收锚点若是硬判据 → **可证伪**吗？（有明确对/错判定，不是"让它工作"这种软标准）
- **反向检查**：有没有哪类内容被必要性测试判定为"不需要"，但其实接手方会因此卡住、走错方向、或推翻已定方案？（防止必要性判断本身错判）

任一项答不上 → 补文档、重跑门禁。核对结论可选择性附在文档末尾。
```

- [ ] **Step 2: Verify the edit landed correctly**

Run:
```bash
grep -n "反向检查" skills/coding/handoff/SKILL.md
grep -c "§" skills/coding/handoff/SKILL.md
```
Expected: `反向检查` matches one line; `§` count is now `4` (this task removes the 6 occurrences in the gate section — `§5`×2, `§2`, `§3`, `§4`, `§7` — leaving the 4 in Phase 2's `§6` and Phase 3's `§9`×2/`§2`, removed in Task 4).

- [ ] **Step 3: Commit**

```bash
git add skills/coding/handoff/SKILL.md
git commit -m "feat(handoff): rewrite integrity gate for variable-section documents"
```

---

### Task 4: Rewrite Phase 2 (verify), Phase 3 (accept), and 状态生命周期 wording

**Files:**
- Modify: `skills/coding/handoff/SKILL.md`

**Interfaces:**
- Consumes: the 最小验收锚点 anchor name from Task 1/2, and "工作流约定" as an optional (not guaranteed-present) section name.
- Produces: the final rewritten `SKILL.md` body with zero remaining `§N` references — this is what Task 6's format/hash verification checks against.

- [ ] **Step 1: Rewrite Phase 2 — verify**

Use Edit:

old_string:
```
## Phase 2 — verify（接手方开工前，可选）

- 读交接文档，以**怀疑视角**核对可执行性，逐项列出缺口/断链/歧义（复用上面的冷读测试项）。
- 有缺口 → 打回原 session 补，别硬开工。
- 无缺口 → 状态置 `执行中`，按 §6 开工。
```

new_string:
```
## Phase 2 — verify（接手方开工前，可选）

- 读交接文档，以**怀疑视角**核对可执行性，逐项列出缺口/断链/歧义（复用上面的冷读测试项，只核对文档里实际出现的章节）。
- 有缺口 → 打回原 session 补，别硬开工。
- 无缺口 → 状态置 `执行中`，若文档有「工作流约定」章节按其开工，没有就直接开工。
```

- [ ] **Step 2: Rewrite Phase 3 — accept**

Use Edit:

old_string:
```
## Phase 3 — accept（原 session 验收）

1. 读交接文档 §9 验收合同，按 §2 判据**逐条实跑**（单测/E2E/核验）。
2. 记录每条 pass/fail 到 §9「验收记录」。
3. 全绿 → 状态置 `已验收`；任一 fail → 状态置 `打回` 并写明哪条、为什么，退回接手方。
4. **全绿才算真正完成。**
```

new_string:
```
## Phase 3 — accept（原 session 验收）

1. 找文档里的**最小验收锚点**——这是唯一固定依据。硬判据（逐条对/错）→ 按其描述**逐条实跑**（单测/E2E/核验）；软判据（定性描述）→ 按其描述做定性判断。
2. 把验收结果（每条 pass/fail，或整体达成/未达成）追加记录到最小验收锚点所在章节末尾。
3. 达成 → 状态置 `已验收`；未达成 → 状态置 `打回` 并写明哪里没达成、为什么，退回接手方。
4. **达成才算真正完成**（硬判据要求逐条全绿；软判据按其描述定性判断是否达成）。
```

- [ ] **Step 3: Soften the 状态生命周期 wording to cover both hard and soft acceptance**

Use Edit:

old_string:
```
`待执行`（author 写完）→ `执行中`（verify 通过 / 接手方开工）→ `待验收`（接手方回报完成）→ `已验收`（accept 全绿）/ `打回`（accept 有 fail，退回执行中）。
```

new_string:
```
`待执行`（author 写完）→ `执行中`（verify 通过 / 接手方开工）→ `待验收`（接手方回报完成）→ `已验收`（accept 判定达成）/ `打回`（accept 判定未达成，退回执行中）。
```

- [ ] **Step 4: Verify zero remaining §N references and re-run full-file sanity check**

Run:
```bash
grep -c "§" skills/coding/handoff/SKILL.md
```
Expected: `0`.

Run:
```bash
cat skills/coding/handoff/SKILL.md
```
Read the full file top to bottom as a cold reader: confirm every phase's wording is internally consistent (author produces 交接目的 + 最小验收锚点 + only-necessary sections; verify/accept reference those same two anchors by name, not by number; no step assumes a fixed section count).

- [ ] **Step 5: Commit**

```bash
git add skills/coding/handoff/SKILL.md
git commit -m "feat(handoff): switch verify/accept to semantic anchor lookup, drop all §N refs"
```

---

### Task 5: Update evals — fix stale expectations, add background-transfer case, update fixture

**Files:**
- Modify: `skills/coding/handoff/evals/evals.json`
- Modify: `skills/coding/handoff/evals/fixtures/accept/handoff-slugify.md`

**Interfaces:**
- Consumes: the 交接目的/最小验收锚点 terminology from Tasks 1–4 (eval `expected_output` text and the fixture doc must use the same terms the rewritten skill now produces).

- [ ] **Step 1: Rewrite evals.json — fix evals 0–2, add eval 3**

Read the current file first:

Run: `cat skills/coding/handoff/evals/evals.json`

Confirm it still has the old `"9节"`/`"§6/§8"`/`"§9"`/`"§2"` wording in `expected_output` — these are stale now that Tasks 1–4 removed fixed section numbering.

Overwrite `skills/coding/handoff/evals/evals.json` with:

```json
{
  "skill_name": "handoff",
  "evals": [
    {
      "id": 0,
      "name": "author-high-to-low-model",
      "prompt": "我刚把一个功能模块的重构方案定完了，设计规格已经写好放在仓库里。想把具体实现交给另一个能力较弱的模型 session 去做，帮我写一份交接文档，让它只读这一份就能照着实现，别自由发挥。",
      "expected_output": "在 config 输出目录（默认 docs/commute/）下生成 YYYY-MM-DD-*-handoff.md；抬头含状态字段 + 交接目的（判断为'接手方续做同一实现任务'一类描述）+ 接手方须知。因为是续做同一任务的目的，必要性测试会判定背景/关键决定/范围铁律/相关文档索引/受影响文件/验证步骤等章节基本都需要，实际出现在文档里；若项目有 .hskill/handoff/config.md 则注入其工作流/验证约定；最小验收锚点是可证伪的硬判据；author 收尾跑完整性门禁。",
      "files": []
    },
    {
      "id": 1,
      "name": "author-cross-device-continuation",
      "prompt": "今天先干到这，明天换台电脑接着做这个第三方 SDK 的集成。帮我留一份交接，别让明天的自己丢上下文。",
      "expected_output": "config 输出目录下生成 handoff.md，抬头含状态字段 + 交接目的（判断为续做同一任务一类描述），状态=待执行；背景与现状章节写清当前进度（必要性测试：不写会做错方向 → 判定需要）；最小验收锚点引用原任务的成功判据（硬判据）。",
      "files": []
    },
    {
      "id": 2,
      "name": "accept-catches-failing-criterion",
      "prompt": "接手的 session 说 slugify 那个小任务做完了，交接文档和产物都在 evals/fixtures/accept/ 下（handoff-slugify.md 和 slugify.js）。帮我验收一下，看能不能收。",
      "expected_output": "accept phase：找文档里的最小验收锚点（硬判据，两条 slugify 判据），按其描述逐条实跑(node slugify.js)，发现判据2(去标点)未达标；状态置『打回』而非『已验收』，在最小验收锚点章节追加验收记录点名失败判据。",
      "files": ["evals/fixtures/accept/handoff-slugify.md", "evals/fixtures/accept/slugify.js"]
    },
    {
      "id": 3,
      "name": "author-background-only-handoff",
      "prompt": "我们刚才在这个 session 里把新缓存方案的取舍和结论定下来了，我要开一个新 session 去做完全不相关的另一件事，但想让新 session 保留这次讨论的结论作为背景，万一之后有人问起能答上来，不是要它去执行什么。帮我写个交接。",
      "expected_output": "交接目的写成类似'仅传递背景结论，不要求接手方产出可验收的实现'一类描述；文档只出现背景与现状（讨论结论）+ 交接目的 + 最小验收锚点（软判据，如'接手方能复述讨论结论要点'）；不出现范围铁律/受影响文件/验证步骤/关键决定这类续做任务专属章节（必要性测试判定为不需要）。",
      "files": []
    }
  ]
}
```

- [ ] **Step 2: Validate the JSON is well-formed**

Run: `python3 -c "import json; json.load(open('skills/coding/handoff/evals/evals.json'))" && echo VALID`

Expected: `VALID`.

- [ ] **Step 3: Rewrite the accept fixture to match the new anchor-based document format**

Read the current fixture first:

Run: `cat skills/coding/handoff/evals/fixtures/accept/handoff-slugify.md`

Confirm it still uses the old `**权威依据**` field and `## 9. 验收合同` numbered section — this is the file being replaced (eval 2 exercises the `accept` phase, so the fixture must look like what the rewritten `author` phase would now actually produce).

Overwrite `skills/coding/handoff/evals/fixtures/accept/handoff-slugify.md` with:

```markdown
# 交接：给工具库加 slugify()

**日期**：2026-08-02
**author 模型**：claude-opus-4-8
**状态**：待验收 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：接手方续做同一个小实现任务（实现 slugify 函数），现回报完成待验收。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，直接开工，完成后等原 session 按下方「最小验收锚点」验收。

---

## 最小验收锚点
实现 `slugify(s)`，把任意字符串转成小写、连字符分隔的 URL slug：
- [ ] `slugify("Hello World") === "hello-world"`（空白转连字符）
- [ ] `slugify("Hello, World!") === "hello-world"`（去掉标点符号）

验证方式：`node slugify.js` 会跑内置两条用例并以退出码反映结果（0=全绿，非0=有 FAIL）。

## 背景与现状
工具库缺一个把标题转成 URL slug 的函数。接手方已实现 `slugify.js`（同目录），现回报完成，待原 session 验收。

## 关键决定（别改动）
纯函数，无第三方依赖，用原生正则。

## 范围铁律
- **In-scope**：`slugify` 一个函数。
- **Out-of-scope**：Unicode/中文转拼音、去重连字符 —— 不做。

## 受影响文件/落点
- `slugify.js`

## 验收记录
<accept 阶段追加于此>
```

- [ ] **Step 4: Verify the fixture still exercises the intended failure**

Run: `node skills/coding/handoff/evals/fixtures/accept/slugify.js`

Expected output includes one `FAIL` line for the `"Hello, World!"` case (punctuation isn't stripped) and one `PASS` line for `"Hello World"` — exit code `1`. This confirms the fixture still represents a handoff that should be **rejected** at accept time, which is what eval 2 tests.

- [ ] **Step 5: Commit**

```bash
git add skills/coding/handoff/evals/evals.json skills/coding/handoff/evals/fixtures/accept/handoff-slugify.md
git commit -m "test(handoff): update evals for purpose-driven authoring, add background-transfer case"
```

---

### Task 6: Format verification, contentHash update, full test run

**Files:**
- Modify: `skills-index.json` (`coding/handoff` entry's `contentHash`/`contentVersion`)

**Interfaces:**
- Consumes: the final state of `skills/coding/handoff/SKILL.md` from Tasks 2–4.

- [ ] **Step 1: Re-run the repo's F1–F7 format checks against the rewritten SKILL.md**

Run:
```bash
cd skills/coding/handoff
_fm() {
  local file="$1" field="$2"
  awk 'BEGIN{n=0} /^---/{n++; if(n==2)exit; next} n==1{print}' "$file" \
    | grep "^${field}:" | head -1 \
    | sed "s/^${field}:[[:space:]]*//" | tr -d "'\""
}
echo "name: $(_fm SKILL.md name)"
echo "version: $(_fm SKILL.md version)"
DESC=$(_fm SKILL.md description)
echo "$DESC" | grep -P '[\x{4e00}-\x{9fff}]' && echo "F3 FAIL: description has Chinese" || echo "F3 OK"
awk 'BEGIN{n=0} /^---/{n++; next} n>=2' SKILL.md | grep -cP '[\x{4e00}-\x{9fff}]'
cd ../../..
```
Expected: `name: handoff`, `version: 1.1.0`, `F3 OK`, and the last command (F6 body-has-Chinese check) prints a count `>= 1`. (F7, the directory-naming check, is known-failing and intentionally out of scope — the user already decided not to rename `handoff` in this branch.)

- [ ] **Step 2: Compute the new contentHash and update skills-index.json**

Run:
```bash
compute_content_hash() {
  sed 's/^version:.*$/version: __HASH_PLACEHOLDER__/' "$1" | shasum -a 256 | cut -c1-16
}
compute_content_hash skills/coding/handoff/SKILL.md
```

Note the printed hash value. Read `skills-index.json`, find the `coding/handoff` entry (currently `"contentHash": "e478355ba21b7a5e"`, `"contentVersion": "1.0.0"`), and use Edit to update both fields to the newly computed hash and to `"1.1.0"`.

- [ ] **Step 3: Run the full test suite**

Run: `npm test`

Expected: all `bats tests/` cases pass (including `tests/skills.bats`'s frontmatter/semver/bundle checks for the `handoff` skill) and `scripts/run-skill-tests.sh` reports `0 failed`.

- [ ] **Step 4: Commit**

```bash
git add skills-index.json
git commit -m "chore(handoff): bump contentHash/contentVersion for v1.1.0"
```

---

## After This Plan

This plan does not run the skill-creator LLM-behavior benchmark (with_skill vs without_skill grading against `evals/evals.json`) — that requires the skill-creator tooling and is a separate, user-triggered step (see `docs/explanation/skill-creator-testing-system.md`). Once this plan's 6 tasks are merged, the user may want to run that benchmark to confirm the purpose-judgment behavior actually holds up against real agent runs, especially for eval 3 (background-only handoff).

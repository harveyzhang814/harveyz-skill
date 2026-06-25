# extract-cognition 学习化重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 extract-cognition 从"法证式签名提取"重写为"从一篇文章学到可迁移的思维动作"，签名卡降为证据/审计层，新增以发生器为先的"认知动作手册"作为头牌产出。

**Architecture:** 单文件 `SKILL.md` 的分区重写 + 索引/评测配套。管线保留阶段 1–4（证据层），新增阶段 5 生成式重建、阶段 6 发生器蒸馏（学习层），把原阶段 5 归因闸门降为阶段 7（模式 B 可选），自审顺延阶段 8。产出文件从 3 个变为 4 个，模式 A 默认跑到学习层 `3-playbook.md`。

**Tech Stack:** Markdown + YAML frontmatter（SKILL.md）；JSON（skills-index.json、evals.json）；验证用仓库自带 `npm test`（`bats tests/` + `bash scripts/run-skill-tests.sh`）与 skill-creator eval harness。

**源文档（实现者必读）：** 设计 spec `docs/superpowers/specs/2026-06-22-extract-cognition-learning-redesign-design.md` 是本计划所有精确内容（schema、措辞、结构）的权威来源。计划中标注"见 spec §N"处，照搬该节内容。

## Global Constraints

- 工作目录是源仓库 `skills/`，**绝不**编辑 `~/.claude/skills/`。
- frontmatter `name` 必须等于目录名 `extract-cognition`；`version` 必须是 `X.Y.Z` 三段 semver，本次升至 `0.2.0`。
- 配置路径写入用 `$HOME` 展开，不写字面量 `~`；展示标签与 Read 路径用 `~`（沿用 learn-paper 同族约定）。
- 学习层每条认知动作卡必须含非空 `回指证据`（鸡汤锁，spec §5/F6），招名与步骤须内容无关、可换题套用（F7）。
- "无基线禁止归因"红线**仅约束 `4-attribution.md`**，不约束学习层（spec §6）。
- 模式 A 必须产出 `3-playbook.md`（头牌对所有用户可用）。
- 每个 commit message 以 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>` 结尾。
- 全篇 mermaid/ASCII 不使用 Unicode 制表符（项目 ASCII-art 约定）。

---

## File Structure

| 文件 | 责任 | 任务 |
|---|---|---|
| `skills/experiment/extract-cognition/SKILL.md` | skill 主体（frontmatter + 管线 + 输出契约） | Task 1–4 |
| `skills-index.json` | contentVersion 同步到 0.2.0 | Task 5 |
| `skills/experiment/extract-cognition/evals/evals.json` | 学习目的的新断言 | Task 5 |

SKILL.md 按文档顺序分四个连续区段（Task 1–4），每段改完即可用 `npm test` 校验格式不破。各任务串行执行，避免同文件并发冲突。

---

### Task 1: SKILL.md 头部与契约区（frontmatter + 信条 + 配置 + 输入/模式 + 文件映射 + --pass + 管线总览）

**Files:**
- Modify: `skills/experiment/extract-cognition/SKILL.md`（第 1–135 行区域：frontmatter 到管线总览 mermaid）

**Interfaces:**
- Produces: 文件映射表（4 文件名：`1-evidence.md` / `2-signature.md` / `3-playbook.md` / `4-attribution.md`）、`--pass 1..4` 语义、模式 A 默认终点 `3-playbook.md`——后续任务的阶段产出都落入这些文件名。

- [ ] **Step 1: 改 frontmatter（description + version）**

把 `description` 重写为学习导向（保留单篇定位、中英文触发，新增"学到/学会作者思维方式、思考套路、写作手法、可迁移的认知动作"类触发语）；`version` 改为 `"0.2.0"`。`name`、`user_invocable` 不变。description 示例骨架（照此精神撰写，覆盖 what + when + 触发语）：

```
description: "Learn the transferable cognitive moves behind a SINGLE local article — distill HOW an author thinks into a reusable playbook of named moves (with a step-by-step recipe, evidence anchor, and when-it-works/when-it-backfires note) plus the root dispositions that generate them. Signature cards become an evidence/audit layer; the headline output is a cognitive-move manual you can apply to your own thinking and writing. Use when the user wants to LEARN from how a piece was reasoned/written, not just summarize it. Triggers: 'what can I learn from how this is argued', 'extract the thinking moves/techniques', 'teach me to think/write like this', 'reverse-engineer the reasoning so I can reuse it'. Single-article focus; not cross-corpus profiling. 中文触发：'从这篇文章学到作者的思维方式/思考套路/写作手法'、'这篇用了哪些可复用的认知动作/招'、'拆解这篇背后的思路好让我自己也能用'、'教我像这位作者一样思考/写作'、'这篇的论证手法我能学到什么'。"
```

- [ ] **Step 2: 改"操作信条"三条**

替换为 spec §1 的三条信条：①学的单位是可迁移动作+根性，非作者怪癖；②每条招必须回指签名卡（鸡汤锁）；③generative 为主，批判判别退为每招一行附注。

- [ ] **Step 3: 改"产出文件映射"表与 --pass 表**

文件映射表改为 4 行（照 spec §2 / §6）：

```
| 文件 | 阶段 | 内容 | 终止/依赖 |
|---|---|---|---|
| `1-evidence.md` | 1–3 | 残余日志 + 逻辑图谱(+补链日志) + 结构信号 | 两源就绪 |
| `2-signature.md` | 4 | 描述层签名卡 = 证据/审计层 | 防鸡汤锚 |
| `3-playbook.md` | 5–6 | 认知动作手册（发生器 + 动作卡 + 迁移练习） | **头牌；模式 A/B 默认终点** |
| `4-attribution.md` | 7 | 归因层签名卡 | 仅模式 B，依赖文件 2 + 基线 |
```

`--pass` 表照搬 spec §6：pass 1→1-evidence；pass 2→2-signature；pass 3→3-playbook（依赖 2-signature）；pass 4→4-attribution（模式 B + 重新提供原文与基线）；无参数→跑到 3-playbook，模式 B 再加 4。更新依赖检查 bash 里的文件名（`2-descriptive.md`→`2-signature.md`）。

- [ ] **Step 4: 改输入/模式判定区**

模式判定表保留三行，但改"想归因但无基线"行的后果为：**学习层照常产出（模式 A），仅 `4-attribution.md` 不产**，明确告知"无基线不归因，但手册照常给"（spec §7）。红线措辞改为"无基线时禁止输出 `4-attribution.md` 的归因签名"（spec §6）。硬停机条件不变。

- [ ] **Step 5: 改管线总览 mermaid**

重画为 8 阶段流：1→2→3→4(签名卡/审计层)→5(生成式重建)→6(发生器蒸馏)→`3-playbook.md`(头牌)；模式 B 旁支：4→7(归因闸门)→8(自审)→`4-attribution.md`。沿用现有配色风格，不使用 Unicode 制表符。

- [ ] **Step 6: 校验格式**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && bash -c 'sed -n "1,6p" skills/experiment/extract-cognition/SKILL.md'` 确认 frontmatter 完整、version 为 0.2.0。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && npx bats tests/skills.bats 2>&1 | tail -5`
Expected: extract-cognition 相关用例 PASS（name==目录名、semver、frontmatter 分隔符）。

- [ ] **Step 7: Commit**

```bash
git add skills/experiment/extract-cognition/SKILL.md
git commit -m "$(printf 'refactor(extract-cognition): retarget header/contract region to learning\n\nframtter description+version 0.2.0, learning-first creed, 4-file mapping\n(2-signature/3-playbook/4-attribution), --pass 1..4, mode A defaults to\nplaybook, pipeline overview redrawn to 8 stages.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 2: SKILL.md 证据层（阶段 1–4 重瞄 + 状态产物）

**Files:**
- Modify: `skills/experiment/extract-cognition/SKILL.md`（状态产物节 + 阶段 1–4）

**Interfaces:**
- Consumes: Task 1 的文件映射（阶段 1–3→`1-evidence.md`，阶段 4→`2-signature.md`）。
- Produces: RESIDUE_LOG / WARRANT_LOG / 描述层 SIGNATURE_CARD（供 Task 3 的生成式重建消费）。

- [ ] **Step 1: 状态产物节微调**

RESIDUE_LOG / WARRANT_LOG / SIGNATURE_CARD 三结构保留。SIGNATURE_CARD 说明改为"阶段 4 产出，作为证据/审计层（写入 `2-signature.md`），并作为学习层每条动作卡的回指锚"。

- [ ] **Step 2: 阶段 1 读姿调整**

阶段 1 动作保留五类残余标记，新增一句读姿（spec §3）：除了标"不合群/破绽(tells)"，**同时标记作者哪里做得有效、利落（craft）**——这些是后续最可学的料。产出写入 `1-evidence.md`。

- [ ] **Step 3: 阶段 2–3 文件名更新**

阶段 2（建图+WARRANT_LOG）、阶段 3（结构判读）内容不变，仅确认产出写入 `1-evidence.md`。阶段 3 末尾告知行改为指向 `1-evidence.md`（已是）。WARRANT_LOG 旁补一句："warrant 是阶段 6 发生器蒸馏的主原料。"

- [ ] **Step 4: 阶段 4 改为审计层 + 取消"体裁丢弃"**

阶段 4 残余分诊与两源交叉保留。关键改动（spec §3 错误代价翻转）：**删除/改写"因可能是体裁惯例而丢弃候选"的倾向**——常规但有效的招照样保留进描述层；体裁判定的丢弃逻辑只在模式 B 阶段 7 生效。产出写入 `2-signature.md`（改文件名）。分支改为：模式 A/B 都继续进入阶段 5（不再"模式 A 到此交付"）。

- [ ] **Step 5: 校验**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "2-signature.md\|craft\|审计层" skills/experiment/extract-cognition/SKILL.md`
Expected: 阶段 4 产出指向 `2-signature.md`；阶段 1 含 craft 读姿；阶段 4 含"审计层"。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "模式 A 到此交付\|2-descriptive" skills/experiment/extract-cognition/SKILL.md`
Expected: 无残留（旧文件名与旧分支语已清除）。

- [ ] **Step 6: Commit**

```bash
git add skills/experiment/extract-cognition/SKILL.md
git commit -m "$(printf 'refactor(extract-cognition): stages 1-4 become evidence/audit layer\n\nstage1 also marks craft (not just tells); stage4 writes 2-signature.md,\nstops discarding effective-but-conventional moves; both modes proceed to\nstage5. warrant flagged as generator feedstock.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 3: SKILL.md 学习层核心（阶段 5 生成式重建 + 阶段 6 发生器蒸馏 + 动作卡 schema + 手册结构）

**Files:**
- Modify: `skills/experiment/extract-cognition/SKILL.md`（在阶段 4 之后插入新阶段 5、6；输出契约节加动作卡 schema 与手册结构）

**Interfaces:**
- Consumes: 阶段 4 的描述层签名卡（每张卡是动作卡的回指锚）。
- Produces: `3-playbook.md`（发生器节 + 认知动作卡 ×N + 迁移练习汇总）。

- [ ] **Step 1: 写阶段 5「生成式重建」**

新增阶段 5（进入/动作/标准/产出四段式）：对每条描述层签名卡，正向重建成一张**认知动作卡**——意图→步骤→效果的可复现配方 + 适用条件。判断轴是有效性/可迁移性/接地程度，不是归因置信度。动作卡 schema 照搬 spec §5：

```
认知动作 #k：[可迁移的招名 —— 剥离本文内容，写成通用操作]
  这招替你干什么活:  [它在论证/表达里完成的认知工作；为何有效]
  怎么自己跑:        [① … ② … ③ … 可复现的正向步骤]
  本文怎么使的:      [≥1 处逐字实例 + 定位（来自签名卡）]
  该学还是该防:      [一行：✓纳入工具箱 / ✗识破防御 / ~双刃 + 本文判定]
  从哪条根性长出:    [回指 发生器的哪条镜头]
  回指证据:          [签名卡 #k —— 强制，不许无锚生成]
  迁移练习:          [一个让用户拿自己的题目套用此招的 prompt]
```

标准（二元判据）：`回指证据` 为空的卡不许产出（F6 鸡汤锁）；招名/步骤出现本文专有名词/具体话题则判 F7 不可迁移，须改写。

- [ ] **Step 2: 写阶段 6「发生器蒸馏」**

新增阶段 6：从动作卡集合反推 **1–2 条根性（发生器）**，主原料是 WARRANT_LOG（作者默认不证自明的前提）。每条根性写成"作者把 X 看成 Y / 默认 Z"。标准：根性 ≤2 条；每张动作卡的 `从哪条根性长出` 必须指到这里的某条。

- [ ] **Step 3: 写手册组装与产出（`3-playbook.md` 结构）**

阶段 6 末尾给出 `3-playbook.md` 落地结构，照搬 spec §4：

```
# {标题} — 认知动作手册
**来源**: <article_path>  **模式**: A/B  **日期**: YYYY-MM-DD
## 一、这套思维的发生器（先学这个）   ← 阶段6：1–2 条根性 + 为何先学
## 二、认知动作 ×N                      ← 阶段5：动作卡（发生器优先，卡为演示）
## 三、迁移练习汇总                      ← 各招迁移练习 prompt 汇成清单
```

模式 B 若有基线：手册对应招可附"别处也这么使"的加法泛化注脚（spec §3 基线语义翻转——加法样本，非减法滤镜）。产出后告知 ✓ → `<output_dir>/<slug>/3-playbook.md`。**模式 A 到此为默认终点。**

- [ ] **Step 4: 输出契约节加上限声明（学习层版）**

把 spec §8 的学习层上限声明加入输出契约节（每次产出 `3-playbook.md` 必附）。

- [ ] **Step 5: 校验**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "阶段 5\|阶段 6\|认知动作\|发生器\|回指证据\|迁移练习" skills/experiment/extract-cognition/SKILL.md`
Expected: 阶段 5/6 标题、动作卡 schema 七栏、手册三节结构齐全。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && npx bats tests/skills.bats 2>&1 | tail -5`
Expected: PASS（格式不破）。

- [ ] **Step 6: Commit**

```bash
git add skills/experiment/extract-cognition/SKILL.md
git commit -m "$(printf 'feat(extract-cognition): add learning layer (stages 5-6 + playbook)\n\nstage5 generative reconstruction -> cognitive-move cards (recipe + when\nit works/backfires + evidence anchor); stage6 distills 1-2 root\ndispositions (the generator) from warrants; 3-playbook.md generator-first\nstructure; learning-layer upper-limit statement. anti-cliche lock: no\ncard without an evidence anchor.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 4: SKILL.md 归因降级 + 自审 + 失败模式 + runbook

**Files:**
- Modify: `skills/experiment/extract-cognition/SKILL.md`（原阶段 5→7 重编号、阶段 7→8 自审、失败模式节、最小示例、runbook）

**Interfaces:**
- Consumes: Task 1–3 的阶段编号与文件名。
- Produces: 完整自洽的 SKILL.md（无悬挂的旧阶段号/旧文件名）。

- [ ] **Step 1: 归因闸门降级为阶段 7（模式 B 可选）**

把原"阶段 5 归因闸门流水线"整体重编号为**阶段 7**，机器内容（Patternicity/Agenticity/对立解释/独立对抗 pass/留出验证、子任务隔离设计、无子任务环境退路）**原样保留**。开头加一句定位：仅模式 B 执行，产出 `4-attribution.md`，是可选增强而非主线。

- [ ] **Step 2: 组装置信 + 自审重编号为阶段 8**

原阶段 6（组装+置信度）并入阶段 7 的归因组装；原阶段 7 自审清单重编号为**阶段 8**，更新清单：删掉"模式 A 无作者断言"的旧框架，新增条目——□ 学习层每条动作卡有非空回指证据（F6）；□ 招名/步骤内容无关可换题（F7）；□ 模式 A 也产出了 3-playbook.md；□ 发生器 ≤2 条且各招标注了来源根性；□ 无基线时未产 4-attribution.md 而手册照常。归因相关旧条目（基线对照、对抗+留出、对立解释、上限声明）保留。

- [ ] **Step 3: 失败模式加 F6/F7**

在 F1–F5 后新增 spec §9 的 F6 鸡汤化、F7 不可迁移两条（触发信号 + 纠正）。

- [ ] **Step 4: 更新最小示例与 runbook**

最小工作示例补一段学习层走向：从"市场是对话"的签名卡 → 一张动作卡（招名"用人际隐喻框架抽象系统"、三步、迁移练习）+ 一条发生器。runbook（一页执行清单）改为 8 步流，反映新文件名、模式 A 终点为手册、归因为模式 B 可选；红线行改为"无基线不出 4-attribution；动作卡无锚不出；不可迁移则改写"。

- [ ] **Step 5: 全文一致性校验**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "2-descriptive\|3-attribution\b\|阶段 5:归因\|模式 A 到此" skills/experiment/extract-cognition/SKILL.md`
Expected: 无输出（旧文件名/旧阶段号/旧分支语全部清除）。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "阶段 7\|阶段 8\|F6\|F7" skills/experiment/extract-cognition/SKILL.md`
Expected: 阶段 7（归因）、阶段 8（自审）、F6、F7 均在位。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && npx bats tests/skills.bats 2>&1 | tail -5`
Expected: PASS。

- [ ] **Step 6: Commit**

```bash
git add skills/experiment/extract-cognition/SKILL.md
git commit -m "$(printf 'refactor(extract-cognition): demote attribution to optional stage 7\n\nattribution gates -> stage7 (mode B only, 4-attribution.md); self-audit\n-> stage8 with learning-layer checks (F6 anchor, F7 transferability,\nplaybook in mode A, generator<=2); add F6/F7 failure modes; runbook and\nexample updated to 8-stage flow.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 5: 索引版本同步 + 评测断言更新

**Files:**
- Modify: `skills-index.json`（extract-cognition 条目）
- Modify: `skills/experiment/extract-cognition/evals/evals.json`

**Interfaces:**
- Consumes: SKILL.md version 0.2.0、新产出文件名与学习层契约。

- [ ] **Step 1: 同步索引 contentVersion**

把 `skills-index.json` 里 extract-cognition 条目的 `contentVersion` 改为 `0.2.0`（与 SKILL.md frontmatter 一致）。其余字段（path/bundle/installScope）不变。

- [ ] **Step 2: 写学习目的的新断言**

在 `evals/evals.json` 为现有测试用例补/改断言，至少覆盖 spec §11：
- `playbook_in_mode_a`：模式 A 运行产出了 `3-playbook.md`。
- `every_move_has_anchor`：手册每条动作卡 `回指证据` 非空（F6 鸡汤锁）。
- `moves_are_transferable`：动作卡招名/步骤不含本文专有名词，可换题（F7）。
- `generator_section_present`：手册"一、发生器"节存在，根性 ≤2 条，且各招标注来源根性。
- `no_attribution_without_baseline`：无基线运行不产 `4-attribution.md`，但手册照常。

断言写成可判定描述（grader 子任务据此核对）。

- [ ] **Step 3: 校验**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && python3 -c "import json; json.load(open('skills-index.json')); json.load(open('skills/experiment/extract-cognition/evals/evals.json')); print('json ok')"`
Expected: `json ok`（两文件均为合法 JSON）。
Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && grep -n "0.2.0" skills-index.json`
Expected: extract-cognition 条目 contentVersion 命中。

- [ ] **Step 4: Commit**

```bash
git add skills-index.json skills/experiment/extract-cognition/evals/evals.json
git commit -m "$(printf 'chore(extract-cognition): bump index to 0.2.0, add learning-goal evals\n\nassertions: playbook in mode A, every move anchored (F6), moves\ntransferable (F7), generator section present, no attribution without\nbaseline.\n\nCo-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>')"
```

---

### Task 6: 全量测试 + eval 重跑验证

**Files:**
- 只读验证 + 产出 `skills/experiment/extract-cognition-workspace/iteration-N/`（gitignored）

**Interfaces:**
- Consumes: 重写后的完整 skill。

- [ ] **Step 1: 跑仓库测试**

Run: `cd /Users/harveyzhang96/Projects/harveyz-skill && npm test 2>&1 | tail -20`
Expected: skills.bats 全绿（含 extract-cognition）。注：forge-doc `test_md_to_pdf.py` 的 `ModuleNotFoundError: markdown` 是**既有的、与本次无关的**失败，记录但不在本计划范围内修。

- [ ] **Step 2: 重跑 eval（skill-creator harness）**

按 spec §11：baseline = 旧 skill 快照（`2-descriptive.md` 版，先 `cp -r` 快照），with_skill = 新版。对 evals.json 用例各跑 with_skill 与 baseline，grader 子任务按 Task 5 断言判定，aggregate 出 benchmark。

- [ ] **Step 3: 判定**

Expected: 新版在 5 条学习目的断言上显著优于旧版快照（旧版无学习层，`playbook_in_mode_a`/`every_move_has_anchor`/`generator_section_present` 应 baseline 失败、with_skill 通过）。若某断言 with_skill 失败，记录缺陷，回到对应 Task 修 SKILL.md 后重跑（iteration-2）。

- [ ] **Step 4: 汇报**

向用户汇报 benchmark 对比与文件路径；交由 finishing-a-development-branch 决定合并。

---

## Self-Review

**1. Spec coverage：** spec §1 目的之变→Task1 Step1-2 + 全局；§2 两层架构→Task1 Step3 文件映射；§3 管线重瞄（读姿/取消丢弃/新阶段/基线翻转）→Task2 Step2/4 + Task3；§4 发生器优先手册结构→Task3 Step3；§5 动作卡 schema+鸡汤锁→Task3 Step1；§6 --pass/模式→Task1 Step3-4；§7 输入降级→Task1 Step4；§8 上限声明→Task3 Step4；§9 F6/F7→Task4 Step3；§10 落地（index/version/desc）→Task1 Step1 + Task5；§11 eval→Task5 + Task6；§12 YAGNI（无交互陪练）→未引入，符合。无遗漏。

**2. Placeholder scan：** 各步给出精确文件名、grep 校验命令、commit 文案；精确内容（schema/结构/上限声明/description）或内联或明确指向 spec §N 照搬。无 TBD/含糊。

**3. Type consistency：** 文件名全程统一为 `1-evidence.md`/`2-signature.md`/`3-playbook.md`/`4-attribution.md`；阶段号统一为 1–8（5=生成式重建、6=发生器蒸馏、7=归因、8=自审）；动作卡七栏名与 spec §5 一致。Task2/4 含 grep 反向校验旧名清除。

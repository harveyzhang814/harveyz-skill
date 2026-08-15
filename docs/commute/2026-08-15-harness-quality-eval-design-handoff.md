# 交接：继续 skill 跨平台 harness 的质量评估设计讨论

**日期**：2026-08-15
**author 模型**：claude-opus-5
**状态**：执行中 <!-- 待执行 → 执行中 → 待验收 → 已验收 / 打回 -->
**交接目的**：把一轮设计讨论的背景、现状与已达成的决策交给新 session，由它把剩下四个未决问题讨论完、产出定稿 spec。这是设计续做，不是实现。

> **接手方须知**：你正在接手一个任务。本文档是完整交接与唯一权威入口：从头读到尾，按「工作流约定」开工，完成后等原 session 按「最小验收锚点」验收。

---

## 最小验收锚点

软判据。达成的标准是：

**「仍待定的四件事」全部有明确结论，据此产出定稿 spec 并经用户 review 通过，且过程中没有推翻本文「关键决定」中的任何一条——除非拿到了新证据并在 spec 里写明推翻理由。**

判断依据不是"讨论得热不热闹"，而是：四件事逐条有结论、spec 落盘、用户说通过。

---

## 背景与现状

用户维护 41 个 skill，通过 `hskill` 发布到 7 个 agent 平台，但**装完之后没有任何验证手段**。为此做一套跨平台 harness 测试框架。

### 已经完成的

**第一期已实现、已验收、已合入 staging。** 三个平台（claude / pi / hermes）× 两种模式（native / inject）能跑起来，产出结构一致的 `RunRecord`，jail 隔离有效。原 session 做过独立复核，7 条硬判据逐条实跑通过（含真实模型 E2E 7/7）。代码在 `tools/skill-harness/`。

第一期解决的问题是「**装得上、认得出、读得到自己的文件吗**」。

### 当前所处的位置

原本 spec 规划的第二期是「过程评估 + 方差标定 + 对比报告」。**这一期已决定取消**（理由见「关键决定」第 1 条）。方向改为**直接做质量评估**。

正在走 `superpowers:brainstorming` 的架构路径，已完成：探索上下文 → 澄清问题 → 达成若干决策。**还没到"提出 2-3 个方案"和"分段呈现设计"这两步**，也没写定稿 spec。

讨论结论已落盘为 `docs/superpowers/specs/2026-08-15-skill-harness-phase2-decisions.md`，顶部标了「设计进行中，未定稿，不要据此实施」。**定稿后应把它合并回上游 spec 并删除该文件。**

### 一条必须知道的事实

第一期的 `RunRecord` **只保留了 `reply` 和 `toolCalls`，原始 transcript 被丢弃了**。这是质量评估落地时必须先补的一环，理由见「关键决定」第 5 条。

---

## 关键决定（别改动）

这些是讨论中已达成的结论。接手方若不知道，极可能重走已经走死过的路。

### 1. 第二期取消，直接做质量评估

讨论中第二期的目标被**连续换了三次**，每次都因不成立被推翻。换三次说明的不是某个细节没想清，是**这个阶段本身没有稳定目标**——它一直在找一个「比质量评估容易、又比第一期有信息量」的中间态，而这个中间态不存在。

三次尝试各自的致命伤，**务必不要重走**：

| 尝试过的方案 | 为什么不成立 |
|---|---|
| 负向断言打在工具名上（`forbid`/`require`/`order`） | 测的是「有没有碰不该碰的东西」，与「有没有按流程走完」不是一回事；且三平台工具名不同（claude `Read` / pi `read` / hermes 另一套），断言跨平台不可比 |
| 步骤合规（从 SKILL.md 抽步骤清单逐步判定） | 多数步骤不产生特征性工具调用（"等待 Subagent 完成"、"向用户报告结果"）；41 个 skill 中 14 个无显式步骤结构；条件步骤（`步骤 4.5：仅在…时执行`）会产生大批假失败 |
| 过程错误分类（固定分类当行） | 三平台错误信号能力不对等——hermes 的 trace 无 `result` 事件，运行级信号全缺。「hermes 零错误」可能只是它报不了错，这种伪影看起来极其可信 |

**决定性理由**：过程错误是**回溯工具**，不是判据。只有当质量出了问题、要追「哪儿断的」时才需要它。为回溯工具单独立一期、还要为它建分类学和方差标定，是把辅助手段当成了目的。

### 2. 质量声明外置，框架只消费不生产

**框架不承担「为 41 个 skill 编写判据」这个工程。**

- 每个 skill 事先备一份质量声明；可人工标注，也可让另一个 LM 抽取
- **抽取动作不在检测框架内**，框架只负责引用与消费
- 声明写一次、review 一次、冻结，之后作为固定量具使用

### 3. 复用已有的 evals.json，不新造格式

仓库已有 `skills/<cat>/<name>/evals/evals.json`，4 个 skill 在用（`coding/handoff`、`mint/learn-skill`、`research/extract-cognition`、`coding/setup-debug`）。

现有字段：`{ skill_name, evals: [{ id, name, prompt, expected_output, files, assertions }] }`

### 4. 判定粒度统一用 `assertions` 数组，每条独立判定

现状不统一：`handoff` 用一整段自然语言 `expected_output`，`learn-skill` 用 `assertions` 数组（5 条独立断言）。

**统一成数组**。理由是跨平台对比需要**固定的行**：

```
learn-skill            claude   pi     hermes
断言 1 四维且哲学在先      ✓      ✓       ✓
断言 2 无评分标签         ✓      ✗       ✗
断言 3 无额外评估段落      ✓      ✓       ✗
断言 4 主体中文           ✓      ✓       ✓
断言 5 结尾收尾问句        ✓      ✗       ✓
```

整段 `expected_output` 只能得到二元结果，看不出差在哪一条——而「差在哪一条」正是整套框架要产出的东西。

### 5. 完整 transcript 必须落盘，但不建任何分析器

回溯工具可以不建，但**原料不能不存**——否则将来质量出问题想追「哪儿断的」永远追不了，而重跑要花钱。存原始 JSONL 是零成本纯 I/O，不写一行判定逻辑。

**这是唯一一件「现在不做就再也补不上」的事。**

### 6. 方差标定不跳过，改为直接标定质量判定本身

上游 spec 原安排是「第二期标定过程指标 → 第三期再赌质量指标」，中间有断层：标定的东西和最终使用的东西不是一回事。

改为：**同一格重复跑 5 次，看 grader 的判定稳不稳**。不稳说明该指标没有区分度，应换指标而非加样本。

### 7. 质量声明需要返修回路

声明若由 LM 抽取，它抽的是 **skill 的「应然」**，而 skill 本身可能写得不好。此时评估实际在问的是「它有没有照着一份可能有问题的说明书做」。

**后果**：首轮跑出的差异中，一部分会指向「声明写错了」而非「平台有问题」。

**处置**：流程中必须留一个**声明返修回路**——首轮跑完人工过一遍声明，之后才能当量具用。否则会把声明缺陷记成平台缺陷，且看起来会很像真的。

### 8. 从第一期继承、不得违反的纪律

- **模型必须 pin**。三平台默认模型不同（claude `claude-sonnet-5`，pi 和 hermes 都是 `MiniMax-M2.7`），不 pin 则「跨平台差异」实为平台⊗模型混合效应。已验证 claude 可经 `ANTHROPIC_BASE_URL` 指向兼容端点跑同一模型。
- **报告三态**：`unavailable` 不得渲染成 `0`，也不得渲染成 `✓`；未跑的格子渲染成空格。没有 residual 的归因表一定在撒谎。
- **`builtinSkillFloor` 是「平台 × 模型/认证」的函数，不是平台常量**。实测：OAuth + sonnet 下 claude 有 16 个内置 skill，MiniMax 端点下 15 个（差 `schedule`，被门控）。

---

## 仍待定（这就是接手方要做的事）

四件，逐条讨论出结论：

1. **grader 怎么跑、跑在哪、用什么模型。** 必须与被测平台的模型解耦，否则又引入一个混淆变量。
2. **grader 的输出结构。** 上游 spec 已指向 skill-creator 方法论的 `text` / `passed` / `evidence` 字段名（见 `docs/explanation/skill-creator-testing-system.md`），待确认是否沿用。
3. **41 个 skill 的质量声明如何分批产出与 review。** 目前只有 4 个 skill 有 evals.json，且格式不统一。
4. **报告形态。** 如何在「断言 × 平台」矩阵上保持三态纪律。

讨论完这四件后，按 brainstorming 的架构路径继续：提出 2-3 个方案 → 分段呈现设计 → 写定稿 spec → 用户 review → 才能进 writing-plans。

---

## 范围铁律

**In：** 把上面四件待定事项讨论出结论，产出定稿 spec。

**Out：**

- **任何实现**。不写代码、不改 `tools/skill-harness/` 下任何文件、不调用 writing-plans 之外的实现类 skill
- **重开「关键决定」里已定的事**，除非拿到新证据——尤其不要重新提议做过程评估/步骤合规/工具名负向断言，那三条路都走死过
- **为 41 个 skill 批量编写质量声明**。这是定完设计之后的事，且抽取动作不属于框架
- **修改上游 spec `2026-08-14-skill-harness-adapter-design.md`**，直到定稿时统一合并

---

## 相关文档索引

| 路径 | 用途 |
|---|---|
| `docs/superpowers/specs/2026-08-15-skill-harness-phase2-decisions.md` | **本次讨论的决策记录**，含三次失败尝试的完整分析。定稿后合并回上游 spec 并删除 |
| `docs/superpowers/specs/2026-08-14-skill-harness-adapter-design.md` | 上游 spec。注意其「过程评估」「分期·第二期」两节已被本次讨论作废，但文件尚未改 |
| `docs/commute/2026-08-14-skill-harness-phase1-handoff.md` | 第一期交接与两轮验收记录（接手方自报 + 原 session 独立复核） |
| `docs/superpowers/specs/measurements/2026-08-14-native-vs-inject.md` | 全部平台实测记录与复现命令，含三平台轨迹字段表 |
| `docs/superpowers/plans/2026-08-14-skill-harness-phase1.md` | 第一期实施计划，15 个 task |
| `docs/explanation/skill-creator-testing-system.md` | skill-creator 的 eval 方法论，待定事项 2 的参考 |
| `tools/skill-harness/` | 第一期实现，13 个模块 |
| `skills/mint/learn-skill/evals/evals.json` | `assertions` 数组格式的样例（决定 4 采纳的形态） |
| `skills/coding/handoff/evals/evals.json` | 整段 `expected_output` 格式的样例（决定 4 要改掉的形态） |

---

## 工作流约定

1. **本次讨论的产物在 worktree `.claude/worktrees/harness-accept`，分支 `doc/harness-accept-record`。** 上表里的 `2026-08-15-skill-harness-phase2-decisions.md` 和本文档**只存在于这条分支**，staging 上没有；spec 的 `builtinSkillFloor` 修正也只在这条分支。要读全须在此分支上。

2. **该分支有 4 个未合入 staging 的提交**，基于 `e246e15`。**staging 动得很快**（多个 session 并行往里合，本文写就时已到 `64d5175`，中间隔了至少一个 release）。要合并前必须先同步。

3. **不要 merge 到 staging**，除非用户明确说「合并」或「完成」。合并时用 `--no-ff`。

4. **不要新建分支**。仓库约定是一个功能/迭代用一个分支，积累所有相关改动。

5. **commit message 受 hook 强制**：Conventional Commits，类型限 `feat|fix|chore|docs|refactor|test|style|perf`，**首行 ≤ 80 字符**。

6. **git stash 栈与主仓和其他 worktree 共享**。不要用裸 `git stash` / `git stash pop`，会弹到别人的改动。

7. **brainstorming 的硬门禁**：设计未经用户批准前，不得调用任何实现类 skill、不得写代码。架构路径的唯一后继是 `superpowers:writing-plans`，且必须在用户 review 定稿 spec 之后。

---

## 接手方 verify 核对结论（2026-08-15）

结论：**通过，可开工。** 交接目的、验收锚点、8 条关键决定、范围铁律均自洽；相关文档索引 9 条路径逐条核实存在。

一处失效，已处置：

- 「工作流约定」第 1、2 条描述的状态已过期——`doc/harness-accept-record` 已 merge 进 staging（`8d2bacb`），worktree `.claude/worktrees/harness-accept` 已删除。**索引里的 9 个文件现在全部在 staging 上可读**，内容未丢失，仅取用方式变化。
- 连带第 4 条「不要新建分支」失去指向对象。接手方新建 `doc/harness-quality-eval-design`，本轮全部产物在该分支积累，仍遵守「一个迭代一条分支」。

---

## author 冷读核对结论

- 交接目的、最小验收锚点：均在。锚点是软判据（设计续做型），判断标准已写明为「四件逐条有结论 + spec 落盘 + 用户通过」，不是"讨论得好"这种无法判定的说法。
- 相关文档索引 9 条路径：已在 `doc/harness-accept-record` 分支上逐条 `ls` 核实存在。
- 关键决定 8 条：覆盖了本轮全部结论，含三次失败尝试的致命伤，接手方无需回问原 session。
- 范围铁律：in/out 均点名，特别点出"不要重新提议那三条走死的路"。
- 反向检查：补写了「工作流约定」第 1 条——若漏掉，接手方很可能在 staging 上找不到决策记录，误以为文档不存在或已丢失，这是最可能踩的坑。另补写了「背景与现状」里 transcript 未落盘这一条，它是决定 5 的现实依据，漏掉会让该决定显得凭空。

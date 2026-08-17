# Skill 跨平台 Harness · 质量评估 — design

**Date:** 2026-08-17
**状态:** 定稿，待 writing-plans
**上游 spec:** [2026-08-14-skill-harness-adapter-design.md](2026-08-14-skill-harness-adapter-design.md)
**第一期:** 已完成并验收，见 [../../commute/2026-08-14-skill-harness-phase1-handoff.md](../../commute/2026-08-14-skill-harness-phase1-handoff.md)
**取代:** 上游 spec 的「过程评估」「质量评估（第三期）」两节，及「分期与验收」中的第二、三期

主线：**同一个 skill 在三个平台上跑出来的差异，只有落到「哪一条断言上不一样」才有用；落到「谁分高谁分低」没用。** 这份 spec 的每个决定都可以拿这句话去验。

---

## 定位

第一期回答的是「装得上、认得出、读得到自己的文件吗」，跑出来的是一张 skill × 平台的 pass/fail 表。它测的是安装与识别，不是行为。

这一期回答「跑起来之后做得对不对」。没有它，41 个 skill 发布到 7 个平台之后，唯一能确认的仍然只是"没崩"。触发场景是：改了一个 skill，或者接入一个新平台，想知道它在各平台上的行为是不是还一致。

**取消原第二期。** 原本规划的中间阶段是「过程评估 + 方差标定 + 对比报告」，直接跳过，理由见下一节。

---

## 为什么不做过程评估

设计讨论中这一阶段的目标被换了三次，每次都因不成立被推翻。换三次说明的不是某个细节没想清，是这个阶段本身没有稳定目标——它一直在找一个「比质量评估容易、又比第一期有信息量」的中间态，而这个中间态不存在。

三次尝试各自的致命伤，留作记录，避免日后重走：

| 方案 | 致命伤 |
|---|---|
| 负向断言打在工具名上（`forbid`/`require`/`order`） | 测的是「有没有碰不该碰的东西」，与「有没有按流程走完」不是一回事；且三平台工具名不同，断言跨平台不可比 |
| 步骤合规（从 SKILL.md 抽步骤清单逐步判定） | 多数步骤不产生特征性工具调用（"等待 Subagent 完成"、"向用户报告结果"）；41 个 skill 中 14 个无显式步骤结构；条件步骤会产生大批假失败 |
| 过程错误分类（固定分类当行） | 三平台错误信号能力不对等——hermes 的 trace 无 `result` 事件，运行级信号全缺。「hermes 零错误」可能只是它报不了错，这种伪影看起来极其可信 |

**决定性理由：过程错误是回溯工具，不是判据。** 只有当质量出了问题、要追「哪儿断的」时才需要它。为回溯工具单独立一期、还要为它建分类学和方差标定，是把辅助手段当成了目的。

**代价：** 放弃了一条比质量评估便宜得多的信息通道。约束性指令（"不要"、"先…再…"）的跨平台遵守度差异，本来一次运行就能出确定结论，不需要 grader、不需要消除方差。这条通道被关掉了，换来的是不再维护一套跨平台不可比的断言。回溯需求靠下面的原料落盘兜底，而不是靠分析器。

---

## 五个组成部分

```
run 阶段                          grade 阶段（离线）              report 阶段
+----------------+               +------------------+           +--------------+
| runMatrix      |  artifacts    | claude -p        | gradings  | 断言 x 平台  |
| + 采集层  (1)  | ------------> | grader 契约 (3)  | --------> | 矩阵    (4)  |
+----------------+               +------------------+           +--------------+
                                          ^                            |
                                   evals.json (2)                      v
                                   质量声明                     方差标定/返修 (5)
```

谁不信任谁：**grade 阶段不信任 run 阶段的内存**，只读落盘产物；**report 阶段不信任 grader 的自我报告**，grader 判不了必须显式说，说不清就是 `unavailable`。

---

## 1. 采集层

**这是唯一一件现在不做就再也补不上的事。** 其余四部分随时可以补，原料丢了只能花钱重跑。

第一期的 `RunRecord` 只留了 `reply` 和 `toolCalls`，原始轨迹被丢弃。实际情况比这更严重：**被测 agent 产出的文件也一起没了**。`runner.js:154` 的 `finally` 调 `jail.js:34` 的 `fs.remove`，整个 jail 连同 agent 写出的文件被删，删之前没有任何东西往外捞。而质量声明要判的东西——learn-skill 的四维报告、handoff 的交接文档——恰恰是文件，不是 `reply`。

**新增落盘布局：**

```
~/.hskill/skill-harness/<runId>/
  records.json          # 不变
  cells.json            # 不变
  cells/<skill>__<platform>__<mode>__r<repeat>/
    transcript.jsonl    # adapter 拿到的 raw，含 hermes 从 collect 通道 export 回来的那份
    stdout.log  stderr.log
    artifacts/          # agent 在 jail 里产出的文件
```

**产出物靠文件清单差集识别，不用启发式。** `install` 之后、spawn 之前对 jail 做一次快照（路径 + mtime + size），跑完取差集，只捞新增和修改的。这样内置 skill 的副本、session 目录、认证文件都不会被抄出来。

**时序**：采集必须在 `runner.js` 那个 `finally` 之前完成。此时被测运行已结束，所以采集异常**不得把该格判成 fail**——采集不到就在 record 里记明，该格的产出物类断言后续判为 `unavailable`。把采集故障记成被测方的质量问题，正是这套框架最该避免的那类伪影。

**代价：** 每格多一次全目录遍历和一次文件拷贝，磁盘占用从两个 JSON 涨到每格一个目录。transcript 设字节上限，超限截断并在 record 里记 `truncated: true`——截断了却不说，等于把一份不完整的原料当完整的用。

**已实测：pi 不重定向 HOME。** 2026-08-17 曾把 `adapters/pi.js:12` 的 `jailEnv` 改成重定向 HOME 到 jail 目录后实测：pi 认证 minimax-cn 失败（`exitCode 1`，stderr 为 `No API key found for minimax-cn`）；同一条命令换回真实 HOME 能正常认证并拿到 reply，排除了「只是没配 key」这个混淆因素——pi 把凭证存在 `$HOME/.pi/agent/auth.json`，重定向后这份凭证读不到。本仓库既定约定是 skill 把产出写到 `$HOME/.hskill/<skill-name>/` 和 `~/Documents/notes/`——pi 保留真实 HOME 意味着这类产出物写进真实用户环境、也捞不进 jail，代价已知并接受：`piProfile.artifactChannel` 定为 `'none'`，pi 这一列只能靠 `reply` 判，产出物类断言对 pi 全部是 `unavailable`，且必须如实这么渲染，不能算 fail。

---

## 2. 质量声明格式

框架不承担「为 41 个 skill 编写判据」这个工程。声明外置：可人工标注，也可让另一个 LM 抽取，**抽取动作不在框架内**，框架只引用与消费。

复用仓库已有的 `skills/<cat>/<name>/evals/evals.json`，不新造格式。改动集中在 `assertions`：

```json
{
  "skill_name": "learn-skill",
  "evals": [{
    "id": 1,
    "prompt": "...",
    "expected_output": "...",
    "files": ["skills/meta/contribute-skill/SKILL.md"],
    "frozen": "2026-08-17",
    "assertions": [
      { "id": "philosophy-first",
        "text": "报告包含四个维度，且设计哲学是第一个出现的维度标题",
        "source": "artifact",
        "na_platforms": [] }
    ]
  }]
}
```

**`assertions` 从裸字符串数组改成对象数组，每条带稳定 `id`。** 判定粒度统一用数组、每条独立判定，因为跨平台对比需要固定的行——整段 `expected_output` 只能得到二元结果，看不出差在哪一条，而「差在哪一条」正是整套框架要产出的东西。`id` 是跨 runId 对齐行的锚：措辞改了行不断，改 `id` 等于换了一条断言。

**`source` 是成本闸门**，取值 `reply | artifact | transcript`，默认 `reply`。它决定 grader prompt 里塞什么。

**三个取值是累进层级，不是互斥集合**：`artifact` 意为 reply 加产出物，`transcript` 意为 reply 加产出物加轨迹。这样一条同时需要 reply 和产出物的断言不必拆成两条，也不必把字段做成数组。`transcript` 最贵，必须显式声明才喂——否则一次全矩阵评估会把几百份 JSONL 塞进 grader，而绝大多数断言根本用不上。

**`na_platforms` 带 reason**，接上 `report.js:68` 已有的 `declared-na` 态，不新造机制。

**`expected_output` 保留但不参与判定**，照 skill-creator 的定位当人读的描述。

**代价：** 声明格式变了，已有 4 个文件要迁移，且迁移是人工的——`id` 只能由人或 LM 生成一次后冻结，没有自动化路径。

**四份已有声明的实际状态各不相同**，迁移工作量差别很大：

| 文件 | 现状 | 要做的 |
|---|---|---|
| `research/extract-cognition` | `skill_name` 正确，`assertions` 已是带 `id` 的对象数组 | 只补 `source` 与 `frozen` |
| `mint/learn-skill` | `skill_name` 腐烂成 `inspect-skill`；`assertions` 是裸字符串数组 | 改名 + 包成对象 + 补字段 |
| `coding/setup-debug` | `skill_name` 腐烂成 `full-stack-debug-env`；无 `assertions` | 改名 + 新写断言 |
| `coding/handoff` | `skill_name` 正确；四个 eval 全无 `assertions`，只有整段 `expected_output` | 新写断言 |

两处 `skill_name` 腐烂都是改名后没同步声明留下的，正是「声明会跟着 skill 一起腐烂」的实例。

`learn-skill` 那份里 3 个 eval 的 5 条断言完全重复——**不做 `$ref` 共享机制**，重复几十行 JSON 不是问题，为它造引用机制才是过度设计。断言 `id` 的唯一性只在单个 eval 内要求，跨 eval 同名不冲突（`extract-cognition` 已经在这么用）。

**不引入 fixture seed 机制。** 现有 `files` 和 prompt 里写的是宿主机绝对路径。jail 只重定向 HOME，不挡文件系统读取，所以照样读得到。只做一件事：**把 `files` 列的文件纳入该 eval 的 contentHash**，被测输入一变就判 stale。代价是 eval 绑死在这台机器的路径上，换机器要改；换来的是零新机制解决了「评的是移动靶」。

---

## 3. grade 子命令与 grader 契约

```
node tools/skill-harness/cli.js grade <runId> [--grader-model M] [--only <skill>]
```

离线读 `<runId>/`，写 `<runId>/gradings.json`。可重复跑、可只重判一个 skill。

**离线而非内联，是为了让「改断言」和「重跑被测运行」解耦。** 内联的话，grader 失败会污染被测记录，改一句断言措辞就要重跑一遍花钱的被测运行，并发控制也纠缠在一起。代价是多一次 artifact 往返，以及 jail 已删、只能读采集层捞出来的东西——这正是第 1 部分存在的理由。

**评谁**：只评同时满足两条的格子——第一期该格是 `pass`，且该 skill 有声明。其余不评，也不当 fail。

**grader 跑在哪**：`claude -p`，跑在 `createJail()` 出来的空 jail 里，`claudeAdapter.jailEnv` 提供认证，**不装任何 skill**。不隔离的话宿主 `~/.claude/skills` 那 41 个会被加载，grader 可能被自己要判的 skill 触发，判定不可复现。

**自指防护**：`--grader-model` 必填并写进 `gradings.json` 头部。若它等于被测模型，报告顶部打警告——*量具与被测物同模型，差异可能是自指伪影*。

**代价（明说）：** 复用 claude CLI 意味着 claude 既是被测平台之一，又是量具。CLI 层的耦合退不掉：claude CLI 挂了，三个平台一起判不了。换来的是零新代码——不必写 HTTP client 和 key 管理。模型层的耦合靠上面那条 pin 退掉，这是这个选择唯一能对冲的部分。

**调用粒度**：一个 `(cell, eval)` 一次调用，一次判完该 eval 的全部断言。按断言逐次调用会把成本乘上断言条数。

**输出契约：**

```json
{ "runId": "...", "graderModel": "...", "subjectModel": "...",
  "gradings": [{
    "skill": "mint/learn-skill", "platform": "pi", "mode": "native",
    "repeat": 0, "evalId": 1,
    "assertions": [
      { "id": "philosophy-first", "verdict": "pass", "evidence": "<引原文片段>" }
    ] }] }
```

沿用 skill-creator 的 `text` / `evidence` 字段名，**但把布尔 `passed` 换成三态 `verdict: pass | fail | unavailable`**。第一期立的纪律要求 `unavailable` 不得渲染成 `0` 也不得渲染成 `✓`，而布尔值无处安放它。**不存 `summary.pass_rate`**——存了就会把三态压平。

**三态在 grader prompt 里必须是个真出口。** 明确告诉 grader：材料不足以判定时输出 `unavailable` 并说明缺什么。不给这个出口，被迫二选一的 grader 会编证据。这是 `unavailable` 的主要价值，不只是给报告用的渲染标记。

**失败时序**：解析失败重试一次；仍失败则该 eval 全部断言标 `unavailable`，evidence 记 `grader output unparseable: <tail>`。量具坏了要看得出来，不能静默算 fail。

**代价：** 沿用了字段名但改了 `passed` 的类型，skill-creator 现成的 eval viewer 和 `aggregate_benchmark.py` 不能直接用，报告要自己渲染。

> **未确认：** 一次调用判整条断言清单的输出稳定性，没实测。这正是第 5 部分要标定的东西——若不稳，先试拆小调用粒度再考虑换指标。

---

## 4. 报告形态

单一断言级矩阵。行按 skill 分组，组内首行是上游状态，其余是断言；列沿用现有 6 个 `platform/mode` 组合。

```
learn-skill            claude/n  claude/i  pi/n      pi/i      hermes/n  hermes/i
  [upstream]           pass      pass      pass      pass      fail      fail
  philosophy-first     pass      pass      pass      fail      .         .
  no-score-labels      pass      pass      fail      fail      .         .
  zh-body              pass      pass      pass      pass      .         .
  closing-question     unavail   pass      pass      n/a       .         .

legend: .  = blocked-upstream, 见本组 [upstream] 行
        (空) = not-run    n/a = 声明排除    unavail = 判不了    ~ = unstable
```

`[upstream]` 行就是第一期矩阵，降级成每个 skill 的前置检查行。

**放大伪影在这里被堵住**：hermes 装不上时断言行填 `.` 而不是 `fail`，**且计数按 `(skill, platform, mode)` 计一次，不按断言条数计**。渲染上重复出现无法避免，计数必须去重——否则断言写得多的 skill 权重就大，一次安装失败被放大成 N 条质量失败，平台差异变成断言条数的函数。

**计数行只打各态数量，不打 pass_rate。** 一个合成出来的比率太容易被单独摘出去引用，而它的分母里藏着"排除了多少 unavailable、多少 blocked"这些恰恰最该被看见的东西。

**第一期的尾部归因段落全部保留**（`builtinSkillFloor`、`model mismatch`、`unavailable fields`、`declared n/a`、`platform notes`），降级的是矩阵层，不是归因层。新增三段：

```
无声明 skill (37): meta/init-skill, coding/ship, ...
grader: model=<grader>  subject=<subject>
unstable assertions (2): learn-skill/closing-question@pi/native, ...
```

**`无声明 skill` 是稀疏矩阵的必需品**——最大的风险是把"没测"静默渲染成"没问题"。它和 `not-run` 是两回事：一个是没写量具，一个是有量具没跑，都得显式列出来。

**代价：** 报告变宽变长，一屏放不下一个 skill 的全部断言 × 6 列。两层语义（能不能跑 / 跑得对不对）挤在一张表里，读的时候要先看 `[upstream]` 行再看断言行。

---

## 5. 方差标定与声明返修回路

上游 spec 原安排是「第二期标定过程指标 → 第三期再赌质量指标」，中间有断层：标定的东西和最终使用的东西不是一回事。改为**直接标定质量判定本身**。

**标定**：`--repeat 5` 同格重复，grade 后按 `(skill, platform, mode, evalId, assertionId)` 聚合五次 verdict。五次一致为稳定；有分歧标 `unstable`。

**`unstable` 断言不参与跨平台对比**，矩阵里渲染成 `~`，不算 pass 也不算 fail。一把自己会漂的尺子量出来的平台差异，分不清是平台差异还是尺子在漂。

**不稳的处置是换指标，不是加样本。** 加样本只能把噪音平均掉，指标本身没有区分度这件事不会因此改变——平均完得到的是一个更精确的、无意义的数。

**返修回路**：声明若由 LM 抽取，它抽的是 skill 的「应然」，而 skill 本身可能写得不好。此时评估实际在问的是「它有没有照着一份可能有问题的说明书做」。首轮跑出的差异中，一部分会指向「声明写错了」而非「平台有问题」。

两类信号触发人工过声明，它们在报告尾部单列，就是返修的工作清单：

1. **`unstable` 断言**——多半是断言写得含糊，grader 每次读出不同意思。
2. **全平台一致 fail 的断言**——「声明写错了」的最强信号。三个平台、三套实现同时错在同一条上，量具有问题的先验高于三家同时踩同一个坑。

**冻结用显式字段**，eval 级 `"frozen": "<date>"`。未冻结的声明，报告顶部警告*该 skill 的声明尚未 review，其平台结论不可引用*。不显式挡一道，首轮那批数据一定会被当成结论用出去。

**与增量覆盖合上**：skill 改动 → contentHash 变 → 该 skill 的声明自动解冻并标 stale，需重新 review 才能再冻结。`learn-skill` 那份 `skill_name` 写成 `inspect-skill` 的 evals.json 就是没有这道闸门的结果。

**代价：** 每格跑 5 次，被测运行成本乘 5，grade 成本也乘 5。这是标定期的开销，标定完成后可降到每格 1-2 次；但每次接入新平台或换被测模型，标定要重来。

---

## 覆盖策略

**按需增量，不预先分批。** 哪个 skill 被改动或出了问题才为它写声明，复用已有的 contentHash staleness 机制。冷启动覆盖不为零——已有的 4 份 evals.json 迁移成新格式即是初始覆盖。

**代价（明说）：** 跨平台对比矩阵永远是稀疏的。任一时刻都有大量 skill 没有声明，横向对比只能在有声明的子集上做。这是这条路线的固有性质，靠报告里的 `无声明 skill` 清单如实暴露，不靠机制消除。

**因此加一条硬约束：对比只在同一 runId 内做。** 稀疏加跨 runId 比较，等于比不同时间点的不同批次，差异归因不成立。

---

## Non-goals

- **不建任何过程分析器。** 原料落盘，分析器不建。
- **不为 41 个 skill 批量编写声明。** 抽取动作不属于框架。
- **不做 with_skill / without_skill 对照。** skill-creator 那套换的是对照轴，这里的轴是 platform_A vs platform_B，不是有无 skill。
- **不复用 skill-creator 的 viewer 和聚合脚本。** 三态改动使其不兼容。
- **不引入 fixture seed 机制。**
- **不做 `$ref` 断言共享。**

---

## 风险

**1. claude CLI 是量具又是被测物。** CLI 挂了三个平台一起判不了。缓解只到模型层 pin，CLI 层无缓解。已知并接受。

**2. 声明缺陷会被记成平台缺陷，且看起来很像真的。** 靠 `frozen` 字段 + 返修回路的两类信号挡。挡不住的部分：声明写得含糊但恰好每次都被 grader 读成同一个意思——这类既不 unstable、也不全平台 fail，会静默通过。

**3. 稀疏矩阵被当成完整矩阵读。** 靠 `无声明 skill` 清单暴露。这是渲染纪律，没有机制强制。

**4. pi 不重定向 HOME，产出物类断言对它全不可用。** 2026-08-17 实测确认 pi 在重定向 HOME 下认证失败（见第 1 部分），故保留真实 HOME、`artifactChannel: 'none'`。后果是 pi 一整列降级到只判 `reply`，产出物类断言对 pi 全部是 `unavailable`，不能算 fail。已知并接受。

**5. 采集层的文件清单差集可能捞进平台自己写的状态文件。** 各平台在 jail 内写什么没有逐一核对。后果是 artifacts 里混入噪音，grader 判定被干扰。缓解：首轮人工看一眼捞出来的东西，按平台加排除规则。

---

## 验收

硬判据，逐条实跑：

1. 一格跑完后，`cells/<...>/` 下有 `transcript.jsonl` 和 `artifacts/`，且 `artifacts/` 内容等于 agent 实际写出的文件——用一个会写文件的 skill 验证，不用 anchor probe。
2. jail 已被删除（`fs.remove` 已执行）的前提下，`grade <runId>` 仍能完整跑完。
3. 4 份已有 evals.json 迁移成新格式，`skill_name` 与目录名一致，每条断言有唯一 `id`。
4. `grade` 对一个产出物缺失的格子输出 `verdict: unavailable`，不是 `fail`。
5. 喂给 grader 一份故意坏掉的输出，其解析失败路径产出全 `unavailable` + 可读的 evidence，不是静默 fail。
6. 某 skill 在某平台 `[upstream]` 为 fail 时，其断言行渲染为 `.`，且计数里该 `(skill, platform, mode)` 只被计一次。
7. `无声明 skill` 清单条数 + 有声明 skill 条数 = 本次矩阵覆盖的 skill 总数。
8. `--repeat 5` 下，verdict 有分歧的断言被标 `unstable` 并出现在尾部清单，矩阵格渲染为 `~`。
9. `--grader-model` 等于被测模型时，报告顶部出现自指警告。
10. `npm test` 全绿。

---

## 未确认项汇总

| 项 | 档位 | 后果 |
|---|---|---|
| pi 在 HOME 重定向下能否认证 | 已查，认证不通 | pi 一整列降级到只判 `reply` |
| 一次调用判整条断言清单的输出稳定性 | 已查，`--repeat` CLI 参数本身是死代码（解析后从未被消费，实测 `--repeat 5` 只跑出 1 格），已改用「5 次独立 run 手动合并成一个 runId」的方法绕过，真实跑出 `unstable: 14`（15 个 skill×evalId×assertionId 组合里 14 个不稳，1 个稳）。归因：约 12/14 来自 5 次重复里有 1 次的模型行为本身就质变（`Skill` 工具触发但回复过短、材料不足以判），另 1 处是同一份材料仅换 eval 场景文本、grader 判定就翻面的真实量具噪声。结论见 [measurements/2026-08-17-quality-eval-e2e.md#step-5-unstable-标定](measurements/2026-08-17-quality-eval-e2e.md) | `--repeat` 死代码是新发现的阻塞项，需要单独任务修；unstable 非零，按 spec「不参与跨平台对比」处理，不加样本硬平掉 |
| transcript 单份体积量级 | 已查，单轮单格实测范围 6.5KB（未触发的纯聊天）~ 约 260KB（触发深度多工具调查），全部远小于 `TRANSCRIPT_LIMIT`（4MB），未观察到任何截断。见 [measurements/2026-08-17-quality-eval-e2e.md#附-transcript-单份体积](measurements/2026-08-17-quality-eval-e2e.md) | 决定字节上限取值；截断比例过高则 `source: transcript` 不可用——本轮样本下不成立 |
| hermes 的产出物是否落在 jail 内 | 推出来的 | hermes 的 isolation 含 HOME 重定向（`profiles.js:39`），据此推断产出物在 jail 内，未实测 |
| 各平台在 jail 内自写哪些状态文件 | 没查 | 决定采集层是否需要按平台排除规则 |

---

## 源码锚点

| 位置 | 关系 |
|---|---|
| `tools/skill-harness/runner.js:154` | 采集层的插入点，`finally` 之前 |
| `tools/skill-harness/jail.js:34` | `cleanup` 即 `fs.remove`，产出物在此销毁 |
| `tools/skill-harness/adapters/pi.js:12` | pi 未重定向 HOME |
| `tools/skill-harness/record.js:12` | `makeRecord`，`unavailable` 数组的生产者 |
| `tools/skill-harness/report.js:10` | `cellStatus`，现有三态判定 |
| `tools/skill-harness/report.js:68` | `declared-na` 的现有渲染 |
| `tools/skill-harness/profiles.js` | 平台能力差异表 |
| `skills/mint/learn-skill/evals/evals.json` | 裸字符串断言 + `skill_name` 腐烂 |
| `skills/research/extract-cognition/evals/evals.json` | 已是对象数组，迁移的正面样例 |
| `skills/coding/handoff/evals/evals.json` | 只有整段 `expected_output`，决定 4 要改掉的形态 |
| `docs/explanation/skill-creator-testing-system.md` | 字段名来源 |

# brainstorming-zh 真实环境测试独立审计

审计对象为仓库源码 `skills/superpowers-rewrite/brainstorming-zh/SKILL.md` 0.1.27 和三个隔离场景的逐轮 transcript、原始 JSONL、最终产物及运行脚本。全程只读；本报告是唯一新增文件。三个场景中的用户均由测试者扮演，所有“批准”只证明模拟会话走过审批分支，不构成真实用户对产品的批准（各 `transcript.md:3`）。

## 确证问题

1. **获批后的状态记录未同步，追溯链自相矛盾。** exploratory 第 10 轮模拟用户明确批准“当前版本的 Spec”，且仅限现有文档（`scenarios/exploratory/transcript.md:329-335`）；记录 H04 标为已批准（`.../neighbor-lending-record.md:100-105`），但最终 Spec 头部仍写“初稿 v1，待用户审核”，D12–D25“尚待审核”（`.../neighbor-lending-spec.md:3-8`），尾部又写“待审核，H04”（同文件 `:300-301`）。defined 第 7 轮模拟用户批准完整 Spec（`scenarios/defined/transcript.md:229-245`），记录 A1/A2/A4 也称已批准（`.../snooze-reminder-record.md:40-48`），但同一记录的 R1–R9 仍为“待确认”（`:6-14`），I8、I9 行甚至同时写“已批准 A2”和“待确认”（`:37-38`）。这违反源码 `SKILL.md:70-72,91` 对审批状态和写 Spec 前核对记录的要求，可能使后续构建者误判审批范围。原始事件显示 exploratory 第 10 轮只编辑 record，未编辑 Spec（`logs/turn-10.jsonl`；`transcript.md:351-359`）。

2. **探索场景的短信次数有已批准要求与最终 Spec 的实质矛盾。** 模拟用户把 R13 改为“只在到期前 24 小时提醒一次”，重审后批准（`scenarios/exploratory/transcript.md:134-165`），最终 Spec 仍把它列为用户决定（`.../neighbor-lending-spec.md:289-291`）。但构建者自查加入 D16：改归还时间时，旧提醒已发则新建一条（`scenarios/exploratory/transcript.md:283-305`；最终 Spec `:146-150`），并在接口假设里继续按“每笔借用一条提醒”估算预算（Spec `:201-206`）。D16 后来随整份 Spec 获模拟批准，故不能称未获审批；问题是 Spec 没明确说明“仅一次”是每笔借用还是每次约定归还时间，旧短信已发后改期会产生第二条。按 `SKILL.md:91,101-105`，这种会改变短信数量和验收的冲突应在送审前显式解决。

## 可能风险与测试边界

- **简单任务的批准解释有歧义，但本场景不能判为越过硬门槛。** 源码 `SKILL.md:14` 要求信息充分的简单任务直接完成，`SKILL.md:109-112` 要求人类伙伴批准完整描述后才能构建。simple 第 1 轮模拟用户已经给出完整函数行为、改动边界和依赖限制，并明确说“请直接修改”（`scenarios/simple/transcript.md:7`）；这可合理视为聊天中对完整描述的预先批准。Agent 随后修改函数（`:9-18,31-41`；原始 `logs/turn-01.jsonl:10-13`），不能据“没有先由 Agent 送审描述”认定违反硬门槛。源码没有明说用户自己提供的完整描述是否即为批准，宜澄清这一点；当前场景支持简易任务直做。
- **跨目录搜索范围偏宽，指定附属文件的读取本身可视为任务授权。** 源码 `SKILL.md:101` 明确指向本技能目录的 `builder-check-prompt.md`；测试以 `--append-system-prompt-file` 直接加载该技能（`run-turn.py:22-25`）。因此 defined 第 6 轮读取这一指定附属文件可视为完成已授权构建者检查所需的资料，不能单凭其不在测试夹具 `project/` 下判定违反 `SKILL.md:60`。但执行前用 `cd /Users/harveyzhang96/Projects/harveyz-skill && find . ...` 搜索了整个仓库，而非直接读取已知技能目录（`scenarios/defined/transcript.md:217-227`；原始 `logs/turn-06.jsonl:7-9`）。这暴露测试布局下“当前项目”边界与搜索范围的歧义及潜在过宽访问；日志未显示它读取了其他仓库文件内容，故降为范围控制风险。测试工具无子代理，Agent 自查符合 `SKILL.md:101` 的降级条款（`transcript.md:200-208`）。
- **测试并非宿主原生技能调用。** `run-turn.py:22-31` 用 `claude -p --append-system-prompt-file` 把 SKILL.md 当系统提示注入，并限制工具为 `Read,Glob,Grep,Bash,Write,Edit`、启用 `bypassPermissions`。因此可观察模型在这组提示和脚本用户输入下的行为，不能证明真实宿主的技能触发、权限提示或子代理调度。defined/exploratory 的复杂构建者检查都被迫自查（各 transcript 第 6/9 轮），这符合源码无子代理时的备选路径，但没有验证独立检查路径（`SKILL.md:101`）。
- **外部访问规则与资料核实的交界尚未验证充分。** exploratory 场景使用虚构短信 API（`scenarios/exploratory/transcript.md:134-148`），未测试真实网络、个人文件或服务文档访问前的询问。defined 第 6 轮的仓库搜索范围提供一个风险信号，不能据此推断网络规则会失败。
- **`npm test` 不是通过结果。** `npm-test.exit:1`，日志末尾为 `custom skill tests: 11 passed, 3 failed`（`npm-test.log:1087`），前面还有多个 pytest 失败。不能把全仓测试表述为通过，也不能仅凭这份日志把失败归因于 brainstorming-zh。三个场景的 `artifacts.json` 所列文件字节数与 SHA-256 均和当前落盘文件相符；这证明产物清单一致，不证明逐轮交互的正确性。

## 流程表现与限定结论

- exploratory 先澄清并两次送审需求，再提交 P01/P02/P03 的成对方案，最后写 Spec 并取得模拟批准（`transcript.md:87-165,163-194,208-309,329-335`）；没有看到产品代码、脚手架或依赖安装。defined 也在需求清单、S1/S2 成对方案、Spec 的顺序上走通（`transcript.md:74-107,117-180,188-215,229-249`）。两者都在批准后停在说明制定计划的下一步，符合模拟用户的“只说明/不改代码”要求与源码 `SKILL.md:109-115`；未验证真实调用 `superpowers:writing-plans`。
- simple 一轮内完成函数修改，原始工具结果返回了预期例子（`scenarios/simple/logs/turn-01.jsonl:11-13`），验证了 `SKILL.md:14` 的直接执行路径。模拟用户首轮给出的完整要求及“请直接修改”可作为 `SKILL.md:109-112` 所说的聊天批准。该场景没有运行项目既有测试（`transcript.md:20-29`），结论只限所列例子与最终文件。
- 逐轮 transcript 的主要用户话语、工具调用与原始 JSONL 大体对应；原始 exploratory 第 9 轮有一次 `Edit` 返回“old_string and new_string are exactly the same”工具错误（`logs/turn-09.jsonl:86`），transcript 只列调用次数和最终成功状态（`:311-327`）。该错误未阻止后续写入，但“工具调用 7 次、exit=0”不足以表示每次调用都成功；审计应以 JSONL 为准。

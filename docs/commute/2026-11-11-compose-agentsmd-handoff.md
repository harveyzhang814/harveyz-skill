---
status: 待验收
date: 2026-11-11
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: same-workspace
branch: feature/devflow-agents-snippet
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+devflow-agents-snippet
base_commit: 3493efb1c7c03fe283b3bd5679b1771b4254897e
source_node: ffd8606c-99fe-4612-9c70-318df10b2088
target_node: 048fa050-dd70-45bc-972f-7f0511a0a05a
---

# 交接：按已批准计划实施 compose-agentsmd

**交接目的**：接手方按已确认的实施计划，实现新 devflow skill `compose-agentsmd`（从标准骨架、模块包与项目配置生成 AGENTS.md），交出方随后验收并合并。

---

## 背景与现状

需求、方案与计划都已由用户确认，并提交在本分支：Spec v0.4 已批准，计划已确认。本分支目前只有文档提交，没有任何实现代码。Task 1–6 全部待做。

## 关键决定（别改动）

- **权威依据只有两份**：Spec 与计划（见「相关文档索引」）。决定记录只用于追溯。三者冲突时，以 Spec 为准，并打回交出方。
- **执行方式**：按计划开头的 `REQUIRED SUB-SKILL`，即 `superpowers:subagent-driven-development`，逐个 Task 执行；不重写计划。
- **接手方的边界**：
  - 函数内部实现可以自行决定。
  - 不得修改接口签名、测试名称与断言、计划的 `Global Constraints`。
  - 计划与代码库现状冲突或无法照做时，停手，打回交出方。
- **Task 4 的模块正文**：沿用 Agent Canvas 原文措辞，只做 Spec 5.4 表、5.4a 节与兜底规则允许的删改（Spec S10）。按兜底规则改动的地方逐条写进 Task 4 的提交说明，Task 6 对照时要用。

## 范围铁律

- **范围内**：计划的 Task 1–6，涉及计划「文件总览」列出的文件。
- **范围外**：
  - 不修改 Agent Canvas 仓库，只读 `/Users/harveyzhang96/Projects/agent-canvas`。
  - Task 6 的 Agent Canvas 配置只放临时目录，不提交。
  - 不迁移本仓库自己的 AGENTS.md / CLAUDE.md。
  - 不合并到 staging；合并由交出方做。
  - 不动其他 skill。

## 相关文档索引

- Spec（权威）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-spec.md`
- 计划（权威）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-plan.md`
- 决定记录（追溯用）：`.hskill/spec/2026-11-11-compose-agentsmd/2026-11-11-compose-agentsmd-record.md`
- Task 4 与 Task 6 的蓝本，从 Agent Canvas 仓库只读取用：
  - `git -C /Users/harveyzhang96/Projects/agent-canvas show 14dbe3e0b:AGENTS.md`
  - `git -C /Users/harveyzhang96/Projects/agent-canvas show 14dbe3e0b:docs/superpowers/specs/2026-10-13-requirement-acceptance-design.md`（取其中 §3.1）
- 测试约定：`docs/reference/testing-guide.md`

## 工作流约定

见 `.hskill/handoff/config.md` 的 `workflow` 段。另有两点：

- **提交信息**：按 Conventional Commits 写，类型用 `feat` / `test` / `docs`，不要用 `doc`。每个 Task 结束时按计划的 Step 5 提交。
- **读 Agent Canvas 仓库时，路径写绝对路径** `/Users/harveyzhang96/Projects/agent-canvas`，不要写 `~/Projects/agent-canvas`。计划 Task 4 正文写的是 `~`，照抄会出问题：会话被隔离在 worktree 里时，Claude Code 会拒绝 `git -C ~/...` 这种运行时才能展开的路径。交出方本次已实测遇到。

## 验证步骤

- 每个 Task 结束时，跑该 Task 的 `Run` 命令。
- 全部完成后跑 `npm test`。
- Task 6 按计划步骤，在临时目录里生成并 diff。

## 最小验收锚点

全部满足才算达成。

1. **各 Task 的测试**：计划写定的所有测试都存在，测试名称和断言与计划一致，并全部通过。
   - 命令：`node --test tests/compose-agentsmd-*.test.mjs`
   - 预期：退出码 0，0 条失败。
2. **全量测试**：`npm test` 退出码为 0。
3. **Spec 第 7 节验收标准 V1–V11**：逐条可判定。
   - V1、V2、V4–V11 分别对应计划 Task 3、4、5 中的具名测试。
   - V3 的判定依据是 Task 6 产出的逐节对照表，写在本文档的接手方自测记录里：每处差异都能归到 Spec 5.4 表的某一行、5.4a，或 Task 4 提交说明里的兜底条目；出现无法归类的差异，即为未达成。
4. **publish-skill 检查**：对 `devflow/compose-agentsmd` 运行，F1–F9 与 R1–R4 都没有违规（警告可以有）。

## 接手方 verify 缺口（2026-11-11）

`validate-handoff.sh` exit 0；工作区检测 pass（`branch`、`core.hooksPath=.githooks`、`merge.ff=false` 均已核对）；`hands-off-to` 边已存在，`target_node` 与本节点一致。已核实无问题：Agent Canvas `14dbe3e0b` 存在且 `AGENTS.md` 为 394 行、§3.1 存在；`hskill install --skill/--target/--scope/--force` 均存在；分叉点基线 `npm test` exit 0。

以下缺口按「关键决定」（计划与 Spec 冲突以 Spec 为准并打回；接手方不得改测试名称与断言）打回，`status` 不动：

1. **（阻断）计划 Task 3 的 V10 测试与 Spec 第 7 节 V10 冲突。**
   - Spec V10：`slot_packs` 把某个**非联动槽**改用本地包；该槽**正文来自本地包**、标记为 `pack=local:<名>`、**首行 `packs` 含两者**。
   - 计划测试 `V10 slot_packs to a local pack uses it and records local:<name>`：本地包 `local-a` 声明联动组两槽、`slot_packs` 两槽都指向它；只断言槽标记与首行匹配 `/packs=local:local-a/`。
   - 后果：(a) 测的是联动槽而非非联动槽；(b) 此时主包 `alpha` 一个槽也不填，不算“被用到”，首行只有 `local:local-a`，“含两者”没被验证，“正文来自本地包”也没断言；(c) 若按 Spec 让两包都被用到，按名字排序首行应为 `packs=alpha@1.0.0,local:local-a`，计划断言 `/packs=local:local-a/` 必然失败——不改断言就无法满足 Spec。另外 fixture `alpha` 只声明联动组两槽，没有可“改用”的非联动槽，需要计划同时说明 fixture 怎么调整（例如 `alpha` 增加一个非联动槽，或本地包改填一个 `alpha` 不填的非联动槽）。
   - 顺带请明确：首行 `packs` 的排序键对本地包取 `local-a` 还是 `local:local-a`。
   - 请交出方修订计划中这条测试的名称/断言/fixture 说明。
2. **（次要）Spec V7 的“嵌套 `@if` → 退出码 2 且不写文件”在计划里没有生成层面的断言。** Task 3 的 V7 测试 `breakIt` 只含未知参数、未闭合 `@if`、只关 `flow-summary`、拆联动组四项；嵌套 `@if` 只在 Task 1 渲染器层断言抛错。最小验收锚点 3 说 V7 对应具名测试。请二选一：在 `breakIt` 中补一项嵌套 `@if`，或在锚点里写明嵌套以 Task 1 测试为准。

## 交出方补正（2026-11-11）

两条缺口都成立，已修订计划（`2026-11-11-compose-agentsmd-plan.md`），Spec 不变：

1. **V10（阻断）**：
   - fixture 调整：`alpha` 新增非联动槽 `instruction-sources`（`slots: ["flow-summary","instruction-sources","flow-steps"]`）。本地包 `local-a` 只声明 `instruction-sources`，模板正文含 `LOCAL-A BODY`，配置写 `slot_packs: { "instruction-sources": "local-a" }`。
   - 测试改名为 `V10 slot_packs moves a non-linked slot to a local pack and both packs are recorded`，断言改为三条：该槽标记为 `pack=local:local-a`、正文含 `LOCAL-A BODY`、`flow-steps` 仍来自 `alpha@1.0.0`。首行为 `packs=alpha@1.0.0,local:local-a`。
   - 排序键：取包名本身，不含 `local:` 前缀，也不含版本，按 JavaScript 默认字符串比较升序。Global Constraints 已同步写明。
   - 连带修改：
     - Task 2 断言改为 `instruction-sources` 来自 `alpha`、`platform-fallbacks` 为 `null`；
     - V11 改为修改 `local-a/instruction-sources.md`。
2. **V7（次要）**：Task 3 的 `breakIt` 新增 `setNestedIfInLocalTemplate`，生成层也断言嵌套 `@if` 时退出码为 2、不写文件。

请重新 verify。

## 接手方自测记录（2026-11-11）

执行范围：计划 Task 1–6，提交 `46d6922..78b301c`（9 个提交，起点 `19eaabc`）。执行方式按计划的 `REQUIRED SUB-SKILL`（`superpowers:subagent-driven-development`）：每个 Task 由独立子代理实现，之后做一轮 Task 审查（是否符合 Spec + 代码质量），全部完成后再做一次整条分支终审。终审提出 8 项问题，经一轮修复后复审通过，对应提交 `85e8f7f`、`78b301c`。

以下命令均在本工作区、HEAD `78b301c` 上实跑。判断成败看退出码，没有经过管道。

| # | 锚点 | 命令 | 结果 |
|---|---|---|---|
| 1 | 各 Task 测试存在、名称与断言同计划、全部通过 | `node --test tests/compose-agentsmd-*.test.mjs` | **pass**：退出码 0，64 个通过，0 失败。计划写定的 48 个测试名逐个在测试文件里 `grep -F` 核对，全部存在。另外 16 个是新增测试，原有的计划测试一个没改：其中 3 个是 Task 3 补的，13 个是终审修复补的。断言与计划一致，这一点由逐 Task 审查核对过。唯一例外见下方「需交出方知悉」第 1 条。 |
| 2 | 全量测试 | `npm test` | **pass**：退出码 0。Node 部分 464 个，457 通过，0 失败，7 跳过；bats 部分全部通过。 |
| 3 | Spec 第 7 节 V1–V11 | 见下表 | **pass**：11 条全部满足。 |
| 4 | publish-skill F1–F9、R1–R4 | 对 `devflow/compose-agentsmd` 按 publish-skill 的规则逐项核对 | **pass**：F1–F8 与 R1–R4 都通过。F8 现值 `411304456391ad45`，与索引里的 `contentHash` 一致，`contentVersion` 为 0.1.0。有 1 条 **F9 警告**：动词 `compose` 不在 `docs/reference/skill-spec.md` 的词表里，但语义合理，不阻断。 |

### V1–V11 对应

| V | 判定依据 | 结果 |
|---|---|---|
| V1 | `V1 generate twice is byte-identical and check reports ok` | pass |
| V2 | `V2 agent_canvas false leaves no canvas wording but keeps acceptance criteria`；`V2 agent_canvas true includes Step 8, release acceptance and V format` | pass |
| V3 | 下方逐节对照表 | pass：无法归类的差异为 0 |
| V4 | `V4 devflow pack files contain no Agent Canvas project specifics` | pass |
| V5 | `V5 hand edit is detected and generate refuses without --force` | pass |
| V6 | `V6 older generated pack version reports outdated` | pass |
| V7 | `V7 config or template errors exit 2 and write nothing`（含嵌套 `@if`） | pass |
| V8 | `V8 hskill install copies pack files byte-for-byte` | pass |
| V9 | 锚点 2 和锚点 4 | pass（带 F9 警告） |
| V10 | `V10 slot_packs moves a non-linked slot to a local pack and both packs are recorded` | pass |
| V11 | `V11 editing a local pack template reports stale, not outdated` | pass |

### V3 逐节对照（Task 6）

做法：把 Agent Canvas `14dbe3e0b:AGENTS.md` 按 SKILL.md「初始化」拆成配置，在临时目录里生成，不提交。终审修复后，我在 HEAD `78b301c` 上用同一份配置重新跑了一次：`check` 输出 `status=ok`，退出码 0；`generate` 退出码 0。新生成的文件与 Task 6 当时的输出逐字节一致（`cmp`），所以下表在 HEAD 上仍然成立。

下表中的兜底编号：#1–#8 对应 `ca56e4b` 提交说明里的 8 条，按出现顺序编号；#9 对应 `311329f`。

#### 2. 配置与描述槽

`$T/.hskill/compose-agentsmd/config.json`（逐字）：

```json
{
  "title": "Agent Canvas",
  "pack": "devflow",
  "agent_canvas": true,
  "integration_branch": "staging",
  "merge_command": "scripts/merge-to-staging.sh",
  "e2e": "`simulate-user` Electron E2E",
  "complexity_signals": "跨进程/跨模块（main↔renderer↔utilityProcess）、修改 IPC 协议"
}
```

`spec_dir` / `plan_dir` / `record_dir` 不写：默认值（`docs/superpowers/specs`、`docs/superpowers/plans`、`.hskill/spec`）与原文落点一致，生成结果逐字相同。

描述槽（全部用 `sed -n` 按原文行号逐字截取）：

| 槽 | 原文来源 |
|---|---|
| `overview.md` | L5–6 技术栈段 |
| `principles.md` | L56–72 `### 术语查阅`、`### 设计判断`（保留 `###`） |
| `platform-adaptation.md` | L15–17 指令源第 1 条（唯一正本 / 不维护 `CLAUDE.md` / Codex 读取…）＋空行＋L43–54 `### Claude Code 适配`（保留 `###`） |
| `repo-env.md` | L76–93 仓库环境正文 |
| `other.md` | L152–154 Step 1.3 `.design-scratch/` / `sync-design` 段；L197 后半句 “`.claude/worktrees/` 下的存量 worktree 是历史遗留，继续有效，不迁移。”；L129 `AGENTS.pre-init-spec.md` 存档说明；L393–394 版本验收的两条设计文档链接 |

#### 3. 兜底条目编号

取自提交说明：#1–#8 = `ca56e4b` 的 8 条（按出现顺序），#9 = `311329f` 的 1 条。

| # | 内容（简） | 本次输出是否体现 |
|---|---|---|
| 1 | flow-summary else 分支“7 步”写法 | 否（`agent_canvas: true` 走 if 分支） |
| 2 | 指令源首条“其他平台按其实际机制加载”随整条删去 | 是 |
| 3 | Step 3.1 `staging` → `@{integration_branch}` | 渲染后与原文一致，无可见差异 |
| 4 | Step 3.2 删 `.worktrees/<…>` 具体路径 | 是 |
| 5 | Step 3.3 删 `merge.ff=false…由「仓库环境」保证` | 是 |
| 6 | 4.2 内联 V 格式，V1 标签改为“……” | 是（相对 AC spec §3.1） |
| 7 | 4.2 内联“（如本 spec 的 `## 10.…`）”→“（如 `## 10.…`）” | 是（相对 AC spec §3.1） |
| 8 | 4.2 不内联 §3.1 引导句与结尾句 | 是（相对 AC spec §3.1） |
| 9 | 7.2 第 4 条 else 分支保留“验证 subagent 同样不合并”“停止并报告” | 否（走 if 分支） |

#### 4. 逐节对照表

| 原文小节 | 生成位置（槽） | 差异 | 归类 |
|---|---|---|---|
| 文件头（无） | 首行生成标记、各槽 `<!-- slot:… -->` 行 | 新增生成标记与槽标记 | 5.2 结构（生成格式，Global Constraints / Spec 5.6）；比对时剔除 |
| `# AGENTS.md`（L1） | 无 | 删去这一行文件名式 H1 | 5.2 结构（`overview` 只生成一个 `# <title>`）＋ 5.4 行“标题、技术栈”（标题取 `title`=Agent Canvas） |
| `# Agent Canvas` 标题＋技术栈（L3–6） | `overview` | 标题由 `title` 生成；技术栈段逐字一致 | 5.4 行“标题、技术栈” |
| 开头说明（L8–9） | `flow-summary` 开头 | 前半句“本文件只写流程……”删去；后半句移入 `## 流程简述` 下第一段，换行合并为一行 | 5.4 行“开头说明” |
| `## 通用约定（与流程无关）`（L11） | 无 | 分组标题删去，子节升为 `##` 并按骨架分散 | 5.2 结构 |
| `### 指令源与能力检测`（L13–28） | `instruction-sources`（`##`） | ① 首条“唯一正本／不维护 `CLAUDE.md`／Codex 读取…／见下文「Claude Code 适配」／其他平台按其实际机制加载”移出模块，逐字进 `platform-adaptation`；② 第 2 条删 `sync-design`、`simulate-user`，“画布 skill”保留在 `agent_canvas` 分支；③ `docs/reference/git-workflow.md` → “项目的分支规则”（换行位置随之变）；`rg` 条保留；`###`→`##` | ① 5.4 行“指令源”＋兜底 #2；② ③ 5.4 行“指令源”；层级 5.2 结构 |
| `### 平台专属能力的通用替代`（L30–41） | `platform-fallbacks`（`##`） | 正文逐字一致（含“关闭画布节点”行）；`###`→`##` | 5.4 行“平台能力替代表”；层级 5.2 结构 |
| `### Claude Code 适配`（L43–54） | `platform-adaptation` 内 `###`，外层 `## 平台适配` | 正文逐字一致；新增外层 `## 平台适配`；前面多了从指令源移来的首条 | 5.4 行“Claude Code 适配…”；外层标题 5.2 结构 |
| `### 术语查阅`（L56–59） | `principles` 内 `###`，外层 `## 项目原则` | 正文逐字一致；位置提前到流程简述之后 | 5.4 行“…术语查阅、设计判断…”；位置与外层标题 5.2 结构 |
| `### 设计判断`（L61–72） | `principles` 内 `###` | 正文逐字一致；位置同上 | 同上 |
| `### 仓库环境`（L74–93） | `repo-env`（`## 仓库环境`） | 正文逐字一致；`###`→`##` | 5.4 行“…仓库环境”；层级 5.2 结构 |
| `## 流程简述`（L95–111） | `flow-summary` | 8 步、闸门、槽位约定逐字一致；前置了开头说明后半句；整节从仓库环境之后移到 overview 之后 | 5.4 行“流程简述＋槽位约定”＋“开头说明”；位置 5.2 结构 |
| `## 上游 skill 与本文件的优先级`（L113–129） | `flow-steps` | 第 1–5 条渲染后逐字一致（落点参数取默认值，第 4、5 条在 `agent_canvas` 分支）；`AGENTS.pre-init-spec.md` 一行删出模块，逐字进 `other` | 5.4 行“上游 skill 优先级”（删去该行；第 5 条按 5.4a 保留） |
| Step 1（L131–159） | `flow-steps` | 1.1/1.2/1.4 一致；1.3 删 `.design-scratch/`/`sync-design` 段，逐字进 `other` | 5.4 行“Step 1” |
| Step 2（L161–182） | `flow-steps` | 2.2 高档判定信号改为通用 5 项，后接 `complexity_signals`：“…可拆成 3 个以上任务、跨进程/跨模块（main↔renderer↔utilityProcess）、修改 IPC 协议”；其余逐字一致（琐碎档“不调用画布 skill”在 `agent_canvas` 分支） | 5.4 行“Step 2” |
| Step 3（L184–214） | `flow-steps` | 3.1 渲染后一致；3.2 删 `.worktrees/<分支名，/ 换成 +>` 路径、删 `.claude/worktrees/` 遗留句（逐字进 `other`），换行位置变；3.3 删 `merge.ff=false…由「仓库环境」保证`（`git config merge.ff false` 仍在 `repo-env`） | 3.2：5.4 行“Step 3”＋兜底 #4；3.3：兜底 #5；3.1：兜底 #3（无可见差异） |
| Step 4（L216–259） | `flow-steps` | 4.2 “用 `sync-design` 产出的设计稿”→“设计稿”（`sync-design` 规则保留在 `other` 的设计稿段）；指向 AC spec §3.1 的链接换成内联 V 格式（示例块＋6 条要点），内联文本相对 §3.1 源文：V1 标签→“……”、“如本 spec 的”→“如”、引导句与结尾句未内联；4.3、4.4 逐字一致 | 设计稿行：5.4 行“Step 4”；内联：5.4a（`agent_canvas: true` 原样保留 V 格式，内联）＋兜底 #6、#7、#8 |
| Step 5（L261–291） | `flow-steps` | 逐字一致 | 5.4 行“Step 5” |
| Step 6（L293–309） | `flow-steps` | 渲染后逐字一致（`e2e` 代入） | 5.4 行“Step 6” |
| Step 7（L311–337） | `flow-steps` | 7.1、7.2 第 1–4、6 条渲染后一致；第 5 条删 `git-workflow.md#合并到集成分支` 链接（“脚本提示处理。”结尾）；分支与合并命令由参数渲染，结果一致 | 5.4 行“Step 7” |
| Step 8（L339–374） | `flow-steps`（`agent_canvas` 分支） | 逐字一致 | 5.4 行“Step 8” |
| `## 版本验收`（L376–394） | `release-acceptance` | 规则正文逐字一致；末尾两条 AC 设计文档链接删出模块，逐字进 `other`（普通 `diff` 因两处都在文件末尾而把它们对齐成“未变”，按节比对才看得出移动） | 5.4 行“版本验收” |
| （新增）`## 项目原则` / `## 平台适配` / `## 其他约定` | `principles` / `platform-adaptation` / `other` | 描述槽标题 | 5.2 结构 |
| （新增）`## 其他约定` 正文 | `other` | 收纳模块删去的项目专属句：设计稿段、`.claude/worktrees/` 遗留句（从原句中截出，去掉前面的“；”）、`AGENTS.pre-init-spec.md` 存档说明、两条 AC 设计文档链接 | 5.4 各行“删去”内容的项目侧落点（项目内容移入描述槽） |

#### 5. 无法归类的差异

无。

#### 6. `check` 输出

```
status=ok
path=/var/folders/0g/clby1fg9341729jj41dymllr0000gn/T/tmp.mrAujxibcG/AGENTS.md
pack=devflow installed=1.0.0 generated=1.0.0
```

退出码 0。

#### 观察（不影响归类）

- Step 2 的高档信号是“通用信号 + `complexity_signals`”。这次 `complexity_signals` 照抄了原文措辞，结果同一行里“跨进程/跨模块”“修改协议”各出现两次。内容没少，只是读起来重复；改配置的写法就能去掉，不需要改包。

### 需交出方知悉（执行中的裁定）

1. **Task 1 的一个测试多了一条断言。** 测试 `unknown parameter throws TemplateError with file and line` 在计划原有断言之外，加了一条 `e.message.includes('m.md:2')`。它只会让测试更严，而且计划的接口说明本来就写了 message 要包含 `<file>:<line>`，所以保留了。如果你认为这算改动了断言，删掉这一行即可。
2. **Step 7.2 第 4 条在 `agent_canvas: false` 下多保留了两句原文。** 这两句是“（验证 subagent 同样不合并）”和“角色或验证状态无法判定时，停止并报告”，见 `311329f`。依据是 Spec 5.4 这一行只要求把“节点角色相关的句子”放进条件里，而这两句与画布无关，按 S10 应保留原文。代价：`false` 分支比 Spec 给出的那句 else 文本多了这两句；它们都不含 V2 列出的词。
3. **Spec 反馈，没有改动，请你决定。** `e2e` 为空时，Step 6 写的是“方式由「仓库环境」或「其他约定」规定”，这是 Spec 5.3 逐字规定的。但这两个描述槽可能为空，于是这句话没有落点，与 5.4 的兜底规则（删去指向可能为空的描述槽的引用）冲突。我按更具体的 5.3 执行了。
4. **超出计划、为满足 Spec 第 3 节和第 6 节而加的校验，都来自终审。** 这些校验都配了新测试，计划里的测试没有改：
   - 模板读入时统一去掉 BOM，并把 CRLF 换成 LF。原来的问题是：模板若是 CRLF 换行，`@if` 指令会原样漏进输出，`agent_canvas: false` 也会带出画布内容。
   - 格式稍有偏差的指令，以及 `@{非法名}` 这样的参数，改为报错，退出码 2。原来它们会被当作普通文字原样输出。
   - 必填的字符串参数和 `title` 不能为空串，否则退出码 2（Spec 第 6 节）。
   - 包名限定为 `^[A-Za-z0-9][A-Za-z0-9._-]*$`，并保留 `disabled` 不可用。
   - `title` 不得含换行，也不得含标记文本。
   - CLI 的子命令查找改用 `Object.hasOwn`。
   - 意外的 I/O 错误统一返回退出码 2；退出码 1 只留给“已存在 / 拒绝覆盖 / 状态不是 ok”。
   - SKILL.md 补了两处说明：建议用 `.gitattributes` 让 AGENTS.md 以 LF 提交；以上校验规则与退出码 2 的覆盖范围。
5. **已知但没有修的小问题**（来自逐 Task 审查，终审判定可以推迟）：
   - `check` 只在没有其他状态时才报 `stale`。这是计划规定的，SKILL.md 已写明。
   - `merge_command` 不是脚本时，合并说明里仍写“该脚本”。按 S10 保留了原文措辞。
   - 兜底 #8 没有内联 §3.1 引导句里“格式固定，供程序解析”这一信息点。
   - SKILL.md 接入流程没写清原文件副本放在哪、何时清理。

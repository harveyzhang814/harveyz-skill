# 决定记录：计划后交接与统一 worktree 管理

建档日期：2026-11-08
分支：`feature/plan-handoff-worktree`

**需求批准：** 用户 2026-11-08 确认 question-me 需求摘要（答复“确认，交回 init-spec”），批准 D1–D15。

## 当前决定

### D1 目标：计划交给较弱的、可能跨厂商/跨框架的执行模型

- **决定：** 让 question-me → init-spec → develop-plan 产出的计划，能交给比原会话弱的执行模型实施；执行方可能是其他厂商的模型，或其他 agent 框架（Claude Code、Codex、opencode）。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“如果我要调用 handoff 给一个比原会话模型更弱的执行模型去执行，最好是在哪里开始 handoff……要考虑执行模型可能不是一个厂商的，也可能是不同 agent 框架的（比如 claude，codex，opencode）。”（本会话第 1 条消息）

### D2 主要动机：省钱/省额度

- **决定：** 交接的主要动机是成本，不是并行吞吐或独立视角。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“交给弱模型的主要动机？”选项：a 省钱/额度（推荐）/ b 并行吞吐 / c 独立视角。答复：“主要是a”。

### D3 交接时机：develop-plan 的计划经用户确认之后

- **决定：** 交出方（强模型）完成需求摘要、Spec、计划三道人工确认后交接；交出方负责验收。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——评估结论表中的交接时机一项，用户答复“可以”。
- **依据：** Spec 的读者被定义为“有能力的构建者”，计划的读者是“不熟悉代码库的工程师”，并写定文件、接口、测试断言与命令；计划是纯 Markdown，任何框架都能照做。

### D4 计划不为执行方加细

- **决定：** develop-plan 现有详略标准不变。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“要不要为弱执行方调计划详略？”答复：“弱执行方的能力不弱，只不过没有主模型那么强，比如opus和sonnet”。

### D5 执行方权限：接口、测试名与断言、Global Constraints 不可改，冲突即打回

- **决定：** 接手方可自行决定函数内部实现；接口签名、测试名与断言、`Global Constraints` 不得修改；计划与现状冲突时停手打回交出方。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“执行方遇到计划与现实冲突时权限到哪？”答复：“按照推荐”。

### D6 一份计划对应一次交接

- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“交接粒度？”答复：“一次计划一个handoff”。

### D7 交接入口在 AGENTS.md 层控制，不写入 skill 步骤

- **决定：** “计划确认后改走 handoff”这一工作流入口，参照现有模式在 AGENTS.md 中控制，不写入 develop-plan 等 skill 的步骤。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“怎么落地？”答复：“handoff迁入工作流的方法，不写入这些步骤skill，参照现在的模式在agents.md里去控制”。
- **待协调：** 与 D15“每次询问”及 develop-plan 原文“不询问执行方式”的关系，见 D16。

### D8 handoff 协议主体不改，只改第 4 步判定措辞并补检测

- **决定：** author/verify/self-test/accept 四阶段与共享工作区协议不变。改两处：author 第 4 步的模式判定从“接手方是否在另一条分支”改为“接手方是否为另一个会话、需被指到确定工作区”；补检测：分支不是集成分支、引用的 Spec 与计划已提交到该分支、交接文档已提交、接手方是另一会话时文档写明工作区路径。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“handoff只需要传递号并检测worktree”（本会话，评估阶段）；检测项清单为 Agent 推断，随摘要确认。
- **依据：** `validate-handoff.sh` 不查集成分支、不查引用文件是否已提交、不查交接文档是否已提交、same-workspace 模式跳过工作区校验。

### D9 测试断言被改弱：不改 skill，靠锚点写法

- **决定：** 交出方把最小验收锚点写成“各 Task 的测试与计划写定的断言一致，并全部通过”。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“缺口 2 降为不改 skill？”答复：“可以”。
- **依据：** 测试内容由交出方在计划中写定，接手方只是落地成文件；Sonnet 级执行方改弱断言概率低（推断）。

### D10 新写一个 worktree 管理 skill，各 skill 统一调用

- **决定：** worktree 的处理收口到一个独立 skill；init-spec 建档时调用它建好工作区，develop-plan 沿用，handoff 用它传递与检测。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“要么单独写一个worktree管理的skill，确保各个skill调用的统一性”；细化此前的“缺口1应该由init-spec和develop-plan来解决worktree问题”。
- **依据：** worktree 逻辑现分散在 handoff、develop-plan、init-skill、contribute-skill、CLAUDE.md/AGENTS.md 五处，路径习惯不一（`.worktrees/` 与 `.claude/worktrees/`）。

### D11 本轮迁移范围

- **决定：** 新 skill 按全部五处调用方的需求设计；本轮只迁 init-spec、develop-plan、handoff。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——选项：A 按五处设计、本轮迁三个（推荐）/ B 五处一次迁完。答复：“A”。

### D12 新 skill 职责：建或复用、进出、检测；不含合并与清理

- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——选项：A 只管建或复用、进出、检测（推荐）/ B A 并另记收尾 skill 为未决 / C 只管建或复用。答复：“A”（参考 superpowers 与 gstack 调研之后）。
- **依据：** superpowers 把检测/建与合并/清理分在两个 skill，清理只删自建、禁 `--force`；gstack 建在派发方、合并删除在最后一步并需用户确认。两家都没有复用已有分支的逻辑，需自补。

### D13 没有分支规则的仓库也一律建 worktree

- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“无规则仓库里新 skill 怎么做？”答复：“这套工作流和worktree是紧密相关的，所以一建立”（理解为“一律建立”，用户未纠正）。
- **代价：** 其他仓库里 init-spec 的现有行为改变。

### D14 新建的基线与确认

- **决定：** 基线默认推断：有集成分支约定用它，否则用仓库默认分支；新建前向用户一次确认基线、分支名、路径；复用已有工作区不问。主目录停在功能分支上时照样新建，确认时把当前分支列为可选基线。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——基线问题答复“A”；主目录停在功能分支问题答复“A”。
- **依据：** 从当前 HEAD 拉分支会静默夹带其他会话未合并的提交。

### D15 交接触发：计划确认时每次询问

- **决定：** 计划确认时询问“本会话执行，还是交接给其他执行方”；将来改为自动路由。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——选项：A 只在用户明确要求时（推荐）/ B 每次询问。答复：“先B，未来准备做自动路由”。

### D16 询问点与交接入口：develop-plan 只留接口，规则写在项目指令

- **决定：** develop-plan 第 5 步把“不询问执行方式”改为“项目指令另有规定时按项目指令，否则沿用默认”；“计划确认后询问执行方式、选交接则走 handoff author”的规则写在 AGENTS.md，并按现有做法同步写入 CLAUDE.md（Claude Code 不读 AGENTS.md）。
- **状态：** 已批准
- **来源：** 用户选择——选项：A 完全按 D7、develop-plan 不改 / B 修订 D7、写进 develop-plan / C 折中、develop-plan 只留接口（推荐）。答复：“C”。CLAUDE.md 同步为 Agent 推断的次要决定，随 Spec 送审。
- **依据：** develop-plan 原文写“不询问执行方式”，与 D15 直接矛盾；Claude Code 读 CLAUDE.md、不读 AGENTS.md。
- **代价：** 只有在项目指令里写了规则的仓库会询问。

### D17 新 skill 的名称、归属与规则来源

- **决定：**
  - 名称 `manage-worktree`（Agent 推断：沿用仓库已有的 `manage-` 动词，符合动词-名词规范）。
  - 归属：放进现 `superpowers-rewrite` bundle，该 bundle 改名为 `devflow`；handoff 仍留在 `coding`。
  - 规则来源：暂时读取 init-workflow 生成的 `.claude/workflow-config.yml`（受保护分支即集成分支，`merge_from` 推断基线，`branch_naming` 给命名模式）；文件不存在时按 D14 默认。
  - 默认路径：`.worktrees/<分支名，/ 换成 +>`；本仓库也改用 `.worktrees/`，更新 CLAUDE.md、AGENTS.md、`.hskill/handoff/config.md` 的路径说法，现有 `.claude/worktrees/` 下的目录不动、改称历史遗留。目录未被 git 忽略时，补写 `.gitignore` 的改动并入新建前的确认。
- **状态：** 已批准
- **来源：** 用户选择——
  - 归属：选项 A 放 `coding`（推荐）/ B 放 `superpowers-rewrite`；答复“统一放到superpowers-rewrite，但重命名这个bundle”。追问范围：A 只放 manage-worktree / B 连 handoff 一起（推荐）；答复“A”。追问名称：A `devflow`（推荐）/ B `specflow` / 自定义；答复“A”。
  - 规则来源：选项 A 读 init-workflow 配置（推荐）/ B 自有配置；答复“暂时读取这份规则，未来融合到新git skill里去”。
  - 默认路径：选项 A `.claude/worktrees/`（推荐）/ B `.worktrees/`；答复“B”。追问本仓库冲突：A 本仓库也改用 `.worktrees/`（推荐）/ B 保留并加路径字段；答复“A”。
- **代价：** handoff 与 manage-worktree 分属两个 bundle；改名牵动目录、`package.json`、`tests/skill-portability.test.mjs`、init-spec 正文与 PRD 中的 bundle 名；Claude Code 中启动时固定工作目录的 subagent 无法切进 `.worktrees/` 下的工作区。

### D18 检测分工与缺失时的处理

- **决定：**
  - 工作区类检测（是否为已登记的 worktree 根、是否为命名分支、是否为集成分支、是否 detached、hooks 是否配置）归 manage-worktree；handoff 在 author 写交接、接手方 verify 两个时点要求先通过 manage-worktree 的“进入并检测”，不通过不放行。
  - `validate-handoff.sh` 只补文档类检测：引用的 Spec 与计划已提交到该分支、交接文档已提交、接手方为另一会话时写明工作区路径。
  - manage-worktree 不可用时，调用方（init-spec、develop-plan、handoff）停下，告诉用户安装 `devflow` bundle 中的 manage-worktree，不自带兜底。
- **状态：** 已批准
- **来源：** 用户选择——分工：选项 A 按两类拆分（推荐）/ B handoff 校验脚本全包 / C 校验脚本调用 manage-worktree 的脚本；答复“A”。缺失处理：选项 A 停下提示安装（推荐）/ B 调用方自带最简兜底；答复“A”。
- **代价：** 工作区类检测靠 agent 按指令调用，不在机器门禁里；未安装 manage-worktree 的用户在该步卡住。

### D19 计划开头 `REQUIRED SUB-SKILL` 不改

- **决定：** 保持现写法；交接时接手方同样按它使用 `subagent-driven-development`。
- **状态：** 已批准
- **来源：** 用户原始需求——“subagent-driven-development不是claude专属，codex等其他框架也适用”（纠正 Agent 此前“只认 Claude Code”的错误前提）。
- **依据：** superpowers 7.0.0 的 `using-superpowers/references/codex-tools.md` 为 Codex 适配了 subagent 派发；该 skill 在宿主无 subagent 能力时自行退回 `executing-plans`；它开工前检测已在 worktree 中即不再新建。opencode 未在其适配清单中，是否支持派发 subagent 未查证。

### D20 与 `superpowers:using-git-worktrees` 的关系

- **决定：** 本仓库 skill 改为调用新 skill；第三方 skill 不动。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——本仓库 `.claude/settings.json` 已关闭它；它从当前 HEAD 拉分支。

### D21 版本、发布与验收

- **决定：** 改动的 skill 升版本并更新 `skills-index.json` 的 `contentHash`/`contentVersion`，本轮不发 npm。验收：`npm test` 通过；handoff 的 bats 测试为新增检测补无效输入用例；新 skill 登记并通过格式校验；无 `workspace_mode` 的旧交接文档校验结果不变；init-skill、contribute-skill 不改。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断

### D22 新增交接检查的生效范围：含 `workspace_mode` 且状态为「待执行」

- **决定：** `validate-handoff.sh` 新增的“已提交”和“必须写明工作区”检查，只在文档含 `workspace_mode` 且 `status` 为「待执行」时生效；既有 bats 用例 37、40 只改 fixture（先提交文档），期望值不变。拟取代 D21 中“无 `workspace_mode` 的旧交接文档校验结果不变”一句的判定口径。
- **状态：** 待审
- **来源：** Agent 推断——构建者检查发现：`workspace_mode` 在 handoff 1.17.1 已存在，不能用来区分新旧文档；verify 与 accept 都重跑校验，接手方没有提交义务，不限定状态会让 accept 把已完成的工作误判打回。
- **代价：** 正处于「待执行」、含 `workspace_mode` 但未提交的在途交接文档会新报 ERROR。

## 未决（用户留待以后）

- init-skill、contribute-skill 迁到新 skill。
- 本会话执行与交接之间的自动路由。
- 新的 git skill，融合 init-workflow 的分支规则；届时 manage-worktree 改读它。

## 已否定或失效

（暂无）

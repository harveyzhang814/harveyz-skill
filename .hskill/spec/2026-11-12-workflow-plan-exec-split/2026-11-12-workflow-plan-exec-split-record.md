# 决定记录：git 工作流的规划与执行分离

建档日期：2026-11-12
分支：`feature/workflow-plan-exec-split`

**需求批准：** 用户 2026-11-12 确认 question-me 需求摘要（答复“确认”），批准 D1–D25；D26–D29 为未决事项，状态“已提出”。

## 当前决定

### D1 修 init-workflow，而不是只手改各项目文档

- **决定：** 修 init-workflow 的模板与渲染，再重新生成各项目的 `docs/reference/git-workflow.md`；不采用“只手改 agent-canvas”或“拆出另一份手写文档”。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“git-workflow.md 怎么修？”选项：A 只手改 agent-canvas / B 修 init-workflow / C 拆文件。答复：“B”。

### D2 架构判断从职能出发，不从现状出发

- **决定：** init-workflow 与 manage-worktree 是否合并，按职能和变化原因判断，不以现有分工为依据。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“不要从现状考虑，而是从他们的职能和功能上去考虑他们应不应该合并。……现状可能是因为一些历史的原因，先后产生的生命周期所导致的。”

### D3 两个模块：init-workflow 规划，manage-worktree 执行

- **决定：** init-workflow 拥有全部 git 策略（分支拓扑、保护、命名、提交格式、集成分支、基线、worktree 路径约定、合并方式），是策略的唯一解释者，并生成 hooks、文档与标准合并脚本；manage-worktree 只做按任务的工作区操作（准备、进入、离开、检测、合并），读取规划侧解释好的结果，不自行解析策略。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“这两个 skill 的架构关系？”选项：A 两个模块重划边界 / B 合并成一个 / C 维持现状只修模板。答复：“A，一个规划，一个执行”。
- **依据：** ①定义、②强制、③说明策略因同一原因变化；④按任务执行因宿主能力或任务生命周期变化；依赖单向（④→①）。现状病根是策略有两个解释者（`render_docs.py` 与 `inspect-worktree.sh`），且 worktree 路径、合并方式未登记为策略。

### D4 两者都对齐最新工作流，清理 init-workflow 的旧设定

- **决定：** init-workflow 生成的内容（模板、hooks、配置模板）与 manage-worktree 都按最新工作流对齐；清除旧流程设定 O1–O5（见 D18 的权威定义与 Spec 现状一节）。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“他们针对的工作流应该是最新的。init-workflow里可能存在旧工作流的一些设定”。

### D5 所有项目「开始新工作」都走 manage-worktree 逻辑

- **决定：** 模板「开始新工作」对所有项目改为 worktree 先行：装了 manage-worktree 用它，未装给出显式基线的兜底命令。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“worktree 先行对另外 16 个项目也生效吗？”答复：“是的，所有项目都使用manage-worktree的逻辑，但需要检查manage-worktree的通用性”。
- **依据：** 已核查 19 个项目：规则文件三种位置均能找到；有 staging 的 15 个推断基线 `staging`，仅 main 的 4 个推断 `main`，master 也能识别。Codex 等宿主未实测（D24）。

### D6 init-workflow 部署时保证 worktree 目录被 git 忽略

- **决定：** worktree 路径约定是规划侧策略，init-workflow 部署时检查该目录是否被 git 忽略，未忽略则补写 `.gitignore` 并列入写入清单；manage-worktree 首次新建时的补写确认保留，作没跑过新版 init-workflow 的仓库的兜底。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“`.worktrees/` 未被忽略由谁补写？”答复：“A”。
- **依据：** 8 个项目 `.worktrees/` 未被忽略（`git check-ignore`）。

### D7 已手改的旧文档首次重跑时照旧覆盖，只提醒

- **决定：** 新版渲染遇到没有项目自填区的旧文档，照旧整份覆盖，给出提醒；不检测、不自动迁移手改内容。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“已有手改、无自填区的项目首次重跑怎么处理？”选项：A 检测后让用户决定 / B 自动挪进自填区 / C 照旧覆盖只提醒。答复：“C”。

### D8 合并脚本也标准化

- **决定：** 提供标准合并脚本，取代各项目分别演化的 `scripts/merge-to-staging.sh`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户原始需求——“合并脚本也是提供标准化脚本”。
- **依据：** harveyz-skill、agent-canvas、File Translator 三份同源脚本已分别演化为 367、355、190 行；目标分支均写死 `staging`。

### D9 标准合并脚本正本归 init-workflow，部署进仓库

- **决定：** 标准脚本正本与 hooks 模板一起由 init-workflow 维护，部署时装进仓库 `scripts/`，目标分支按配置渲染；没装 skill 的人和 CI 也能运行。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“标准脚本放哪、怎么到各仓库？”选项：A 正本归 init-workflow 部署进仓库 / B 放执行侧 skill 从 skill 目录运行。答复：“A”。

### D10 manage-worktree 新增「合并」动作

- **决定：** manage-worktree 新增「合并」：核对当前分支 → 调用仓库的标准合并脚本 → 报告结果。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“执行侧本轮是否新增动作？”选项：A 不新增 / B 新增「合并」/ C 新增「合并」与「清理」。答复：“B”。
- **影响：** 修订 `2026-11-08-plan-handoff-worktree` 决定 D12 中“manage-worktree 不做合并”一项；“不清理 worktree、不删分支”保持不变。

### D11 发布流程只修模板写法

- **决定：** 模板「发布到主分支」改为不切换主工作树的写法，并指向项目自己的发布流程（如 release-project）；发布流程本身不标准化。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“发布到主分支是否纳入本轮？”选项：A 只修模板 / B 标准化发布 / C 不动。答复：“A”。

### D12 旧配置位置继续兼容

- **决定：** 项目根 `workflow-config.yml` 与 `.claude/workflow-config.yml` 继续兼容读取，init-workflow 照旧提示迁移；兼容逻辑只留在规划侧。本轮部署的仓库迁到主路径 `.hskill/init-workflow/workflow-config.yml`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“旧配置位置是否继续兼容？”答复：“A”。
- **依据：** 9 个项目在项目根，1 个（harveyz-skill）在 `.claude/`。

### D13 本轮部署 harveyz-skill 与 agent-canvas

- **决定：** 本轮在 harveyz-skill 与 agent-canvas 重新部署文档、hooks、标准合并脚本；File Translator 及其余项目不在本轮。写 harveyz-skill 以外的仓库时另行取得用户授权。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“本轮在哪些仓库重新部署？”答复：“A”。

### D14 成功标准

- **决定：** 1 规划侧唯一解释策略，manage-worktree 读解释结果，测试覆盖有 staging、仅 main、master、三种配置位置；2 生成文档无旧写法，「开始新工作」指向 manage-worktree 并给兜底、「合并」指向标准脚本、有自填区、首次覆盖手改给提醒；3 标准脚本目标分支按配置渲染、项目检查走扩展点、生成的 hook 拦截不经脚本的合并并在两仓库实测；4 manage-worktree「合并」在集成分支或 detached HEAD 拒绝、缺标准脚本时停下、正常合并并报告，有测试；5 两仓库重新部署后实走：建 worktree 并用「合并」合进本地 staging，agent-canvas 超 token 预算仍被挡，自填区内容重跑后仍在；6 `npm test` 通过。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** 用户选择——问题：“怎么算做对了？”答复：“A”（按六条）。

### D15 hooksPath 未生效的项目不在本轮范围

- **决定：** 5 个项目 `core.hooksPath` 未生效，init-workflow 重跑即会修复，本轮不处理。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——init-workflow Step 4e 本就检测并修复 git config 漂移。

### D16 未装 manage-worktree 时的兜底写法

- **决定：** 文档兜底命令为 `git worktree add .worktrees/<分支名，/ 换成 +> -b <分支> <按配置推断的基线>`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——由 D5 推出，基线必须显式写出。

### D17 覆盖提醒的内容

- **决定：** 提醒写明文档将被覆盖，附找回手改内容的 `git diff` 命令；本轮要保留的内容在重新生成前由人工迁入自填区。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——由 D7（不自动迁移）推出。

### D18 最新工作流的权威定义

- **决定：** 以 harveyz-skill `CLAUDE.md` 的 Git 工作流与跨 session 交接两节、agent-canvas `AGENTS.md` 的 Step 3 与 Step 7 为准。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——两处是本次 devflow 刚更新的现行规则。

### D19 项目特有检查走扩展点

- **决定：** 项目特有的合并前检查（如 agent-canvas 的 token 预算）通过配置声明的扩展点挂入标准脚本，不写进脚本本体；机制在方案审查中确定。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——agent-canvas 的 token 预算检查写死在脚本里，标准化后需保留且不污染其他项目。

### D20 「合并」不决定时机

- **决定：** 「合并」只在用户明确说“合并”或项目指令规定时由调用方触发，动作本身不判断该不该合并。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——harveyz-skill `CLAUDE.md` 规定只在用户明确说“合并”或“完成”后合并。

### D21 缺标准脚本时停下

- **决定：** 仓库没有标准合并脚本时，「合并」停下并提示先运行 init-workflow，不退回手动 `git merge`。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——devflow 的“不自行兜底”原则（上一轮 D18）。

### D22 保留 skill 名 manage-worktree

- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——合并的是该 worktree 上的分支，仍属工作区生命周期。

### D23 「清理」本轮不做

- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断——D10 选 B 而非 C。

### D24 非 Claude Code 宿主未验证

- **决定：** manage-worktree 在 Codex 等宿主上的可用性未实测，本轮不验证。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断。

### D25 合并来源检查对脚本合并是否生效需先核实

- **决定：** pre-commit 靠解析 `MERGE_MSG` 判断合并来源；标准脚本用 `update-ref`。方案审查前先核实两者关系，结果可能影响 hook 设计。
- **状态：** 已批准（question-me 摘要确认）
- **来源：** Agent 推断。
- **核实结果：** 标准脚本以 `commit-tree` + `update-ref` 生成合并提交，不触发任何 hook，提交信息带 `Merge-Via: merge-to-staging.sh`（读代码，`scripts/merge-to-staging.sh:317`）。依 git 文档（未实测）：干净的 `git merge` 运行 `commit-msg`，`pre-commit` 只在存在 `pre-merge-commit` 时被连带运行；各项目都没有该 hook，故生成的 pre-commit 合并来源检查只在冲突后手动 commit 时生效。本会话处于 worktree 隔离，无法在 `/tmp` 实测，实测排入计划首个任务并写进验收标准。

### D30 解释结果在部署时写成文件

- **决定：** init-workflow 部署时把解释结果写入仓库内固定文件 `.hskill/init-workflow/resolved.env`（`key=value`，提交入库）；文档、hooks、标准合并脚本与该文件出自同一次解释；manage-worktree 只读该文件，不再解析配置。
- **状态：** 已批准
- **来源：** 用户选择——方案 C1：a 部署时写成文件 / b 运行时调用规划侧解析脚本。答复：“C1：a”。批准依据：本条答复。

### D31 没有解释结果文件时 manage-worktree 停下

- **决定：** 仓库没有 `resolved.env` 时，manage-worktree 停下并提示先运行 init-workflow，不保留旧解析作过渡。
- **状态：** 已批准
- **来源：** 用户选择——方案 C1b：a 过渡期保留旧解析并警告 / b 直接停下。答复：“C1b：b”。
- **代价（已告知）：** 新版 manage-worktree 装机后，未重新部署 init-workflow 的项目中 devflow 全部停下，直到重新部署；装机时机须与 D27 一并安排。

### D32 项目自填区为文档内保留块

- **决定：** 生成的 `git-workflow.md` 末尾设 `<!-- BEGIN PROJECT NOTES -->` / `<!-- END PROJECT NOTES -->`，重新渲染时原样保留两标记之间的内容。
- **状态：** 已批准
- **来源：** 用户选择——方案 C2：a 文档内保留块 / b 单独手写文件。答复：“C2：a”。

### D33 合并前项目检查在配置中声明

- **决定：** 配置新增 `merge.pre_checks`（命令列表，`{target}` 占位），部署时渲染进标准脚本的 MANAGED 块，按序执行，任一失败即不合并。
- **状态：** 已批准
- **来源：** 用户选择——方案 C3：a 配置声明 / b 约定目录。答复：“C3a”。

### D34 以提交标记拦截不经脚本的合并

- **决定：** 由配置生成 commit-msg 与 pre-push 拦截：在合并目标分支上做合并而提交信息没有 `Merge-Via: <脚本名>` 即拒绝；推送合并目标分支时检查同一标记。pre-commit 按来源检查合并的逻辑只保留给不走脚本的受保护分支。
- **状态：** 已批准
- **来源：** 用户选择——方案 C4：a 认标记行 / b 拦截所有手动合并。答复：“C4a”。

### D35 compose-agentsmd 不再手填集成分支与合并方式

- **决定：** compose-agentsmd 的 devflow 包删除 `merge_command` 参数，合并写法固定为“调用 manage-worktree「合并」”；`integration_branch` 改为生成时从 `resolved.env` 读取，文件缺失时报错并提示先运行 init-workflow。
- **状态：** 已批准
- **来源：** 用户选择——问题：“compose-agentsmd 这两个参数怎么处理？”选项：A 本轮一起改 / B 只改合并写法 / C 不动。答复：“A”。
- **依据：** compose-agentsmd 0.1.0 已合入 staging，两个必填参数是集成分支与合并方式的第三处手填副本；harveyz-skill 与 agent-canvas 都尚未部署它。

### D36 两仓库实走拆为合并前（副本）与合并后（真实仓库）两段

- **决定：** 合并前在 `/tmp` 克隆的两仓库副本上部署并完整实走，不触碰真实 staging；合并后在真实仓库部署，只做不留痕的核对（一次手动合并被拒、四类产物取值一致）。细化 D14 第 5 条。
- **状态：** 已批准
- **来源：** 用户选择——问题：“两个仓库的实际走查放在什么时候、在哪里做？”选项：A 拆成合并前副本与合并后核对 / B 只在合并后做。答复：“A”。
- **依据：** 构建者检查指出，部署只在功能分支上时，真实 staging 上没有新产物，合并前无法实走，且实走会在真实 staging 留下测试合并。

## 未决事项

### D26 manage-worktree「清理」（合并后移除 worktree、删分支）

- **状态：** 已提出，留待以后
- **来源：** 用户选择——D10 未选“合并与清理”。

### D27 File Translator 与其余 16 个项目的部署

- **状态：** 已提出，留待以后
- **来源：** 用户选择——D13。

### D28 发布流程标准化

- **状态：** 已提出，留待以后
- **来源：** 用户选择——D11。

### D29 新 git skill 是否取代 init-workflow 作为规划侧

- **状态：** 已提出，留待以后
- **来源：** Agent 推断——`2026-11-08-plan-handoff-worktree` Spec 第 9 节未决“新的 git skill，融合 init-workflow 的分支规则”；按 D3，它即规划侧。

## 已否定与已失效

（暂无）

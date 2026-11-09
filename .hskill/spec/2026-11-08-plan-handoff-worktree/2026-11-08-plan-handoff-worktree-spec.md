# Spec：计划后交接与统一 worktree 管理

- **版本：** v0.2（送审稿，未批准；v0.1 经构建者检查后修订）
- **决定记录：** `2026-11-08-plan-handoff-worktree-record.md`（下文以 D 编号引用）
- **分支：** `feature/plan-handoff-worktree`
- **未决事项：** 见第 9 节

## 1. 意图与目标

强模型（如 Opus）负责需求澄清、Spec、实施计划三道人工确认，确认后把计划交给较弱、可能跨厂商或跨框架（Claude Code、Codex、opencode）的执行模型实施，再由强模型验收；主要动机是省钱/省额度（D1、D2、D3）。

要做到这一点，需要三件事同时成立：

1. 从 init-spec 建档起，所有产物（决定记录、Spec、计划、交接文档）都落在同一个命名分支的 worktree 里并已提交，接手方进入该 worktree 就能看到全部依据（D10、D13）。
2. worktree 的建立、复用、进出、检测只有一套写法，由新 skill `manage-worktree` 承担，各调用方统一调用（D10、D12）。
3. 计划确认时有一个询问点，让用户选择本会话执行还是交接（D15、D16）。

## 2. 范围

**本轮做：**

- 新建 `manage-worktree` skill（D10、D12、D17）。
- 把 `superpowers-rewrite` bundle 改名为 `devflow`，并把 `manage-worktree` 放入该 bundle（D17）。
- 修改 init-spec、develop-plan、handoff 三个 skill（D8、D11、D16、D18）。
- 修改 AGENTS.md、CLAUDE.md、`.hskill/handoff/config.md`（D7、D16、D17）。

**本轮不做：**

- init-skill、contribute-skill 迁到 manage-worktree（D11，留待以后）。
- 合并与清理 worktree、删分支（D12）。
- 自动路由（D15，留待以后）。
- 新的 git skill，以及把 init-workflow 的规则并入它（D17，留待以后）。
- 计划详略标准、`REQUIRED SUB-SKILL` 写法、handoff 四阶段协议主体（D4、D8、D19）。
- npm 发布（D21）。

## 3. 不可接受的结果

- 新分支从当前 HEAD 静默拉出，夹带其他会话未合并的提交（D14）。
- 交接文档指向的 Spec 或计划没有提交到交接分支，接手方看不到（D8）。
- 交接文档没有写明工作区路径，接手方要自己猜在哪开工（D8）。
- 任何调用方在 manage-worktree 不可用时自行兜底建 worktree，导致写法再次分散（D18）。
- 已验收、执行中、待验收等非「待执行」状态的交接文档，以及没有 `workspace_mode` 字段的文档，校验结果发生变化（D21，范围见 5.6）。
- manage-worktree 删除任何 worktree 或分支（D12）。

## 4. 现状（实施前提）

- worktree 逻辑分散在五处：handoff（author 第 4 步建 worktree，以及文末「平台适配」一节的分宿主进出写法）、develop-plan（第 1 步“工作区”，无规则时调用 `superpowers:using-git-worktrees`）、init-skill（`.worktrees/feature-init-<name>`）、contribute-skill（`.claude/worktrees/feature+contribute-<name>`）、CLAUDE.md 与 AGENTS.md 各写一份建 worktree 的步骤。
- init-spec 没有工作区步骤，决定记录和 Spec 写在项目根下的 `.hskill/spec/` 中，位置取决于会话当前所在目录。
- develop-plan 第 5 步原文：“确认后直接使用 `superpowers:subagent-driven-development` 执行，不询问执行方式”。
- `validate-handoff.sh` 不检查引用文件或交接文档是否已提交；`same-workspace` 模式下跳过全部工作区校验。`workspace_mode` 字段在 handoff 1.17.1 已存在：模板、`docs/commute/` 下两份文档、bats 用例 35–40 都在用；bats 默认 fixture 的 `status` 为「待执行」，文档未被 git 跟踪。
- handoff 的 verify 与 accept 都会重跑 `validate-handoff.sh`；接手方在执行中修改 `status`、写自测记录后，没有提交义务。
- init-workflow 按以下顺序查找规则文件：`.hskill/init-workflow/workflow-config.yml`（主路径）→ 项目根 `workflow-config.yml` → `.claude/workflow-config.yml`（后两者为向后兼容，init-workflow 会询问是否迁到主路径）。本仓库目前在第三个位置，其中有：`branches.protected`（`main`、`staging`），各受保护分支的 `merge_from`（`staging` 接收 `feature/*`、`fix/*`、`chore/*`、`doc/*`），`branch_naming.allowed_patterns`。该文件没有 worktree 路径字段。
- 本仓库的 `core.hooksPath=.githooks` 与 `merge.ff=false` 记录在共享的 `.git/config` 中，对所有 worktree 生效。
- `.worktrees/` 与 `.claude/worktrees/` 都已被 `.gitignore` 忽略。
- bundle 名即 `skills/` 下的目录名。`superpowers-rewrite` 当前含 question-me、init-spec、develop-plan；引用该名称的位置有 `skills-index.json`（3 个 skill 的 `bundle` 字段和 `bundleMeta` 键）、`package.json` 的 `files`（由 `scripts/generate-npmignore.js` 从 `skills-index.json` 生成）、`tests/skill-portability.test.mjs`、init-spec 正文（HARD-GATE 一段）、`docs/product/PRD.md`。
- 安装器中没有 bundle 之间的依赖机制；已安装副本按 skill 名平铺，不按 bundle 分目录。
- `superpowers:subagent-driven-development` 支持 Claude Code 与 Codex 等宿主，宿主不能派 subagent 时自行退回 `executing-plans`；开工前检测已在 worktree 中就不再新建（D19）。

## 5. 方案

### 5.1 整体流程

```
question-me（不写文件）
   |
init-spec 建档前 --> manage-worktree「准备」：建或复用 worktree，进入并检测
   |                    （新建时先请用户确认基线、分支名、路径）
   v
init-spec 在该 worktree 写决定记录、Spec，并提交
   |
develop-plan --> manage-worktree「准备」：复用同一 worktree（不问）
   |           写计划并提交；请用户确认计划
   v
计划确认后：项目指令规定了询问 --> 问用户「本会话执行 / 交接」
   |                                   |
   | 本会话执行（默认）                 | 交接
   v                                   v
subagent-driven-development       handoff author：用当前 worktree 作为交接工作区，
                                   写交接文档并提交，过门禁，派发
                                         |
                                  接手方 verify --> manage-worktree「进入」该路径并检测
                                         |
                                  执行、自测 --> 交出方 accept（「进入」同一路径）
```

### 5.2 manage-worktree（新 skill）

**位置：** `skills/devflow/manage-worktree/`，属于 `devflow` bundle（D17）。

**职责：** 建或复用、进出、检测三类动作；不做合并、清理、删分支（D12）。

**对外动作：**

| 动作 | 输入 | 行为 | 结果 |
|---|---|---|---|
| 准备 | 任务 topic（用于分支名 slug）；可选的期望分支类型；可选的锚点文件路径（本任务已产生的决定记录、Spec 或计划） | 按下文“建或复用”的规则找到或建出工作区，进入，检测 | 工作区绝对路径、分支名、基线（新建时）、检测结果 |
| 进入 | 已有工作区的绝对路径；可选的期望分支名 | 按宿主进入该路径并检测；分支与期望不符时报告，不自行切换 | 同上 |
| 检测 | 无（检测当前所在工作区） | 只读检测 | 检测结果 |
| 离开 | 无 | 按宿主离开并保留工作区 | — |

**规则来源（D17）：** 按 init-workflow 的查找顺序读取第一个存在的规则文件（`.hskill/init-workflow/workflow-config.yml` → 项目根 `workflow-config.yml` → `.claude/workflow-config.yml`），只读不迁移：

- **集成分支：** `branches.protected` 中列出的分支。
- **基线推断：** 新分支类型（默认 `feature`）对应的 `<type>/*` 出现在哪个受保护分支的 `merge_from` 里，就用那个分支（本仓库为 `staging`）。
- **命名：** 分支名须匹配 `branch_naming.allowed_patterns`。

文件不存在时：集成分支取仓库默认分支（远端 `HEAD` 指向的分支；取不到时依次尝试 `main`、`master`），基线同上，分支名默认 `feature/<slug>`（D14）。

**建或复用（按顺序判断，命中即止）：**

“链接 worktree”指 `git worktree add` 建出的工作区，不含仓库主工作树。

0. 给了锚点文件 → 找到包含该文件的工作区；它是处于命名、非集成分支的链接 worktree 时复用，不询问；否则报告原因，转入规则 1–4。这一条保证换会话后，develop-plan、handoff 仍能回到建档时的同一工作区。
1. 当前目录是链接 worktree 的根，处于命名分支且不是集成分支 → 复用，不询问（D14）。
2. 期望分支已存在，并已被某个链接 worktree checkout → 复用那个 worktree，不询问。
3. 期望分支已存在，但没有被任何工作区 checkout → 为它新增 worktree（不建新分支），在默认路径下；告知路径，不询问基线。
4. 其他情况（含主工作树停在某条功能分支上、处于 detached HEAD、处于集成分支、未给锚点的新会话）→ 新建：先向用户一次确认基线、分支名、路径；基线按“规则来源”推断，当前所在分支（若是非集成的命名分支）列为可选的另一基线（D14）。用户确认后从显式基线拉分支建 worktree。

**默认路径（D17）：** `<仓库根>/.worktrees/<分支名，/ 换成 +>`。该目录未被 git 忽略时，把补写 `.gitignore` 的改动并入新建前的那次确认，确认后提交该改动。

**检测项（D18）：** 每项给出通过、不通过及原因：

- 当前目录是一个链接 worktree 的根目录（不是主工作树）。
- 处于命名分支，不是 detached HEAD。
- 当前分支不是集成分支。
- 仓库存在 `.githooks/` 目录时，`core.hooksPath` 指向它。

**按宿主进出（从 handoff「平台适配」迁入，语义不变）：**

- **Claude Code：** 用 `EnterWorktree(path: <绝对路径>)` 进入，绝不用 `name` 模式；离开用 `ExitWorktree(action: "keep")`；工具未加载时先用 ToolSearch 加载，不降级为 `cd`；必须由当前会话直接调用，不交给 subagent。
- **Codex：** 让会话的 workspace 根就是该路径（CLI 用 `codex -C <路径>`，App 打开该 worktree）；不用 `--worktree`，因为它会另建 managed worktree。
- **其他宿主或无法绑定时：** git 命令一律 `git -C <路径>`，其他 shell 命令写成同一条 `cd <路径> && <命令>`，文件读写一律用绝对路径。

**非 git 目录：** 返回“不适用”，调用方在当前目录继续。

### 5.3 bundle 改名

`skills/superpowers-rewrite/` 整体改名为 `skills/devflow/`，同步修改第 4 节列出的所有引用位置，并为 `devflow` 写 `bundleMeta` 描述（含 manage-worktree）。重新生成 `package.json` 的 `files`。不为旧名 `superpowers-rewrite` 保留别名。

### 5.4 init-spec

在第一阶段第 4 步“建档”写决定记录之前，调用 manage-worktree「准备」，在返回的工作区里写决定记录与 Spec，按项目 Git 规则提交。

- manage-worktree 不可用：停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree（D18）。
- 返回“不适用”（非 git 目录）：在当前目录继续。
- HARD-GATE 中的 bundle 名改为 `devflow`。

### 5.5 develop-plan

- **第 1 步“工作区”：** 改为调用 manage-worktree「准备」。接续 init-spec 时把已批准 Spec 的路径作为锚点传入，命中复用；独立调用时可能新建。删除“没有专门规则时使用 `superpowers:using-git-worktrees`”。不可用时同 5.4。
- **第 5 步：** 把“确认后直接使用 `subagent-driven-development` 执行，不询问执行方式”改为：项目指令对计划确认后的执行方式另有规定时按项目指令，否则直接使用 `subagent-driven-development`（D16）。`REQUIRED SUB-SKILL` 的写法不变（D19）。

### 5.6 handoff

**author 第 4 步（D8）：** 判定条件从“接手方是否在另一条分支上开工”改为“接手方是另一个会话，需要被指到一个确定的工作区”。

- 调用 manage-worktree「准备」，有计划或 Spec 时把它的路径作为锚点传入：已在命名分支的链接 worktree 里就复用它，否则按 manage-worktree 的规则新建。
- 文档里写明 `workspace_mode`、`branch`、`worktree`。复用当前工作区时填 `same-workspace`，新建交接工作区时填 `shared-worktree`；两种模式都必须填 `branch` 与 `worktree`。
- manage-worktree 不可用时同 5.4。

**author 第 7、8 步顺序：** 先落库（提交交接文档及其引用的、本次产生的产物），再跑完整性门禁；门禁不过就修改、重新提交、重跑。这样门禁才能检查“已提交”。

**verify 与 accept：** “进入 author 备好的工作区”改为调用 manage-worktree「进入」，传入 `worktree` 路径和期望的 `branch`；检测不通过时按现有规则打回，不自行开工。

**文末「平台适配」一节：** 改为指向 manage-worktree 的“进入”与“离开”，删去重复内容。

**`validate-handoff.sh` 新增检查（D18）：** 只在文档同时满足“含 `workspace_mode` 字段”和“`status` 为「待执行」”时生效。「待执行」覆盖 author 门禁与接手方 verify 两个时点，正是“接手方开工时必须看得到”的检查对象；执行中、待验收、已验收、打回的文档不受影响，因此 accept 不会因接手方未提交而误判打回。现有 bats 用例 37、40（含 `workspace_mode`、状态为「待执行」、文档未跟踪）的 fixture 需要把文档提交后再校验，期望结果不变。

| 检查 | 不通过时 |
|---|---|
| 任一模式下 `branch` 与 `worktree` 都已填写 | ERROR |
| 交接文档本身已被 git 跟踪，且没有未提交改动 | ERROR |
| 正文链接指向仓库内已存在的文件时，该文件已被跟踪且没有未提交改动 | ERROR |
| 正文链接指向不存在的文件 | WARN（保持现状） |

### 5.7 AGENTS.md、CLAUDE.md、`.hskill/handoff/config.md`

**AGENTS.md「跨会话交接」新增小节“计划后交接给执行模型”（D3、D5、D6、D9、D15、D16）：**

1. develop-plan 的计划经用户确认后，先询问用户“本会话执行，还是交接给其他执行方”。
2. 选择交接：不调用执行技能。交出方先把计划开头的 `REQUIRED SUB-SKILL` 填为 `superpowers:subagent-driven-development` 并提交计划，再走 handoff 的 author 阶段。一份计划对应一次交接。交接文档列 Spec 与计划为权威依据。最小验收锚点写成“各 Task 的测试与计划写定的断言一致，并全部通过”，再加上 Spec 的验收标准。
3. 接手方按计划执行，可自行决定函数内部实现；不得修改接口签名、测试名称与断言、`Global Constraints`；计划与现状冲突时停手打回。

**AGENTS.md「Git 与工作区」：** 建 worktree 改为调用 manage-worktree；路径约定改为 `.worktrees/<分支名，/ 换成 +>`，`.claude/worktrees/` 改称历史遗留。

**CLAUDE.md：** 同步上述两处，沿用现有“两份文件各写一份”的做法。worktree 路径习惯一节与“建 worktree 的硬动作”改为调用 manage-worktree，并更新路径。

**`.hskill/handoff/config.md` 的 workflow 段：**

- 删除“用 `superpowers:writing-plans` 从 spec 拆任务，`superpowers:executing-plans` 执行”，改为“计划由交出方在交接前用 develop-plan 写好并经用户确认；接手方按计划开头的 `REQUIRED SUB-SKILL` 执行，不重写计划”。
- 路径习惯改为 `.worktrees/`。
- 进入工作区的写法改为指向 manage-worktree。
- 保留“看到建新 worktree 的建议一律跳过”的提醒。

### 5.8 版本

改动的 skill（manage-worktree 新建为 `0.1.0`；init-spec、develop-plan、handoff 升版本；question-me 只因目录迁移而变动）更新 `skills-index.json` 的 `contentHash` 与 `contentVersion`（D21）。

## 6. 状态与异常路径

| 情形 | 结果状态 |
|---|---|
| 用户拒绝新建前的确认 | 不建 worktree；调用方停下，告诉用户可改选基线、分支名或路径后重来 |
| 基线分支在本地不存在 | 不新建；报告原因，请用户指定基线 |
| 期望分支已被另一个 worktree checkout | 复用那个 worktree（规则 2），不另建 |
| 「进入」的路径不存在或不是 worktree 根 | 报告不通过；handoff 的 verify/accept 按现有规则打回或重建 detached 工作区，manage-worktree 不自行修复 |
| 「进入」后分支与期望不符 | 报告不通过，不切换分支 |
| 宿主不允许进入该路径（如跨仓库） | 退回“其他宿主”方式，用显式路径 |
| 交接门禁发现引用的产物未提交 | ERROR；author 提交后重跑 |
| manage-worktree 不可用 | 调用方停下，提示安装 |

## 7. 验收标准

1. `npm test` 通过。
2. 新 skill 通过格式校验并登记：`skills/devflow/manage-worktree/SKILL.md` 存在，已在 `skills-index.json` 中登记，bundle 为 `devflow`。
3. 改名后的打包无误：`skills/superpowers-rewrite/` 不再存在；`skills-index.json`、`package.json`（重新生成后）、`tests/skill-portability.test.mjs`、init-spec 正文、PRD 中不再出现 `superpowers-rewrite`。
4. handoff 的 bats 测试新增以下用例，并全部通过（以下均指含 `workspace_mode`、状态为「待执行」的文档，除非另注）：
   - `same-workspace` 但缺 `worktree` → exit 1；
   - 交接文档未被跟踪 → exit 1；
   - 交接文档有未提交改动 → exit 1；
   - 正文链接指向一个未被跟踪的已存在文件 → exit 1；
   - 正文链接指向一个已跟踪但有未提交改动的文件 → exit 1；
   - 全部已提交的合规文档 → exit 0；
   - 状态为「执行中」「待验收」的文档未提交 → 结果与改动前一致；
   - 不含 `workspace_mode` 的文档，在上述各种情形下结果与改动前一致；
   - 既有用例 37、40 只改 fixture（先提交文档），期望值不变。
5. 文本核对：
   - develop-plan 第 5 步不再含“不询问执行方式”，并含“项目指令另有规定时按项目指令”的分支；第 1 步不再引用 `using-git-worktrees`。
   - init-spec 建档步骤在写决定记录前调用 manage-worktree。
   - handoff 第 4 步的判定条件是“接手方是另一个会话”；「平台适配」一节指向 manage-worktree。
   - AGENTS.md 与 CLAUDE.md 都含“计划后交接给执行模型”的规则。
   - `.hskill/handoff/config.md` 不再提 `writing-plans` 和 `executing-plans`。
   - CLAUDE.md、AGENTS.md、config.md 中的 worktree 路径约定为 `.worktrees/`。
6. 端到端演练（人工，由用户执行）：在合并进 `staging`、按 CLAUDE.md 规定从 `staging` 装机之后进行，不属于合并前的验收。在本仓库从 init-spec 走到计划确认，选择“交接”，确认交接文档的 `worktree` 指向建档时的同一工作区、文档已提交、门禁通过。演练产生的 worktree 与分支由用户按现有流程清理。合并前的验收只包括第 1–5 条。

## 8. 由 Agent 决定、随本稿送审的次要决定

- **S1：** handoff 的「平台适配」内容迁入 manage-worktree，handoff 只保留指针（由 D12“进出归 manage-worktree”推出）。
- **S2：** 新文档两种 `workspace_mode` 都必须填写 `branch` 与 `worktree`；`same-workspace` 改为表示“复用交出方当前的工作区”。
- **S3：** handoff author 改为先提交、后跑门禁，否则“已提交”无法检查。
- **S4：** 期望分支已存在但未被 checkout 时，为它新增 worktree，视为复用，不询问基线。
- **S5：** 非 git 目录下 manage-worktree 返回“不适用”，调用方在当前目录继续。
- **S6：** 检测项“hooks 已配置”只检查 `core.hooksPath`；`merge.ff=false` 等本仓库特有设置仍由 AGENTS.md 和 CLAUDE.md 规定（它们存在共享的 `.git/config` 中，对所有 worktree 生效）。
- **S7：** bundle 改名不保留旧名别名。
- **S8：** CLAUDE.md 按现有做法同步 AGENTS.md 的新规则。
- **S9：** manage-worktree 按 init-workflow 的三级查找顺序读规则文件（已有答案：init-workflow 的主路径是 `.hskill/init-workflow/workflow-config.yml`）。
- **S10：** 「准备」接受锚点文件路径，换会话后靠它回到建档时的工作区；没有锚点时按规则 4 新建并请用户确认，用户可在确认时改选已有分支。“链接 worktree”不含主工作树（由 D14 推出）。
- **S11：** 选择交接时，交出方把 `REQUIRED SUB-SKILL` 填为 `superpowers:subagent-driven-development` 并提交计划后再交接（由 D19 推出）。
- **S12：** 端到端演练放在合并、从 `staging` 装机之后；合并前只做第 7 节第 1–5 条（CLAUDE.md 规定装机只能从 `staging` 取）。
- **S13（推断）：** D17 记录的代价“Claude Code 中启动时固定工作目录的 subagent 无法切进 `.worktrees/`”只影响需要中途切换工作区的 subagent。`subagent-driven-development` 派出的 subagent 从主会话当前目录（已在 worktree 内）启动，不需要切换，默认执行路径不受影响；未实测。

## 9. 未决事项

- init-skill、contribute-skill 迁到 manage-worktree。
- 本会话执行与交接之间的自动路由。
- 新的 git skill，融合 init-workflow 的分支规则；届时 manage-worktree 改读它。
- **未查证：** opencode 是否支持 subagent 派发（不支持时，`subagent-driven-development` 自行退回 `executing-plans`）。
- **未查证：** 安装器对已安装用户的 bundle 改名升级路径。

## 上游 skill 与本文件的优先级

`question-me`、`init-spec`、`develop-plan`、`manage-worktree`、`handoff`（以下合称 devflow）在本仓库
使用时，下列规则优先于 skill 自身的默认行为：

1. **落点**：spec 写到 `@{spec_dir}/YYYY-MM-DD-<slug>-design.md`，决定记录写到
   `@{record_dir}/YYYY-MM-DD-<slug>/YYYY-MM-DD-<slug>-record.md`，plan 写到
   `@{plan_dir}/YYYY-MM-DD-<slug>.md`。
2. **分档**：分档只由 Step 2 决定。`question-me` 摘要确认后即结束，不走它的路由；低档的测试清单和
   闸门 2 照常走 Step 4。
3. **闸门**：`init-spec` 的方案比较与 spec 合在一次闸门 2 里送审，不逐项单独审批；`develop-plan` 写完
   plan 后送用户确认（闸门 3），确认后先问“本会话执行，还是交接给其他执行方”，按 5.3 执行。
<!-- @if agent_canvas -->
4. **闸门后动作**：spec 获批后，先做 4.3 第 4 条的画布动作，再调用 `develop-plan`。
   `init-spec` 中“此处不得调用其他技能”不限制这些动作。
5. **验收标准**：spec 的 `## 验收标准` 按 4.2 的格式写，不用 skill 的通用写法替代。
<!-- @endif -->

## Step 1 澄清（人工闸门 1）

### 1.1 说明

需求进入后的第一步。**默认用户的初始输入不是定稿需求**，不得直接进入分流或开发。只有明确
复述需求、范围和成功标准，并得到用户确认，才算通过闸门并进入 Step 2。

### 1.2 标准

按输入形态选择当前会话可用的能力：

| 输入形态 | 处理方式 |
|---|---|
| 意图清楚但表述有歧义 | `rephrase`（单轮） |
| 目标模糊、多解或缺成功标准 | `question-me`（多轮，一次一问） |
| 要做新东西且方案未定 | `question-me`（只做澄清）；方案比较和 spec 由 Step 4 的 `init-spec` 接手 |

### 1.3 执行细则

本阶段不写代码、不建分支；读代码仅限为澄清问题收集依据。

### 1.4 特例

- 琐碎档也必须澄清，一轮复述确认即可。
- 用户声明“走 spec 路径（旧称 SDD）/ 走 TDD”不构成跳过；它只指定路径，不代表需求已定稿。

## Step 2 复杂度判定

### 2.1 说明

澄清收口后定档。档位决定 Step 3–6 的路径；定档后继续执行，不另设人工闸门。

### 2.2 标准

| 档 | 判定信号 | 路径 |
|---|---|---|
<!-- @if complexity_signals -->
| 高 | 跨进程或跨模块、修改数据模型或持久化格式、修改协议/状态机/生命周期、多方案需取舍、可拆成 3 个以上任务、@{complexity_signals} | **spec 路径**：spec → plan → execute |
<!-- @else -->
| 高 | 跨进程或跨模块、修改数据模型或持久化格式、修改协议/状态机/生命周期、多方案需取舍、可拆成 3 个以上任务 | **spec 路径**：spec → plan → execute |
<!-- @endif -->
| 低 | 单模块、方案唯一、需求能被一组测试用例说清（bugfix、小增强、纯函数逻辑） | **TDD**：测试清单 → 实现 |
<!-- @if agent_canvas -->
| 琐碎 | 文案、注释、配置项、重命名、纯文档 | 直接改，无 spec、无测试清单、不调用画布 skill |
<!-- @else -->
| 琐碎 | 文案、注释、配置项、重命名、纯文档 | 直接改，无 spec、无测试清单 |
<!-- @endif -->

### 2.3 执行细则

默认由当前 agent 判定。先用一行“判为 X 档，因为 Y”说明，再继续执行，供用户随时否决，但
不额外停顿。

### 2.4 特例

用户已声明档位时以用户声明为准。

## Step 3 建分支 + worktree

### 3.1 说明

澄清收口并定档后、写任何产物之前执行。此后一切落盘产物都在同一分支、同一 worktree 中，
不再换工作区。`@{integration_branch}` 主工作树必须保持干净。

### 3.2 标准

- 默认源码工作使用 `feature/<slug>`。
- 纯文档且确定不会改源码时使用 `doc/<slug>`。
- bugfix 可使用 `fix/<slug>`；判断不准时使用 `feature/<slug>`。
- 基线 `@{integration_branch}`、路径都由 `manage-worktree` 按规则推断，新建前
  向用户确认一次。

### 3.3 执行细则

调用 `manage-worktree`「准备」，传入 slug 作为 topic、按 3.2 选定的分支类型；它负责复用或新建、
进入与检测，本文不重复它的规则。由谁调用按档位区分：

| 档 | 调用方 |
|---|---|
| 高 | `init-spec` 建档前、`develop-plan` 开工前（以 spec 路径为锚点复用）各自调用；当前 agent 不另行调用 |
| 低、琐碎 | 当前 agent 在写测试清单或改动前直接调用 |

检测有未通过项时不开工。

### 3.4 特例

- 同一里程碑复用已有分支，不为每轮反馈新建分支。
- Step 4 否决产物时在原分支修订；只有明确作废后才移除 worktree 与分支。

## Step 4 写产物（人工闸门 2）

### 4.1 说明

按档位写 spec 或测试清单并送审。低档的闸门同时确认两件事：产物内容是否通过，以及后续开发由
当前任务继续，还是 handoff 给另一任务或 agent。高档在这里只审 spec；是否 handoff 留到 Step 5
plan 确认后（闸门 3）再定。

### 4.2 标准

| 档 | 产物 | 落点 |
|---|---|---|
<!-- @if agent_canvas -->
| 高（spec 路径） | spec，须含 `## 验收标准` 一节（与判据分开） | `@{spec_dir}/YYYY-MM-DD-<slug>-design.md` |
| 低（TDD） | 一页测试清单：一句话需求 + “输入 → 预期”用例 + 涉及文件，须含 `## 验收标准` 一节（与判据分开） | `@{spec_dir}/YYYY-MM-DD-<slug>-test-plan.md` |
<!-- @else -->
| 高（spec 路径） | spec，须含 `## 验收标准` 一节 | `@{spec_dir}/YYYY-MM-DD-<slug>-design.md` |
| 低（TDD） | 一页测试清单：一句话需求 + “输入 → 预期”用例 + 涉及文件，须含 `## 验收标准` 一节 | `@{spec_dir}/YYYY-MM-DD-<slug>-test-plan.md` |
<!-- @endif -->
| 高/低，涉及前端或由前端驱动 | 设计稿 | 与 spec / 测试清单同期完成并送审 |

<!-- @if agent_canvas -->
测试清单与 spec 同目录是刻意的：`describe-node` 的 spec 自动发现只认 `docs/superpowers/specs/`
前缀，放别处就得每次手传 `--spec`。

`## 验收标准` 是第二道关（版本验收）的依据，写法（每条一个 `### V<n>｜类别｜验证方式` 三级
标题加标签）如下：

```markdown
## 验收标准

### V1｜真实环境生效｜机器可查
标签：……
正文：怎么验、去哪看、什么算通过，长度不限。

### V2｜没有引出新问题｜观察期 7 天
标签：……
```

- **类别**四选一：真实环境生效、原始问题消失、没有引出新问题、体验可接受。
- **验证方式**三选一：机器可查、观察期 N 天、人工裁决。「体验可接受」只能配人工裁决。
- **标签**是一句话，不超过 60 字，用来在界面上标识这一条，不是判据正文；判据以 spec 正文为准。
- **自检**：每写一条，问一句「它能在隔离的 E2E 环境里被证明吗」。能，就属于第一道关，挪进判据。
- 「原始问题消失」要引用 spec「现状与缺口」里的一处痛点。
- **解析认哪一节**：二级标题去掉可选的「数字.」前缀后以「验收标准」开头即算（如 `## 10. 验收标准（…）`）；``` 围栏代码块里的内容（如上面的示例）不参与解析。

判据（J 编号）是第一道关的依据，能在隔离 E2E 里证明的内容放判据，不放验收标准。
<!-- @else -->
`## 验收标准` 是 handoff 验收与完成判定的依据，写法按 `init-spec` 的默认写法。
<!-- @endif -->

### 4.3 执行细则

1. 将产物直接写入 Step 3 建好的最终开发分支并提交。
2. 送审并等待用户确认内容。
3. 低档：让用户决定当前任务继续，还是 handoff。高档跳过本条，见 5.3。
<!-- @if agent_canvas -->
4. 闸门通过后、handoff 分叉前，若当前任务位于 Agent Canvas 节点且相关 skill 可用，依次调用：
   `describe-node` 第一次、`capture-requirement`（全流程仅一次，带 `--acceptance-spec <spec 绝对路径>`）、
   `relate-node` 第一次。
<!-- @endif -->

### 4.4 特例

- 琐碎档跳过整个 Step 4，直接进入 Step 5。
<!-- @if agent_canvas -->
- 不在 Agent Canvas 节点或相关 skill 不可用时，跳过 4.3 第 4 条，不伪造成功。
<!-- @endif -->
- 决定 handoff 后，整套交接使用共享 `handoff` skill（author → verify → self-test → accept），
  项目约定读取 `.hskill/handoff/config.md`，本文件不重复 skill 内部流程。交接沿用 Step 3 的
  worktree，不另建 worktree 或分支。
<!-- @if agent_canvas -->
- `describe-node` 的 `--spec`（本文所有调用通用）：Claude 节点不传，App 自行认 spec；回执里没有
  `specStatus` 说明是旧版 App，改为显式传。Codex、pi 节点和旧版 App 显式传 spec 的绝对路径：
  相对路径会静默失败（返回 `specUsed: null`）；会话读过别的 spec 时自动发现会退到 Read 档、
  命中多份就放弃（接手节点只 Read 过 spec，尤其要显式传）。
- handoff 时，交出节点只执行 `describe-node` 第一次；接手节点开工前执行自己的第一次。
<!-- @endif -->

## Step 5 执行

### 5.1 说明

按档位完成实现。

### 5.2 标准

| 档 | 做法 |
|---|---|
| 高（spec 路径） | 闸门 2 通过后用 `develop-plan` 写 plan 并提交，送用户确认（闸门 3），再按 5.3 本会话执行或交接 |
| 低（TDD） | 按已批准的测试清单实现 |
| 琐碎 | 直接修改 |

### 5.3 执行细则

高档 plan 经用户确认后，先询问用户“本会话执行，还是交接给其他执行方”：

- **本会话执行**：按 plan 开头的 `REQUIRED SUB-SKILL` 执行（由 `develop-plan` 按条件选定）。
  总控 agent 不得把 plan + execute 整包交给单个 subagent。
- **交接**（计划后交接给执行模型）：不调用执行 skill。交出方按 `develop-plan` 的条件（执行方为全新会话）选定执行 skill，
  填入 plan 开头的 `REQUIRED SUB-SKILL` 并提交 plan，再走 `handoff` 的 author 阶段；交接文档写明所选 skill 及理由。一份
  plan 对应一次交接；交接文档把 spec 与 plan 列为权威依据；最小验收锚点写成“各 Task 的测试与 plan 写定的断言一致，并全部通过”，再加上
  spec 的 `## 验收标准`。其余按 4.4 的 handoff 特例。
- **接手方的边界**：按 plan 执行，可自行决定函数内部实现；不得修改接口签名、测试名称与断言、
  `Global Constraints`；plan 与代码库现状冲突或无法照做时，停止并打回交出方。执行 skill 要求的自行裁决只适用于上述不可修改项以外的问题；涉及不可修改项的冲突，包括任务审查者提出的，一律停止并打回。

派发要在指定 worktree 里改文件或跑 git 的 subagent 时，prompt 第一段写目录守卫命令
（`cd <绝对路径> && git rev-parse --show-toplevel && git branch --show-current`，结果不符就停）。
任务完成后，总控自己核对提交落在哪个 worktree、哪条分支，以及 `Co-Authored-By` trailer 是否
符合要求。只在正文里写一句“在某路径下工作”不算数。

## Step 6 测试分级

### 6.1 说明

实现完成后、汇报前执行。

### 6.2 标准

| 情形 | 测试 |
|---|---|
<!-- @if e2e -->
| 高复杂度或涉及前端 | 必须对真实编译产物执行 @{e2e} |
<!-- @else -->
| 高复杂度或涉及前端 | 端到端测试，方式由「仓库环境」或「其他约定」规定 |
<!-- @endif -->
| 低复杂度且纯后端逻辑 | 单元测试或集成测试即可 |
| 琐碎 | 无测试；仍需执行文档/差异检查 |

### 6.3 执行细则

E2E 未通过即任务未完成，不得以“单测全绿”宣告完成。

## Step 7 验证、集成与汇报

### 7.1 说明

<!-- @if agent_canvas -->
非闸门。验证通过后，由负责集成的 agent 完成（或确认无需）合并，再汇报，随后直接进入 Step 8。
<!-- @else -->
非闸门。验证通过后，由负责集成的 agent 完成（或确认无需）合并，再汇报。
<!-- @endif -->

### 7.2 标准

宣告完成前必须：

1. 检查 `git status --short` 与 `git diff --check`。
2. 运行与风险匹配的测试，并使用 `superpowers:verification-before-completion` 取得新鲜证据。
3. 明确区分“已运行并通过”“未运行”“因环境受阻”，不用推测替代结果。
<!-- @if agent_canvas -->
4. 判定集成责任：独立节点或不在 Agent Canvas 节点时，由当前 agent 负责；handoff 接手方不合并
   （验证 subagent 同样不合并），由交出方在 `accept` 完成后负责。角色或验证状态无法判定时，停止并报告，不得把责任交给
   `close-node`。
<!-- @else -->
4. 判定集成责任：由当前 agent 负责；handoff 接手方不合并（验证 subagent 同样不合并），由交出方在 `accept` 后负责。角色或验证状态无法判定时，停止并报告。
<!-- @endif -->
5. 负责集成的 agent 提交本任务改动后，检查当前分支的 `HEAD` 是否已包含于 `@{integration_branch}`：

   ```bash
   git merge-base --is-ancestor HEAD @{integration_branch}
   ```

   退出码为 0 表示已合并，跳过合并动作；退出码为 1 表示尚未合并，调用 manage-worktree「合并」；未安装带「合并」的版本时直接运行
   `@{merge_script}`；其他退出码表示 Git 状态无法判定，停止并报告。合并到
   `@{integration_branch}` 一律走这条路径，禁止手动执行 `git checkout @{integration_branch} && git merge ...`。真实冲突按
   脚本提示处理。
6. 汇报改动、验证结果、集成责任与结果、剩余风险及当前分支状态。
<!-- @if agent_canvas -->

## Step 8 收尾

### 8.1 说明

本步只做节点收尾，不判定也不执行合并（集成责任见 7.2）。agent 只完成 `describe-node` 第二次、
`relate-node` 第二次与质量观测（含送审检查）。

`close-node` 与 `external-closeout` 都由用户通过当前平台的命令入口人工触发（`external-closeout`
的执行体是外部 agent），agent 不自调，也不照着 skill 步骤手工代跑；两者只做节点生命周期（停止、
会话回到仓库根、隐藏），不合并、不送审、不清理 worktree，不是 Git 合并的前置条件。

### 8.2 标准

`close-node` 前必须已有一份用户可见的 Step 7 汇报（节点关闭后可能无法继续输出）：独立节点说明
合并结果；handoff 接手方说明已交回交出方验证，交出方说明 `accept` 与合并结果。前提不满足就先
回到 Step 7。

### 8.3 执行细则

顺序不能反：

1. `describe-node` 第二次，`--spec` 按 4.4 传。
2. `relate-node` 第二次，核对 `produces`、`references`、遗漏的 `depends-on` 与可明确指认两端的
   `hands-off-to`。
3. 质量观测与送审：先读 `get-node` 的 `availableActions`，仅当 `observe_node_quality` 可用，才执行
   `observe-node-quality <本节点 id>`，并按结果逐项汇报（描述、合并、送审）。送审由需求自己的送审
   检查判定，结果为 `not-ready` 时如实汇报卡住的节点，未合并只提醒、不代做合并；不手动
   `submit-requirement`。没有 `implements` 边时结果为 `not-applicable`，照常跳过，不为此立项。
   送审后需求停在 `in_acceptance`，不往 `done` 推。独立节点、交出方、接手方一视同仁，不依赖角色判定。
   **旧版 App 兜底**：`observe_node_quality` 不可用（App 尚未升级到带它的版本）时，沿自己的
   `implements` 边找需求节点，仅当其 `availableActions` 含 `submit_requirement`，才执行
   `submit-requirement <需求节点id> --commit <本分支 HEAD 的 40 位 sha>`；没有 `implements` 边则跳过。

### 8.4 特例

- 琐碎档或不在 Agent Canvas 节点时，不调用画布 skill。
<!-- @endif -->

# 测试清单：handoff 与 fork-topic 建节点改走路由引擎

## 需求（一句话）

在 Agent Canvas 画布节点里，handoff（author 第 6 步）建接手节点改用 `create-routed-pty-node --category develop`，fork-topic 改为用 `create-routed-pty-node --category think` 建节点并把 prompt 发过去；不在画布里时两者行为不变。

## 背景与已定决定

- 触发由 skill 负责，程序不强制；字段由发起方 agent 按 describe 指南定级（Agent Canvas 节点路由 v2.1，`agent-canvas` 仓库 `docs/superpowers/specs/2026-11-10-node-routing-category-params-design.md`）。
- 调用顺序：`list-node-route-categories` → `describe-node-route-category <类别>` → `create-routed-pty-node`。字段标准、证据要求、description 段落以 describe 输出为准，skill 不抄写。
- 用户点名节点类型（如 codex）或模型时不走路由，用 `create-pty-node`（路由不接受指定，R-99）。
- 路由命令不存在（旧版 App：「未知子命令」，退出码 1）或 `PRECONDITION_FAILED` → 退回 `create-pty-node`，并告诉用户退回原因；`INVALID_ARGUMENT` → 按报错修正后重试路由，不换成 `create-pty-node`。
- handoff 第 9 步派发消息不变，只含寻址信息；路由的 `--description` 是写给执行方与复核者的节点说明，不是派发消息。
- fork-topic 在画布里建节点后不建关系（新关系类型另立需求，上线后再补）；不加 `--expect-reply`。
- agent-canvas-control 不改；App 不改。
- 现状：已安装的 App 尚无路由命令，新版 skill 部署后在 App 升级前会走退回路径。

## 用例（输入 → 预期）

画布环境由 eval fixture 提供桩 `agent-canvas-ctl` / `agent-canvas-arrange`：把每次调用的 argv 记进日志，返回仿真的 JSON；可切换「有路由」「旧版 App」「首次 INVALID_ARGUMENT」三种模式。断言以调用日志和回复为准。

### handoff

| # | 输入 | 预期 |
|---|---|---|
| H1 | 画布里，低档任务已有测试清单，用户要交接，未点名 agent | 依次调用 `list-node-route-categories`、`describe-node-route-category develop`、`create-routed-pty-node`：`--category develop`；`--params` 恰好含 describe 列出的全部字段；`--evidence` 指向真实存在的测试清单/交接文档；`--description` 按 describe 的段名以 `## ` 分段；`--cwd` 为交接工作区；不带 `--message`。全程不调用 `create-pty-node`。之后 `put`、`link-nodes --type hands-off-to`、`send --file` 照旧，派发消息只含寻址信息 |
| H2 | 画布里，用户说「交给 codex 做」 | 用 `create-pty-node --node-type codex`，不调用任何路由命令 |
| H3 | 画布里，桩处于「旧版 App」模式（路由命令报未知子命令、退出码 1） | 退回 `create-pty-node --node-type claude-code --task-type execute`，只建一个节点；回复告诉用户路由不可用、已退回 |
| H4 | 画布里，桩对第一次 `create-routed-pty-node` 返回 `INVALID_ARGUMENT`（例如缺一个字段） | 按报错补齐后再次调用 `create-routed-pty-node`；不调用 `create-pty-node`；最终只建出一个节点 |
| H5 | 不在画布里（`whoami` 失败） | 行为与改动前一致：不调用任何建节点命令，输出可粘贴接手指令（现有 eval 0、1 作回归） |

### fork-topic

| # | 输入 | 预期 |
|---|---|---|
| F1 | 画布里，主讨论在等支线结论 | 调用 `describe-node-route-category think` 后 `create-routed-pty-node --category think`，`--params` 恰好含 describe 列出的全部字段，`--description` 按段分好，总长 ≤ 2500 字符；`put` 新节点；把 prompt 写进临时文件（仓库外）后 `send <新节点> --file`；不调用 `link-nodes`；回复说明派给了哪个节点和 messageId。prompt 本身仍满足现有约束（查不出的写全、查得出的只给线索、含交回要求） |
| F2 | 不在画布里 | 行为与改动前一致：只输出代码块里的 prompt，不建节点、不写文件（现有 eval 0–2 作回归） |
| F3 | 画布里，桩处于「旧版 App」模式 | 退回 `create-pty-node --node-type claude-code --task-type plan`，照常 `put` 与 `send`；回复说明已退回 |
| F4 | 画布里，用户说「用 opus 开个支线」 | 用 `create-pty-node --model opus`，不调用路由命令 |

## 涉及文件

- `skills/coding/handoff/SKILL.md`（author 第 6 步；版本 1.18.1 → 1.19.0）
- `skills/coding/fork-topic/SKILL.md`（新增画布内派发；版本 1.0.0 → 1.1.0；description 去掉「Text only … no dispatch」的绝对说法，改为不在画布里只出文本）
- `docs/superpowers/specs/2026-10-11-fork-topic-design.md`（「边界」一节的「不替用户派发」改为仅限不在画布里）
- `skills/coding/handoff/evals/evals.json`、`skills/coding/fork-topic/evals/evals.json`（新增 H1–H4、F1、F3、F4）
- 新增 eval fixture：画布命令桩（`skills/coding/handoff/evals/fixtures/canvas-stub/`，fork-topic 的 eval 引用同一份或各放一份）
- `skills-index.json`（两个 skill 的 contentHash / contentVersion）

## 验证方式

1. `npm test` 全绿（SKILL.md 格式、索引一致性、既有 bats）。
2. 用 `tools/skill-harness` 跑新增与回归 eval（handoff：H1–H5；fork-topic：F1–F4），逐条看断言结果。
3. 真实试跑（**待带路由命令的 App 安装后**，需用户同意画布写操作）：用新版 handoff 或 fork-topic 在真实画布上建一个节点，核对路由日志，并记录发起方组请求实际多花的 token（回答缺口 2）。

## 验收标准

### V1｜真实环境生效｜机器可查
标签：新版 handoff 在画布里建出的接手节点走了路由
正文：带路由命令的 App 进入稳定后，取用新版 handoff（≥ 1.19.0）建出、且有 `hands-off-to` 边指向的接手节点，在 `<agentCanvasHome>/node-routing/*.jsonl` 里都能找到 `nodeId` 相同、`decision.category` 为 `develop` 的 decision 记录；用户点名 agent 或模型的情形除外。

### V2｜真实环境生效｜机器可查
标签：新版 fork-topic 在画布里分出的节点走了 think 路由
正文：同一条件下，用新版 fork-topic（≥ 1.1.0）在画布里分出的节点，路由日志里有 `nodeId` 相同、`decision.category` 为 `think` 的 decision 记录，且该节点收到的首条消息就是 fork-topic 生成的 prompt。

### V3｜体验可接受｜人工裁决
标签：两个入口的落点与任务相称、组请求成本可接受
正文：用户抽查观察期内这两个入口产生的路由记录，判断落点（模型与 effort）是否与任务相称，以及发起方组一次请求多花的 token 是否可接受。由用户在界面上写结论。

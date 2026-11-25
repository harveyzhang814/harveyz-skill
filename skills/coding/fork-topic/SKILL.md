---
name: fork-topic
description: "Fork a side topic out of the current discussion into a concise prompt for another agent session. When outside a canvas node it outputs paste-ready text only; inside an Agent Canvas node it instead creates a think node and sends the prompt there. Never writes repo files, creates branches, or does acceptance. Use handoff instead when the work must come back for formal acceptance. Only on the user's request; do not suggest it unprompted. Triggers: '/fork-topic', 'fork this topic', 'split this off into a new session', 'spin off a side discussion', 'take these conclusions into a new topic'."
user_invocable: true
version: "1.2.0"
---

# fork-topic — 把支线话题分出去

把讨论中的支线（或带着本次结论开的新话题）写成一段精简的可粘贴 prompt，交给另一个 agent。

主次：目的是分出去；约束是尽可能精简；手段是查不出的写全，查得出的只给线索。

- **查不出的写全**：只在对话里的东西——目标、已定结论、否决方案及理由、用户说过的偏好与约束、未落盘的草稿。只写支线用得上的。
- **查得出的只给线索**：磁盘、仓库、接手方能访问的系统里的东西，写去哪找 + 为什么看，不抄内容、不写摘要。
- **不添加**对话里没有的结论、约束或推论。
- **交回要求**只在主讨论正等着这个结论时写。
- 不落仓库文件、不建分支、不验收。

写完后对照查漏：目标（含从哪个讨论分出）/ 已定结论 / 否决方案及理由 / 偏好与约束 / 线索 / 交回要求。只查有没有遗漏，不按它排版；对话里没有的项不补。

## 输出

先跑 `agent-canvas-ctl whoami`，看自己在不在 Agent Canvas 画布节点里。命令不存在或取不到节点 id，就是不在。

**不在画布里**：只输出文本，不替用户派发。prompt 放在一个代码块里（内容含代码块时外层用 4 个反引号），代码块外最多一句说明。

**在画布里**：不输出可粘贴的整段 prompt，而是建一个 think 节点并把 prompt 发过去。命令按下面的写法直接调用，报错时再查 `agent-canvas-ctl help <命令>`。

1. 建节点，默认走路由引擎（由它选 agent 类型与模型）：
   - `agent-canvas-ctl list-node-route-categories`，确认有 `think`。
   - `agent-canvas-ctl describe-node-route-category think`：字段定级、证据要求、节点说明的段落格式都以它的输出为准，这里不重抄。证据指向的文件必须真实存在；对话里的内容不是文件，没有可指的文件就不凑证据。
   - `agent-canvas-ctl create-routed-pty-node --category think --title "<支线一句话>" --cwd <当前工作目录>`，带上上一步得出的 `--params 字段=级别,…`、`--evidence 名称=路径,…`、`--description`（按段名以行首 `## <段名>` 分段），不指定 agent 类型与模型。**不带 `--message`**：prompt 在后面单独发。`--description` 是节点说明，不是 prompt。
2. 只有两种情形改用 `agent-canvas-ctl create-pty-node --title "<支线一句话>" --cwd <当前工作目录> --task-type plan` 建：
   - 用户点名了 agent 类型或模型（如「用 opus 开个支线」）→ 不调路由命令；`--node-type` 取点名的类型，只点名模型时取 `claude-code`；点名了模型就带 `--model <点名的模型>`。
   - 路由命令报未知子命令（旧版 App：退出码 1，stderr 以 `未知子命令:` 开头）或 `PRECONDITION_FAILED` → `--node-type claude-code`，并告诉用户路由不可用、已退回。
3. 路由报 `INVALID_ARGUMENT` 不退回：按报错修正后重试路由，最多重试两次，仍不过按第 7 条处理。报错表示没建出节点，所以全程仍只有一个新节点。
4. `agent-canvas-arrange put <新节点 id>` 放上画布（建出来默认不在画布上）。
5. 把 prompt（只写 prompt 正文，不加代码块围栏）写进 `mktemp` 建的临时文件，文件在仓库之外，不进任何 git 目录。然后按顺序：
   1. **prompt 里写了交回要求时**，先连等待边（原会话等新会话），再发送：`agent-canvas-ctl link-nodes --from <自己的节点 id> --to <新节点 id> --type waits-for`。自己的节点 id 取自开头 `whoami` 的结果。连边成功：记下返回的 `relationId`。连边失败：把报错告诉用户，照常 `send`（这次会弹审批），不删节点、不重建。没有交回要求就不连边。
   2. `agent-canvas-ctl send <新节点 id> --file <临时文件>`。没有 active 的等待或交接关系时，`send` 会在画布上弹审批卡，命令阻塞到用户作答。
   3. **`send` 未成功**（非 0 退出码都算；分类以 stderr 文本为准，错误码只作补充——命令行失败时 stderr 通常只有中文提示、不带错误码）：两类共同规则：不重试、不删节点；按「不在画布里」的格式输出代码块里的可粘贴 prompt；不走第 6 条，回复里不得声称消息已发出，也不得给出 `messageId`。
      - 明确未执行（stderr 含「请勿重试」，或含「被用户拒绝」「审批超时」「被策略规则」；stderr 含 `APPROVAL_DENIED`、`APPROVAL_TIMEOUT`、`INVALID_ARGUMENT`、`PRECONDITION_FAILED`、`NOT_APPLICABLE`、`TARGET_NOT_FOUND` 等码时也归这一类）：告诉用户「节点已建、消息未发出」，请用户把 prompt 贴进新节点。
      - 结果不明（其余非 0 退出，含 `OUTCOME_UNKNOWN`、`EXECUTION_FAILED`，以及看不出类别的报错）：如实说明「结果未知」，把报错原文告诉用户，请用户先到新节点核对是否已经收到；prompt 仍然给出，「确认没收到再贴」写在代码块外的说明里，不写进 prompt；不自动重发。
      - 已连了等待边的，一律保留不删，并补一句：等待边已保留，用户手动贴入（结果不明时先确认没收到）prompt 后照常等待，结论交回后可经用户同意，用 `agent-canvas-ctl resolve-wait` 加第 1 步记下的 relationId 具体值解除；不自动解除。
6. **仅 `send` 成功时**：回复说明派给了哪个节点、`messageId`，结束本轮，不 sleep、不轮询。交回要求照常写在 prompt 里；不会自动回传，结论由用户到那个节点里取，再贴回主讨论。若连了等待边，补一句：结论贴回主讨论后，可经用户同意，用 `agent-canvas-ctl resolve-wait` 加第 1 步记下的 relationId 具体值解除等待；不自动解除。
7. 建节点失败（含重试用尽，含退回的 `create-pty-node` 也失败）→ 把报错告诉用户，改为输出代码块里的可粘贴 prompt（同不在画布里的输出）。除上面规定的重试与退回外，不要换个参数再建一个；退出码 2 先 `agent-canvas-ctl search-nodes <标题关键词> --kind pty` 核对是不是已经建出来了（旧版 App 不认 `--kind` 时去掉它）。

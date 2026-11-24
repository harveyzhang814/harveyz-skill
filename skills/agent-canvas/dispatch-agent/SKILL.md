---
name: dispatch-agent
description: "Dispatch work to another claude-code/codex agent node on Agent Canvas and get its result back — create a new node or reuse a running one, send the task asking for a reply, receive the reply, and handle held, withdrawn, failed, or interrupted messages. Use when the user wants a task handed to another agent on the canvas, several tasks fanned out in parallel, or a quick answer from another node."
user_invocable: true
version: "1.1.0"
---

# 派活给另一个 agent（dispatch-agent）

如果画布工具（MCP server `agent_canvas`，Claude Code 里显示为 `mcp__agent_canvas__*`）和
`agent-canvas-ctl` 命令都不可用，这个 skill 不适用，直接跳过。

本 skill 只写流程：选收件节点 → 发任务并要求回复 → 取回复 → 处理异常。下文用工具名指代能力；
参数、返回值、报错和会不会弹审批，以工具自己的说明为准，这里不复述。没有画布工具、只能走命令行时，
用 `agent-canvas-ctl help <命令>` 查同一能力的 CLI 写法（命令名与工具名不完全相同，以 help 为准）。

**写操作打到的是用户正在用的真实画布。** 发出的消息会真实写进对方会话，对方会照着做：只发用户
任务需要的内容，不发测试消息；建出来的节点留在用户画布上，不为试探随手建。

## 1. 选收件节点：复用还是新建

**复用**——用户点名了某个节点，或画布上已有在跑的 claude-code / codex 节点握着相关上下文：

1. 已知 id 直接 `get_node`；只知道标题或主题时先 `search_nodes`。
2. 看 `get_node` 返回的 `actions[]` 里 `send_message` 是否 `available: true`（只有进程在跑的
   claude-code / codex 节点可以收消息）。不可用时把 `reason` 告诉用户，不要私自改发给别的节点。
3. 收件节点与你之间没有 active 的 `waits-for` 或 `hands-off-to`（不分方向），且用户没有在本会话内选「始终允许」时，发送会在画布上弹审批卡片，由用户放行。是不是你建的节点不再影响审批。

**新建**——没有合适的现成节点：

| 情形 | 用哪个工具 |
|---|---|
| 一般情况 | `create_pty_node`（节点类型选 claude-code 或 codex，工作目录给项目路径） |
| 用户要求按任务类别自动选节点类型与模型 | `create_routed_pty_node`；先 `list_node_route_categories`、`describe_node_route_category` 选类别，不确定时先 `preview_node_route` |
| 新会话是为实现画布上某个需求节点 | `derive_pty_from_requirement`（会自动连上 `implements`） |

- 新节点是你建的，给它发消息照样按上面第 3 条判定；要建等待关系，由你在发送前连 `waits-for`（本 skill 不强制）。消息会排队，等新会话启动完成才写入。
- 派生层级只数 agent 发起的创建，遇到人发起的创建（Fork、`/branch`、界面派生等）就重新计数；新节点会是第 4 代及以后时，建节点本身会弹审批。
- 新节点默认**不在画布上**，这是正常状态。用户要看它时用 `show_nodes` 放上去。
- 走 CLI 时，`create-pty-node` 可以一步完成建节点和发消息；若它报“节点已经或可能已经建出、消息
  没发成”，先用 `search_nodes` 按标题核对，确认节点存在后再单独发消息，不要再建一个。

## 2. 发任务并要求回复

用 `send_message` 发给收件节点，**要拿回结果就要求回复**——不要求时对方做完不会回传。

- **任务写成自包含的**：对方看不到你的会话。写清目标、相关路径、完成标准、要回复什么（例如
  “回复改了哪些文件和测试结果”）。
- 记下返回的 `messageId`，派给多个节点时记下每个 `messageId` 对应的任务。
- 要审批的发送会等用户在卡片上作答后才返回：放行后照常返回。返回的 `status` 是 `queued` 就正常往下走；是 `held`，或发送报错被拒（`APPROVAL_DENIED`）、审批超时（`APPROVAL_TIMEOUT`），见第 4 节。
- 消息**不会自动重发**，你也不要自行重发同一条。
- 发斜杠命令（命令型消息）时原样写入、没有回复，回执止于 `delivered`。

## 3. 取回复

**默认做法（你是 claude-code / codex 节点）：发完就结束本轮，回复会推回来。**

1. 告诉用户派给了谁、在等谁的回复，然后结束本轮。不要 sleep，不要循环 `get_message` 等状态，
   也不要为等回复把这一轮拖着。
2. 回复在你空闲时作为**新的一轮**写进来，开头是
   `[agent-canvas 回复 msg_… · 来自「X」· 回复你的 msg_…]`。信封里“回复你的 msg_…”就是你当初
   那条消息的 id，据此对上是哪个任务的结果。
3. 派给几个节点就各来一轮；全部到齐再汇总给用户。

**`wait_reply` 只在两种情况用：**

- 你在 shell 节点或画布外：回复写不进你的会话，会停放（`parked`），只能用 `wait_reply` 领取。
- 这一轮里必须当场拿到一个很快就能答完的短答复才能往下走（比如向另一个节点问一个事实）。

`wait_reply` 只能前台阻塞调用，不包 sleep、不放后台。超时说明还没等到：agent 调用方结束本轮即可，
回复之后会写进来，不要接着再等一次；shell 调用方稍后再领取。要对方做较长的工作时不要用它干等，
也不要调大超时去等长任务。

需要核对进度或排查时，用 `get_message` 看单条消息的回执轨迹（正常是
`queued → delivered → received → replied`），用 `list_messages` 看某个节点或某条消息链收发过什么。

## 4. 异常处理

| 状态 | 含义 | 怎么办 |
|---|---|---|
| 发送报错 `APPROVAL_DENIED` / `APPROVAL_TIMEOUT` | 用户在审批卡片上拒绝了，或审批超时；消息没有发出（回执记为 `denied`） | 如实告诉用户；拒绝是用户的决定，不要重试 |
| `held` | 被护栏拦下（例如同一消息链里往返次数到了上限），等用户在节点的卡片上放行或终止 | 告诉用户；agent 解不了，不要重发、不要换个说法再发一条绕过。用户放行后照常等回复 |
| `cancelled` | 消息已撤回 | 是你撤的就按新计划走；要改口可以再发一条说明 |
| `failed` | 写入后没确认收到，文字**可能已经**写进对方会话 | 先 `get_node` 或看对方节点确认，再决定要不要补发，不要直接重发 |
| `interrupted` | 对方进程退出或 App 重启，消息没投出去 | 告诉用户，由用户决定是否重发 |
| `closed-without-reply` | 没等到回复就结束了：用户接管了对方这一轮、对方这一轮被打断，或用户终止了这条消息链 | 告诉用户原因，由用户决定下一步 |

- **撤回**：发错了、或任务作废，用 `cancel_message` 撤回。只能撤回自己发的、还没写入对方会话的
  消息；已经写入的撤不回，需要时再发一条更正。
- **`wait_reply` 返回 `replied` 却没有回复内容**：表示对方的回复被 held 或已撤回，不是空回复，
  按上表 `held` 或 `cancelled` 处理。
- **发送被直接拒绝**（发送太频繁、对方待投消息太多、正文太长等）：按报错调整，例如把长任务说明写进
  文件再发，不要原样重试。

## 相关 skill

收到别人派来、要求回复的消息时，把结论写在本轮最后一条回复里即可，它会被原样发回；要给更精确的
结论，在本轮结束前用 `reply_message` 显式回复。节点生命周期里的固定动作各有 skill：命名与描述用
`describe-node`，梳理关系用 `relate-node`，需求立项用 `capture-requirement`。

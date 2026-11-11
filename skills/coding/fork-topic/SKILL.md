---
name: fork-topic
description: "Fork a side topic out of the current discussion into a concise prompt for another agent session. When outside a canvas node it outputs paste-ready text only; inside an Agent Canvas node it instead creates a think node and sends the prompt there. Never writes repo files, creates branches, or does acceptance. Use handoff instead when the work must come back for formal acceptance. Only on the user's request; do not suggest it unprompted. Triggers: '/fork-topic', 'fork this topic', 'split this off into a new session', 'spin off a side discussion', 'take these conclusions into a new topic'."
user_invocable: true
version: "1.1.0"
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

**在画布里**：不输出可粘贴的整段 prompt，而是建一个 think 节点并把 prompt 发过去。命令用法以 `agent-canvas-ctl help <命令>` 为准。

1. 建节点，默认走路由引擎，由它按任务难度选 agent 类型与模型，依次做：
   - `agent-canvas-ctl list-node-route-categories` 确认有 `think` 类别。
   - `agent-canvas-ctl describe-node-route-category think`，按它的输出给每个字段定级、备证据、按它规定的段落格式写节点说明。字段、级别口径、证据要求、说明格式都以这条命令的输出为准，这里不重抄。证据指向的文件必须真实存在；对话里的内容不是文件，没有可指的文件就不凑证据。
   - `agent-canvas-ctl create-routed-pty-node --category think --title "<支线一句话>" --cwd <当前工作目录>`，再加上上一步得出的 `--params`、`--evidence`、`--description`（具体写法以 `help create-routed-pty-node` 为准）。不自己指定 agent 类型与模型。**不带 `--message`**：prompt 在后面单独发。`--description` 是节点说明，不是 prompt。
2. 只有下面两种情形绕开路由、用 `create-pty-node` 建，其余一律走路由：
   - 用户点名了 agent 类型或模型 → 不走路由，直接 `agent-canvas-ctl create-pty-node --node-type <点名的类型> --title "<支线一句话>" --cwd <当前工作目录> --task-type plan`。只点名模型（如「用 opus 开个支线」）时，节点类型取默认的 `claude-code`，并带上 `--model <点名的模型>`。
   - 路由命令报未知子命令（旧版 App：退出码 1，stderr 以 `未知子命令:` 开头），或报 `PRECONDITION_FAILED` → 退回 `agent-canvas-ctl create-pty-node --node-type claude-code --title "<支线一句话>" --cwd <当前工作目录> --task-type plan`，并告诉用户路由不可用、已退回。
3. 路由报 `INVALID_ARGUMENT` 不退回：按报错修正字段后重试路由，最多重试两次，仍不过就把报错告诉用户，并按第 7 条输出可粘贴的 prompt，不停下。任何报错都表示这次没建出节点，所以重试或退回之后，全程仍只有一个新节点。
4. `agent-canvas-arrange put <新节点 id>` 放上画布（建出来默认不在画布上）。
5. 把 prompt（只写 prompt 正文，不加代码块围栏）写进 `mktemp` 建的临时文件，文件在仓库之外，不进任何 git 目录；然后 `agent-canvas-ctl send <新节点 id> --file <临时文件>`。
6. 回复里说明派给了哪个节点、`messageId` 是什么，结束本轮；不 sleep、不轮询，不等对方回复。交回要求照常写在 prompt 里，让对方产出一段可贴回主讨论的结论；没有自动回传，结论由用户到那个节点里取，再自己贴回主讨论。
7. 建节点失败（含重试用尽，含退回的 `create-pty-node` 也失败）→ 把报错告诉用户，改为输出代码块里的可粘贴 prompt，与不在画布里时的输出形式相同。这是建节点失败的唯一处理方式。除上面规定的重试与退回外，不要换个参数再建一个；退出码 2 先 `agent-canvas-ctl search-nodes <标题关键词> --kind pty` 核对是不是已经建出来了（旧版 App 不认 `--kind` 时去掉它）。

画布路径只多写一个仓库之外的临时文件，仍然不落仓库文件、不建分支、不验收。

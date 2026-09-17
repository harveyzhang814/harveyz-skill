---
name: agent-canvas-control
description: Control Agent Canvas node entities and layout from claude-code/codex/pi nodes — create, query, update, delete nodes, and put or hide them on the canvas; also usable from shell/hermes-tui nodes or terminals outside the canvas via `--canvas`/`resolve-canvas`/`resolve`.
user_invocable: true
version: "1.0.1"
---

# 操控节点与画布（agent-canvas-control）

如果 `agent-canvas-ctl`/`agent-canvas-arrange` 命令都不存在，这个 skill 不适用，直接跳过，
不要尝试执行下面的命令。命令存在时可以直接尝试子命令——即使没有 `AGENT_CANVAS_MCP_URL`，
两个二进制也会按当前工作目录反查所在画布；如果解析不到目标画布，子命令会以非零退出码报错，
此时同样说明当前不适用，跳过即可，不要重试。

两个二进制分工**互不重叠**：`agent-canvas-ctl` 管节点实体与关系（建/查/改/删/连接），
`agent-canvas-arrange` 管画布摆放（放上/收起/移动/分组的成员与配色）——**建的节点默认不
放上画布**，节点存在但游离于画布之外，是正常状态，不是遗漏；想让它出现在画布上，建完之后
再调一次 `agent-canvas-arrange put`。两者所有子命令成功时把结果 JSON 打印到 stdout、退出码
0；失败时把错误信息打印到 stderr、退出码非 0。

## agent-canvas-ctl：节点实体与关系

- `agent-canvas-ctl list-nodes`
  列出当前画布所有节点，返回 `[{id, title, description, kind, state}, ...]`（不含画布摆放
  字段——查节点在不在画布上、在哪个坐标，用下面 `agent-canvas-arrange list/get`）。

- `agent-canvas-ctl get-node <nodeId>`
  获取单个节点详情（同样不含摆放字段）。

- `agent-canvas-ctl search-nodes <query> [--limit <n>]`
  按标题/描述模糊搜索当前所有非归档节点（编辑距离容错，不要求精确匹配，标题命中权重高于描述），
  按相关度降序返回 `[{id, title, description, kind, state, createdAt, score}, ...]`。
  `score` 不是归一化到 0~1 的置信度（标题命中会乘 1.5 倍权重），只用于本次结果内部排序。
  `--limit` 缺省时不截断结果数量。收起的节点（`agent-canvas-arrange hide`）仍会被搜到；
  已归档节点不在范围内，要搜归档节点用 `search-archived-nodes`。

- `agent-canvas-ctl create-node --kind <markdown|html|text|browser> --title <标题> --file <文件路径或URL> [--description <描述>]`
  创建一个静态节点，**不放上画布**（不接受 `--position`）。`--file` 对 `markdown`/`html`/`text`
  指向一个文件：`markdown` 在文件不存在时会创建空文件，`html`/`text` 要求文件已存在（否则
  报错，不创建节点）；对 `browser` 传入初始 URL（不做存在性校验）。成功返回 `{nodeId}`；
  要放上画布用 `agent-canvas-arrange put <nodeId> [--position x,y]`。

- `agent-canvas-ctl create-pty-node --node-type <claude-code|shell|hermes-tui|codex> --title <标题> [--cwd <路径>] [--task-type <execute|evaluate|analyze|plan>]`
  创建并启动一个 pty 节点，使用该节点类型的默认启动命令（不支持自定义 command）；**不放上
  画布**（不接受 `--position`，进程照常启动，与是否在画布上无关）。`--cwd` 缺省时用当前
  shell 的工作目录。`claude-code` 类型总是新建会话，不支持 resume。`--task-type` 可选，
  设置节点的初始任务类型分类。不支持 `customNodeTypes`。成功返回 `{nodeId}`。

- `agent-canvas-ctl create-requirement-node --title <标题> [--description <描述>] [--priority low|medium|high] [--status open|in_progress|done] [--acceptance-criteria <验收标准>] [--links <a,b,c>]`
  创建一个需求节点，**不放上画布**。`--priority`/`--status` 缺省时分别为 `medium`/`open`。
  成功返回 `{nodeId, requirementId}`——`requirementId` 是自动生成的需求编号（`YYMMDD-XX`
  格式），和其余 `create-*` 子命令（只返回 `{nodeId}`）不同。

- `agent-canvas-ctl derive-pty-from-requirement <nodeId> [--cwd <路径>] [--node-type <claude-code|shell|hermes-tui|codex>] [--task-type <execute|evaluate|analyze|plan>]`
  从一个需求节点派生出一个 pty 会话节点并立即启动进程。需求节点**原样保留**，派生出的
  会话节点自动连一条 `implements` 关系指向它；同一条需求可以派生多个会话（分析、执行、
  评估各一个）。派生出的节点**不放上画布**。
  `--node-type` 缺省 `claude-code`，`--cwd` 缺省用当前 shell 的工作目录。
  成功返回 `{nodeId, requirementNodeId, relationId}`。

- `agent-canvas-ctl update-node-title <nodeId> <新标题>`
  修改节点标题。

- `agent-canvas-ctl update-node-description <nodeId> <新描述>`
  修改节点描述。

- `agent-canvas-ctl update-node-task-type <nodeId> <execute|evaluate|analyze|plan|none>`
  修改 pty 节点的任务类型分类，`none` 清空为未设置。仅对 pty 节点生效。

- `agent-canvas-ctl update-node-requirement <nodeId> [--status open|in_progress|verifying|done] [--deferred true|false] [--priority low|medium|high] [--acceptance-criteria <验收标准>] [--links a,b,c]`
  修改一个已存在的需求节点的 requirement 字段，patch 语义：只有显式传了的字段才写，没传的
  原样不动。`--deferred` 与 `--status` 正交，不是 status 的取值之一。仅对需求节点生效。
  成功返回 `{success: true, requirement: <patch 后的完整 requirement 对象>}`。

- `agent-canvas-ctl archive-node <nodeId>`
  归档节点（从检索空间移出+停进程，可恢复，不影响 relation）。

- `agent-canvas-ctl stop-node <nodeId>`
  停止指定 pty 节点的底层进程。不归档、不删除、不改变它在画布上的摆放。对非 pty 节点
  或进程已停止的节点是 no-op，如实回报 `stopped:false`，不报错。
  成功返回 `{success: true, stopped: boolean, reason?: string}`。

- `agent-canvas-ctl purge-node <nodeId> --yes`
  彻底删除节点（不可恢复，相关 relation 转 stale）；`--yes` 必填，否则直接拒绝执行、
  不发起任何画布请求。若在画布节点内调用，可能阻塞最长约 90 秒等待人工在该节点卡片上
  审批；被拒绝时报错 `用户拒绝了该操作`。

- `agent-canvas-ctl list-archived-nodes`
  列出当前所有已归档节点的摘要，返回 `[{id, title, description, kind, archivedAt}, ...]`。

- `agent-canvas-ctl search-archived-nodes <query>`
  按关键字搜索已归档节点（大小写不敏感，匹配 title/description 子串），返回结构同上。

- `agent-canvas-ctl restore-node <nodeId>`
  把一个已归档节点恢复回画布。

- `agent-canvas-ctl list-relations`
  列出当前画布所有关系（含 stale），返回 `[{id, type, from, to, status, label}, ...]`。

- `agent-canvas-ctl link-nodes --from <nodeId> --to <nodeId> --type <t> [--label <文字>]`
  在两节点间创建一条关系。`--type` 按两端节点 kind 的注册表校验（不合法组合报错并
  列出该端点对的合法 type；`spawns` 是系统专属，总是被拒；`unspecified` 不能显式传）。
  类型不是固定 7 个——注册表可演进，实际合法列表以 `agent-canvas-ctl relation-guide`
  当前返回的为准。成功返回 `{relationId}`。

- `agent-canvas-ctl link-nodes --from <nodeId> --to <nodeId> --reading "<自然语言谓语>" --why "<为什么现有 type 都装不下>" [--despite <t>,<t>] [--label <文字>]`
  **逃逸阀**：矩阵里这对端点确实没有一个合适的 type 时用这个，不传 `--type`。
  `--reading`/`--why` 成对必填，缺一即拒。若该端点对已有现成的合法 type，还必须传
  `--despite`，逐个点名已经看过、确认装不下的现有 type，漏一个即拒——这是留给治理循环的
  "已排除记录"，也是为了不让逃逸阀变成偷懒的默认选项。落盘后 `type` 记为 `unspecified`，
  `reading`/`why` 单独存在关系上，将来治理循环可能把它升格成正式 type（不影响你现在
  已经建的这条关系的 `relationId`）。

- `agent-canvas-ctl unlink-relation <relationId>`
  删除一条关系（relationId 由 list-relations 获取）。若在画布节点内调用，可能阻塞
  最长约 90 秒等待人工在该节点卡片上审批；被拒绝时报错 `用户拒绝了该操作`。

- `agent-canvas-ctl node-relations <nodeId> [--direction in|out|both] [--type <t>] [--depth <n>]`
  返回该节点的关系，每条带对端摘要（`id`/`title`/`kind`）。`direction` 缺省 `both`；
  `depth` 缺省 1、上限 3（超过会被夹到 3，不报错），带环检测（A→B→A 不会无限展开）。

- `agent-canvas-ctl update-relation <relationId> [--type <t>] [--label <文字>]`
  修改一条已有关系的 type/label（不支持改 status/display）。`--type`/`--label` 至少传一个；
  改 type 时同样按矩阵校验。

- `agent-canvas-ctl relation-guide [<nodeId>]`
  返回关系矩阵、判据、阶段建议，以及当前节点的上下文（既有关系/血缘链/需求节点候选/
  文档节点候选）。不传 `nodeId` 时按祖先进程链反查调用者自己所在的节点（同
  `whoami`/`summarize-self`）。「什么时候该调、该建哪些关系」见 `relate-node` skill。

- `agent-canvas-ctl create-group [--title <标题>] [--description <描述>]`
  只建分组容器实体，**不放上画布、不加成员、不配色**。成功返回 `{nodeId}`；接下来用
  `agent-canvas-arrange put` 摆上画布，再用 `group-add`/`group-color` 加成员/配色
  （加成员要求分组已经在画布上，是正当前置条件，不是限制）。

- `agent-canvas-ctl whoami`
  反查当前进程所属的画布节点，返回 `{id, title, description, kind, state}`。
  只在画布节点的进程树内可用。

- `agent-canvas-ctl summarize-self [--spec <规格文档路径>]`
  为你所在的这个节点生成标题、描述与任务类型并写回画布，不需要传 nodeId。
  `--spec` 指定据以撰写的规格文档；不传时会从本会话记录里自动发现
  （`docs/superpowers/specs/` 下你写过或读过的 .md）。
  返回 `{nodeId, title, description, taskType?, specUsed}`；
  `specUsed` 为 null 表示没找到规格文档，如有需要可用 `--spec` 补传。
  不再撰写需求——需求撰写是独立的 `draft-requirement`（下一条）。该命令要跑一次模型
  调用，通常 5–15 秒。

- `agent-canvas-ctl draft-requirement [--spec <规格文档路径>]`
  为你正在实现的某个需求节点撰写标题/描述/优先级/状态/验收标准，纯撰写不落盘。
  `--spec` 指定据以撰写的规格文档；不传时会从本会话记录里自动发现
  （`docs/superpowers/specs/` 下你写过或读过的 .md）。
  该命令只应被 `capture-requirement` skill 的三步流水线调用，不独立暴露给用户。
  节点已 implements 某个需求节点、或未读到 spec 时以非零退出码报错（需求编号不重铸）。

- `agent-canvas-ctl notify <text> [--title <标题>]`
  往通知中心发一条消息（不经过画布工具体系，不是画布操控）。落一条项目 scope 的通知，
  能反查到调用节点时通知会关联到该节点。`--title` 缺省为 "PTY"。

- `agent-canvas-ctl list-profiles`
  列出当前可见的全部 Agent Profile（含全局与项目两个 scope，project 覆盖同 id 的 global）。

- `agent-canvas-ctl create-profile --json <文件路径>`
  创建一个新的 Agent Profile。`--json` 指向一个 JSON 文件，内容需包含 `name`/`scope`
  （`project`|`global`）等字段；`id` 缺省时自动生成，传了已存在的 `id` 会报错。

- `agent-canvas-ctl update-profile --json <文件路径>`
  更新一个已存在的 Agent Profile。`--json` 指向一个 JSON 文件，内容需包含 `id`；
  `runtime`/`workingDir` 不可修改——传了不同值会报错。

- `agent-canvas-ctl resolve-canvas`
  只做目标画布解析、不连 MCP server。见下方「目标画布解析」。

## agent-canvas-arrange：画布摆放

节点建完默认不在画布上——这不是缺可见性，节点列表照常能看到它、能从那里一键放上画布；
这里是给 agent 用的等价操作。

- `agent-canvas-arrange list [--on-canvas | --off-canvas | --hidden]`
  列出全部节点的摆放态（含不在画布上的），返回
  `[{id, title, kind, onCanvas, hidden, position?, width?, height?, containerId?, color?}, ...]`。
  三个过滤参数互斥，缺省返回全集；`--on-canvas`/`--off-canvas` 按有没有落在画布上筛，
  `--hidden` 单独筛"放过又收起"的节点。

- `agent-canvas-arrange search <query> [--limit <n>]`
  与 `agent-canvas-ctl search-nodes` 同一套模糊匹配，返回摆放形状（带 `score`）。
  含收起的节点，不含已归档节点。**这是「自足」的关键**：只用这一个二进制就能从
  "标题里带某个词的节点"走到"把它摆上画布"，不需要回 `agent-canvas-ctl` 拿 id。

- `agent-canvas-arrange get <nodeId>`
  单个节点的摆放态，形状与 `list` 里的一条一致。

- `agent-canvas-arrange put <nodeId1,nodeId2,...> [--position <x,y>]`
  把节点放上画布。不带 `--position` 时用自动布局位（可以是逗号分隔的多个 id 一次放上）；
  带 `--position` 时精确定位到该坐标（只能对单个 id 生效）。已经在画布上的节点是 no-op。

- `agent-canvas-arrange hide <nodeId1,nodeId2,...>`
  将指定节点从画布隐藏：仅影响呈现层，不影响该节点参与检索、图搜索的能力，可随时通过
  `put` 恢复显示。对没有放上画布过的节点是 no-op。

- `agent-canvas-arrange move <nodeId> <x> <y>`
  把已在画布上的节点移动到指定坐标（等价于 `put <nodeId> --position <x,y>`，位置参数写法
  不同：这里 x/y 是独立参数，`put` 是 `--position x,y`）。

- `agent-canvas-arrange group-add <groupId> <nodeId1,nodeId2,...>`
  把节点加入分组。**分组必须已经在画布上**（先对 groupId 调过 `put`），否则响亮报错、
  非零退出——不是静默失败。

- `agent-canvas-arrange group-remove <groupId> <nodeId1,nodeId2,...>`
  把节点移出分组。若分组是网格布局，被移除节点在 `memberCells` 里占的格子一并清掉。

- `agent-canvas-arrange group-color <groupId> <颜色>`
  修改分组容器的配色。颜色取值：`red`/`orange`/`yellow`/`green`/`teal`/`blue`/
  `indigo`/`purple`/`pink`/`black`/`gray`/`white`。

- `agent-canvas-arrange whoami`
  与 `agent-canvas-ctl whoami` 是同一个查询，两边都有（寻址前置，不专属任何一域）。

- `agent-canvas-arrange resolve`
  与 `agent-canvas-ctl resolve-canvas` 是同一套本地解析，只是名字更短。见下方
  「目标画布解析」。

## 目标画布解析

上面所有子命令默认按以下优先级自动定位画布，通常不需要关心这一节：
`--canvas <路径>`（放在子命令之前）> 环境变量 `AGENT_CANVAS_MCP_URL`（画布内节点自带）>
当前工作目录向上匹配注册表里画布的绑定路径。

`agent-canvas-ctl resolve-canvas` / `agent-canvas-arrange resolve` 只做目标画布解析、
不连 MCP server。解析到时把 `{url, source, boundPath?, pid?}` 打印到 stdout、退出码 0；
解析不到时把可用画布清单打印到 stderr、退出码 1。适合在执行别的子命令前先探测
「现在有没有画布可连」。

## 已知限制

不支持触发节点的"功能按钮"（restart/branch/stop 等），只有增删改查与摆放。

---
name: agent-canvas-control
description: Control Agent Canvas node entities and layout from claude-code/codex/pi nodes — create, query, update, delete nodes, and put or hide them on the canvas; also usable from shell/hermes-tui nodes or terminals outside the canvas via `--canvas`/`resolve-canvas`/`resolve`.
user_invocable: true
version: "1.1.0"
---

# 操控节点与画布（agent-canvas-control）

如果 `agent-canvas-ctl`/`agent-canvas-arrange` 命令都不存在，这个 skill 不适用，直接跳过。

## 先查再调：命令与能力以二进制自己的回答为准

这个 skill **不列命令清单**。有哪些命令、各自怎么写、有哪些能力，都由两个二进制当下自己
报告——不要凭记忆或旧文档猜子命令名和参数；觉得「好像做不到」之前，先查一遍再下结论。

| 想知道 | 怎么查 |
|---|---|
| 有哪些命令、各一句话说明 | `agent-canvas-ctl help`、`agent-canvas-arrange help` |
| 某个命令的用法、参数、规则、示例、会不会弹审批 | `agent-canvas-ctl help <命令>`（或在命令后加 `--help`；arrange 同理） |
| Agent Canvas 的全部能力，以及每条能力由哪个二进制的哪个命令调用 | `agent-canvas-ctl list-actions` |
| 一条能力的参数（JSON Schema）与语义（目标、完成判据、报错、审批） | `agent-canvas-ctl describe-action <id>`，`id` 取自 `list-actions`（如 `stop_node`） |
| 某个节点**此刻**能不能调某条能力 | `agent-canvas-ctl get-node <nodeId>` 返回的 `actions[]`：`available`、不可用时的 `reason`、`bindings`（该能力在各入口上的命令名） |

`help`、`list-actions`、`describe-action` 在本地作答：不连画布、零副作用、App 没启动也能用，
随时可以调。`list-actions`/`describe-action` 回答的是「有没有、怎么调」，不回答「这个节点现在
能不能调」——后者只有 `get-node` 的 `actions[]` 说了算（它列的是以该节点为目标的动作；有些
动作取决于节点的运行状态，比如进程停了就不能再停）。

## 两个二进制的分工

- `agent-canvas-ctl` 管**节点实体与关系**：建、查、改、归档、删除节点，建/查/删关系，
  Agent Profile，通知，本节点自述。
- `agent-canvas-arrange` 管**画布摆放**：放上、收起、移动节点，分组的成员与配色。

两边互不重叠，在 arrange 上找实体或关系命令会直接报错并指回 ctl。`help`、`whoami`、
`list-actions`、`describe-action` 两边都有。

**建出来的节点默认不在画布上**——节点存在、能被查到，只是没摆上画布，这是正常状态，不是遗漏；
要它出现，建完再用 arrange 放上去（见下方示例 1）。

## 寻址：命令打到哪块画布

按以下优先级自动定位目标画布：

1. `--canvas <项目路径>`——全局选项，**必须写在子命令之前**：
   `agent-canvas-ctl --canvas <项目路径> list-nodes`。写在子命令之后会被拒，报错里会给出挪到前面
   的正确写法。
2. 环境变量 `AGENT_CANVAS_MCP_URL`——画布节点里自带，所以**在画布节点内什么都不用写**。
3. 当前工作目录向上匹配某个正在运行的画布的绑定路径。

画布外的终端，或要操作别的项目的画布时，先用 `agent-canvas-ctl resolve-canvas`（arrange 上叫
`agent-canvas-arrange resolve`）探测：它只做本地解析、不连接画布；解析到时把
`{url, source, boundPath?, pid?}` 打印到 stdout、退出码 0，解析不到时把可用画布清单打印到
stderr、退出码 1。解析不到说明当前不适用，跳过即可，不要反复重试。

## 审批：哪些调用会弹确认卡片

下面五个命令经 CLI 调用时要人工在画布上批准：`delete-node`、`purge-node`、`unlink-relation`、
`create-profile`、`update-profile`。

- 命令会先在 stderr 打印「等待画布审批」的提示，然后**最多等 90 秒**。卡片出现在调用方所在的
  节点上（画布外调用时出现在窗口上）。
- 被拒绝报 `用户拒绝了该操作`，超时报 `审批超时，操作未执行`；两种情况操作都**没有执行**、
  退出码非 0。拒绝是用户的决定，不要重试；等待期间也不要再发一遍。
- `delete-node`/`purge-node` 还必须显式带 `--yes`，没带时在本地直接拒绝，不会弹卡片。
- 名单以 help 为准：每个命令的 `help <命令>` 里「调用性质 → 审批」一行写明 CLI 面是否请求审批。

## 安全：在画布节点里跑，打到的就是真画布

画布节点的环境里带着画布的 MCP 地址（`AGENT_CANVAS_MCP_URL`）和本节点的身份 token，在这里直接
运行的每一条命令都作用在**用户正在用的真实画布、真实数据**上——没有沙箱，也没有 dry-run。

- 想弄清某个命令怎么用，读 help / `describe-action`，不要靠「试一下」。
- **不要为了探测、验证、复现随手跑写操作**（建节点、改标题、连关系、归档、停进程、放上/收起……）；
  只执行用户任务真正需要的那几条，建出来的东西就留在用户的画布上。
- 只读命令（列表、查询、搜索、`whoami`、`relation-guide`）可以放心调。
- 写测试或脚本时，子进程会继承这两个环境变量；不要让测试里的 CLI 调用带着它们跑。

## 输出与退出码

成功时结果 JSON 打印到 stdout、退出码 0；失败时错误打印到 stderr、退出码 1。批量动作（如一次
放上/收起多个 id）**部分生效时退出码 2**：有效项已经照常生效，结果仍在 stdout——读逐项结果
看清哪些成了，不要把 2 当成整条没做而重试整个列表。

## 常见工作流（完整示例）

**1. 建一个文档节点并放上画布**

```
agent-canvas-ctl create-node --kind markdown --title 设计笔记 --file docs/notes.md
agent-canvas-arrange put <nodeId>
```

第一条返回 `{nodeId}`。`put` 不带 `--position` 时用自动布局位；要精确定位写
`agent-canvas-arrange put <nodeId> --position 400,200`（只能对单个 id）。

**2. 不确定有没有某个能力：先查目录，再看这个节点此刻能不能调，再调**

```
agent-canvas-ctl list-actions
agent-canvas-ctl describe-action stop_node
agent-canvas-ctl get-node <nodeId>
agent-canvas-ctl stop-node <nodeId>
```

`get-node` 的 `actions[]` 里 `stop_node` 为 `available: false` 时，`reason` 说明为什么（比如进程
已经停了），这时不要硬调；它的 `bindings` 告诉你该用哪个命令名。

**3. 建分组并把节点放进去**

```
agent-canvas-ctl create-group --title 认证改造
agent-canvas-arrange put <groupId> --position 0,0
agent-canvas-arrange group-add <groupId> <nodeId1>,<nodeId2>
agent-canvas-arrange group-color <groupId> blue
```

分组必须先放上画布才能加成员——没放上时 `group-add` 会响亮报错，不是静默失败。

**4. 在画布外操作某个项目的画布**

```
agent-canvas-ctl resolve-canvas
agent-canvas-ctl --canvas <项目路径> list-nodes
agent-canvas-arrange --canvas <项目路径> list --off-canvas
```

`--canvas` 每条都要写、都写在子命令之前。画布外的进程不是任何画布节点，「按调用者反查自己所在
节点」的命令（如 `whoami`）在这里没有节点可反查。

## 相关 skill

节点生命周期里的固定动作有各自的 skill，不在这里重复：给本节点起名写描述用 `describe-node`，
梳理关系用 `relate-node`，需求立项用 `capture-requirement`，收尾用 `close-node`。

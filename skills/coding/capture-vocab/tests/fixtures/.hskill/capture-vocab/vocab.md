# Domain Vocabulary

## 顶栏
三栏骨架之上、贯穿整个窗口宽度的横条，画布收起时照常显示。对应 `AppToolbar`。
_Avoid_: canvas header, 画布工具栏（易与内嵌的 ToolBar 子组件混淆）
_Reference_: src/renderer/src/App.tsx（第 355 行附近，AppToolbar 在 Canvas 之外、之上）

## 工作区
右侧可拖拽调宽的滑出区域，即 PanelArea 组件本身，内部承载所有 Tab（代码内部叫 Workspace）。
_Avoid_: 抽屉, Drawer, RightPanel, SidePanel, InspectorPanel
_Reference_: src/renderer/src/components/PanelArea.tsx:55, src/renderer/src/store/projectStore.ts

## 画布区
无限画布主视图区域，承载节点与连线的可视化画布本体，对应代码中的 Canvas 组件。
_Avoid_: canvas, Canvas; 用「画布」指代整个项目
_Reference_: src/renderer/src/components/Canvas.tsx

## 工具区
左侧的工具抽屉区域，对应代码中的 LeftToolDrawer 组件。
_Avoid_: 左侧抽屉, LeftToolDrawer, LeftPanel, LeftDrawer
_Reference_: src/renderer/src/components/LeftToolDrawer.tsx

## Tab
抽屉内的分组标签，用户界面上显示为"Tab"；代码内部实现名为 Workspace（不向用户暴露该词）。每个 Tab 拥有自己独立的 dockview 实例与内容布局。
_Avoid_: Workspace（这是代码内部名，产品侧统一叫 Tab）
_Reference_: src/renderer/src/store/projectStore.ts:25（PanelWorkspace 类型）、108-109（panelWorkspaces/activePanelWorkspaceId）；src/renderer/src/components/WorkspaceTabBar.tsx:5

## 视图
工作区内某个 Tab 下承载内容的整个可视区域，对应代码中每个 Tab 各自持有的独立 dockview 实例（挂载于其 container div），内部可容纳多个 Widget（当前实现层面仍是 dockview 原生 Panel）。这是产品侧的 UI 区域概念，不是某个 React 组件名或编程通用意义上的 "View"。
_Avoid_: View（避免与通用编程概念混淆）
_Reference_: src/renderer/src/components/PanelArea.tsx（WorkspaceEntry container 结构）

## Widget (瓦片)
视图内单个内容展示单元的产品侧设想名称（非可点击 tab-header + 内容体，多个 widget 以网格并排常显）。中文名"瓦片"，取自 dashboard 类产品（如 Grafana、Power BI）里对网格排列内容块的常见叫法。当前代码中尚未落地为独立实体——现有实现仍是 dockview 原生的 Panel（可点击 tab 切换），组件为 PanelTab.tsx。
_Avoid_: 卡片（与前端 Card 组件混淆）, 面板（与代码里的 Panel 概念混淆）; (Widget 目前是 spec-only 术语，尚未在代码中对应实体)
_Reference_: docs/superpowers/specs/2026-07-17-panel-workspace-tabs-design.md（术语约定表）；src/renderer/src/components/PanelTab.tsx:59（当前仍是 dockview 原生 tab，未实现 widget 化）

## 编辑器
顶栏"编辑器 / 画布"切换开关（⌘⇧C）二选一状态之一：`canvasVisible` 为 false 时的显示模式，中栏由 PanelArea（工作区）占满全屏，Canvas 隐藏；与"画布模式"互斥显示，二者共用同一张卡片的圆角与内缩（spec §4.4 决策 A）。
_Avoid_: 编辑器模式（代码里没有对应的 isEditorMode 状态名，只是 canvasVisible 取反）、PanelArea 全屏模式
_Reference_: src/renderer/src/store/projectStore.ts:114（canvasVisible）、631-632（setCanvasVisible/toggleCanvasVisible）；src/renderer/src/components/AppToolbar.tsx:24,131,152；src/renderer/src/App.tsx:414-415

## 分支/Worktree 追踪机制
主进程直接查询 git（而非解析 PTY 里 Claude 打印的 statusLine 文本）来获取 claude-code 节点当前所在的 branch 与 worktree 名。branch 与 worktree 由同一次查询、同一个字段（gitBranchInfo）整体获取和推送，不是两套独立机制。初次 spawn 时查一次，之后每当 hook 事件命中 EnterWorktree/ExitWorktree/Bash `git worktree add|remove|prune` 时重新解析并推送更新。
_Avoid_: PTY statusLine 解析（旧机制，已改造为只保留 model/effort/ctx 解析职责，不再解析 branch/worktree 段）
_Reference_: src/main/git/gitBranchService.ts（resolveGitDirs）、src/main/ipc.ts（startGitBranchWatch/repointGitBranchWatch，NODE_SPAWN 的 claude-code 分支）、IPC.NODE_GIT_BRANCH_CHANGED、src/renderer/src/store/projectStore.ts（node.gitBranchInfo）

## Dashboard 窗口
独立于画布主窗口的单独窗口，展示所有已打开项目窗口的运行状态快照（包括各节点状态、自动睡眠开关等），对应代码中的 DashboardView 组件。
_Reference_: src/renderer/src/DashboardView.tsx, src/main/dashboard/dashboardState.ts, src/main/dashboard/dashboardPush.ts

## 席位
Canvas 留给常驻 agent 的位置：右侧独立列常驻存在的坑位，跑在宿主进程里、有窗口上下文、
知道自己是哪个项目。它只提供"这里可以坐一个常驻 agent"的可能性，本身不赋予画布操控权——
删掉画布区它随之消失，按架构北极星 §1.3 两问落在"功能表面"，不是节点。今天坐在这个席位
上的是「Pilot（主体）」，占席者原则上可换（Claude Agent SDK 第二 backend 曾实现过但未
合并，是较弱的证据）。
_Avoid_: 与「Pilot（主体）」混用——席位是坑位，Pilot 是坐在坑位上的常驻 agent 产品；两者
分开是因为 Pilot 的宿主已经移到 PilotGate，Pilot 活得比席位（Canvas）久。
_Reference_: docs/explanation/copilot-north-star.md §2；docs/superpowers/specs/2026-09-10-pilot-canvas-dual-subject-design.md §2

## Pilot（主体）
一个独立的常驻 agent 产品：自己的宿主（PilotGate）、自己的接入面（Telegram / cron / 远程
会话通道）、自己的持久化（线程/会话）。不是 Canvas 的一个功能，也不天生具有画布操控权——
默认身份没有任何画布工具；要拿到画布能力，要么坐在 Canvas 的「席位」上且当次线程选了
「`画布操控` profile」，要么走连接态门禁（供给面判连接，不判身份）。Canvas 不是 Pilot 的
宿主，是它的画布能力供给方之一。
_Avoid_: Canvas Pilot（产品名已收口为 Pilot，`Canvas` 前缀不随画布区消失，按 B2 命名判据
不该带，carve-out 仅保留完整产品名 `Agent Canvas` / `agent-canvas`）；把"Pilot"直接等同于
"席位"或"`画布操控` profile"——三者是分开的三层，见
docs/superpowers/specs/2026-09-10-pilot-canvas-dual-subject-design.md §2
_Reference_: src/main/pilot/、src/pilotGate/、docs/explanation/copilot-north-star.md §1.1-1.2

## `画布操控` profile
Pilot 线程创建时可选的一个具名「Agent Profile」：选了它，这条线程的 systemPrompt 换成
`CANVAS_OPERATOR_SYSTEM_PROMPT`，画布工具随之出现在工具表里。默认身份（不选它）没有任何
画布操控工具，只能对话。它是"这次坐席位要不要开画布操控权"的开关，本身不是主体也不是席位。
_Avoid_: 把它当成默认能力——2026-08-13 起画布操控已从默认身份退成这个 opt-in profile。
_Reference_: src/main/pilot/pilotConfig.ts（`CANVAS_OPERATOR_SYSTEM_PROMPT`）、
docs/superpowers/specs/2026-08-13-pilot-minimal-default-identity-design.md

## 线程（Thread）
Pilot 面板 tab 栏里的对话单位，最终落地为 `PilotThreadController` 内一条独立的 `PilotBridge`——一个独立的 pi 会话进程，有自己的转录文件（`sessionPath`）、独立忙碌状态（`busyByThreadId`），可与同一 scope 下其他线程并发（上限 5 条同时活跃）。与 pi SDK 的 "session" 是同一个东西的两种叫法（前者是 Agent Canvas 领域词，后者是 pi SDK 自己的词），一一对应，不是两层概念。
_Avoid_: session（指 pi SDK session 时可与"线程"互换；但不要用来指 claude-code/hermes-tui 节点自己的 claudeSessionId/hermesSessionId——那是终端会话 ID，跟 Pilot 线程模型无关的另一个概念）
_Reference_: src/main/pilot/pilotThreadController.ts（activeBridges/busyByThreadId/PilotBridge）

## Scope（作用域）
线程的身份与归属标识，不直接装线程——而是通过 `scopeKey` 映射到唯一一个 `PilotThreadController` 实例，由该 controller 实际持有并管理多条线程（同一 scope 下的所有线程共用同一份磁盘目录、同一个 cwd）。Scope 决定线程存于哪个 `sessionDir`、生命周期（随窗口关闭 dispose，还是 app 生命周期常驻）、是否被多个画布窗口共享可见。分 project scope（项目）与 global scope（全局，又分 private 私有 / shared 共享）两种。
_Avoid_: 无特别需要避免的旧叫法；注意不要和"线程"混用——scope 是线程的容器/身份，本身不是线程
_Reference_: src/main/pilot/pilotScope.ts（PilotScope/scopeKey/resolveScope）、src/main/pilot/pilotScopeRegistry.ts（PilotScopeRegistry.acquire 按 scopeKey 缓存 controller）

## Agent Profile
Pilot 线程可在创建时绑定的具名预设，定义该线程用哪个"身份"运行：systemPrompt（替换基座身份，不是追加）、tools、skills、model、thinkingLevel。全局 + 项目两层存储，project 按 id 覆盖 global；与线程是引用关系（线程只存 agentProfileId，运行时实时查表），不是创建时的快照；线程绑定后不能中途换 profile，只能新建线程选别的。这是"多 agent"能力的第一阶段——多个具名身份，但底层执行引擎仍是同一个 pi SDK，不是不同 agent backend，也不是同会话内多 agent 协作（这两条是明确排除的二期）。
_Avoid_: Agent Backend（不同概念，指二期才会做的可插拔非 pi-SDK 执行引擎）; 裸用"多 agent"指代本概念（容易被误解成同会话多 agent 协作）
_Reference_: src/shared/pilot.ts（AgentProfile 类型）, src/main/pilot/pilotProfileStore.ts, src/main/pilot/pilotAgentProfile.ts（applyAgentProfile）, docs/superpowers/specs/2026-08-13-pilot-agent-profile-design.md

## 节点
外部资源在 Agent Canvas 里的句柄，加上我们自己附加的元数据与关系。引用是它的本质而非属性
（定义见架构北极星 §1）。节点独立于任何展示模块存在——画布区、活跃节点列表、全部节点列表、
Dashboard 窗口各渲染它的一个投影，删掉其中任何一个，节点数据完好。
_Avoid_: 「画布上的节点」（把节点绑死在一个展示模块上；只有在确实要强调「有视图记录」时才可用
「已放上画布的节点」）; 卡片（那是画布区里节点的一种画法，对应 NodeCard 组件）
_Reference_: docs/explanation/architecture-north-star.md §1；src/shared/types.ts（NodeEntity）

## 项目
一个 cwd 及其全部状态：一份 projectHash(cwd) 前缀、四份落盘文件（实体 / 节点视图 / 外壳 UI /
通知历史）、一个主窗口。这是 Agent Canvas 里数据归属与窗口生命周期的基本单位。
_Avoid_: 「一个画布」「打开一个画布」「这张画布」（沿用旧义会让「画布」同时指整个项目与中栏
那块展示区，而画布区默认隐藏——用一个多数时候不可见的东西命名整个单位，讲不通）
_Reference_: src/main/canvas/projectFiles.ts（projectHash）；src/renderer/src/store/projectStore.ts

## 活跃节点列表
左侧工具区（LeftToolDrawer）内一个 tab（NodeListPanel）展示的节点子集——用 isInWorkingSet() 过滤：pty 类节点看进程是否存活、browser/内容类节点看面板是否已打开、requirement 节点看状态是否未完成。是画布全部节点的动态窄集，服务日常在用节点间的切换。
_Avoid_: 进程列表（并非只按 PTY 进程过滤，requirement/browser 等无进程节点也可能在内）
_Reference_: src/renderer/src/components/ActiveNodeListPanel.tsx, src/renderer/src/components/LeftToolDrawer.tsx, src/renderer/src/components/ToolPanelButtons.tsx:7, src/renderer/src/utils/workingSet.ts

## 全部节点列表
顶部工具栏"节点"按钮（title="节点检索"）弹出的 HiddenNodesModal 弹窗，展示画布上全部未归档节点（不做在用过滤），支持搜索/类型筛选/日期范围/排序，用于查找和找回当前不在用、面板未打开、甚至已隐藏的节点。归档节点不在此列表内（归档节点在"归档管理"单独入口）。代码注释中引用 spec §3.2 时称其为"找回面"。
_Avoid_: 活跃节点（旧文案曾写"{N} 个活跃节点"，与左侧"活跃节点列表"窄集撞词，已改为"{N} 个节点"）；进程（该列表按"是否归档"过滤，不按进程存活过滤）
_Reference_: src/renderer/src/components/AppToolbar.tsx:136, src/renderer/src/components/AllNodesModal.tsx:273

## Pilot 权限系统
Pilot 调用工具前的审批与记忆机制，实现为仓内定义、宿主固定注入的内置 pi extension（用户装不上也卸不掉，不进 profile 的 `extensions` 列表）。判定顺序：先查规则表（优先级 `deny > ask > allow`），未命中才落到默认基线（11 个破坏性工具一律询问 + `allowedDirectories` 路径守卫）。审批卡片三个按钮——允许一次 / 长期允许 / 拒绝；点「长期允许」时由可替换的推导器（`PatternDeriver`，v1 是 `literal-v1`）算出规则 pattern 并持久化进全局单文件 `~/.agent-canvas/pilot/permissions.json`。它提供的是软约束、摩擦与可审计性，不是安全边界——Pilot 是无沙箱本地进程，bash 字面匹配挡不住蓄意绕过。
_Avoid_: 沙箱 / 安全边界（本机制明确不承担这个职责）; allowedDirectories（那是 Agent Profile 级的路径白名单，越界批准写回 profile 而非 permissions.json，两者不是同一张表）; 永久拒绝（没有这个按钮，deny/ask 规则只能在设置面板手写）
_Reference_: src/main/pilot/permission/（rules.ts 匹配 / derive.ts 推导器 / defaults.ts 基线 / index.ts 组装）, src/main/pilot/permissionStore.ts, src/shared/pilot.ts（PilotPermissionRule）, docs/superpowers/specs/2026-08-19-pilot-permission-extension-design.md

## 主进程（main）
Electron 应用里唯一常驻的后台进程，持有系统权限——起 agent CLI 子进程（node-pty）、
读写画布数据、管理窗口，是所有跨进程通信最终落地执行的地方。
_Reference_: src/main/index.ts, src/main/ipc.ts

## 渲染进程（renderer）
每个窗口一份，只负责渲染画布（React Flow）、面板、终端展示（xterm.js）等 UI；不持有
Node.js/系统权限，只能通过 preload 暴露的白名单接口向 main 发请求。
_Reference_: src/renderer/src

## IPC
main 与 renderer 之间唯一合法的通信通道：renderer 发请求，main 处理后返回结果或推事件
回来。跨进程操作的等待与失败窗口都发生在这里。
_Reference_: src/shared/ipc.ts, src/main/ipc.ts

## store
特指 renderer 侧的 Zustand 状态（如 projectStore），管理 UI 展示用的状态，不是权威数据
源——是 main 侧真实状态经 IPC 同步过来的快照/缓存。
_Avoid_: 与 main 侧一批同名后缀的持久化类（CronStore、PermissionStore、ThemeStore 等）
混用——那些是 main 里的磁盘存储封装，和这里说的 renderer 展示状态不是同一概念，只是恰好
都叫 Store。
_Reference_: src/renderer/src/store

## preload
main 与 renderer 之间的桥接脚本，运行在权限受限的中间环境；把 main 的能力收窄成一组白名单
接口注入 window，是 renderer 调用 main 能力的唯一入口。它本身不含业务逻辑，只做"暴露哪些
接口"这一件事。
_Reference_: src/preload

## utilityProcess
main 主动 fork 出的独立子进程，用于隔离重、可能长时间运行、可能因第三方代码崩溃的逻辑
（Pilot 对话 pi SDK、summarizer），与 main 之间用 postMessage 通信，renderer 够不着，
须经 main 转发。cron 的调度逻辑本身跑在 main 进程里，实际执行 job 时复用 Pilot 的
utilityProcess，并不自己独立开一个。
_Reference_: src/main/pilot/createPilotBridge.ts:115, src/main/summarizer/createSummarizer.ts:38,
src/main/cron/cronRunner.ts, src/main/cron/cronStoreForHost.ts

## 远程会话通道
Canvas 对外的一张独立供给面：app 级 loopback HTTP listener（端口每次启动都变，写在
`~/.agent-canvas/remote-channel.json`）+ 独立凭据（`remote-token`，与画布的 `mcp-token`
是两枚、互不通用）+ 两个工具（`remote_message` / `remote_approval_reply`，不进
`CANVAS_OPERATIONS`）+ 出站投递（2026-09-08 起由 spawn 一次性命令
改为 HTTP 打给常驻的 PilotGate）。它把一句话送进一条长活的全局 Pilot 线程，再把里程碑与
最终回答推回去。刻意不认识任何具体平台——只认一个不透明的 `conversationId`（语义是
"网关那侧的会话标识"，换新上下文就该换新值）。绑定的 agent profile 只能是
`runtime: 'global'`。
_Avoid_: 外部渠道; Hermes 通道（把通道跟某一个网关绑死，与主线判据相反）; PilotGate（那是**服务**这条通道的网关，不是通道本身）; 远程 MCP; 远程接口
_Reference_: src/main/pilot/gate/（2026-09-08 由 src/main/remote/ 迁入 M6.10）, docs/superpowers/specs/2026-09-07-pilot-gate-telegram-design.md, docs/superpowers/specs/2026-09-02-remote-conversation-channel-design.md

## 中转
**已退役（2026-09-08）**，被 PilotGate 取代。历史文档里大量出现，故保留词条做重定向，不删。

原义：把平台消息搬进远程会话通道、再把结果搬回平台的**外部**组件。唯一实现是本机 Hermes 的
`pre_gateway_dispatch` 插件 + `hermes send` 出站命令，住在 `integrations/hermes/`（已删除）。

它连同「`src/` 里不含任何中转特定概念」那条判据一起被推翻：网关不再是外部组件，而是 Pilot
agent 自己的子系统 `src/pilotGate/`；边界从「仓库内 / 外」移到「核心 / 网关」（新判据 J1–J3）。
**旧条目的 Avoid 方向与现状相反，勿照用。**
_Avoid_: 用它指代 PilotGate; 用它论证「平台适配必须在仓库外」
_Reference_: docs/superpowers/specs/2026-09-07-pilot-gate-telegram-design.md（§0 定位、§1 判据）

## PilotGate
Pilot agent 自己的消息平台网关子系统，让 Pilot 长在 Telegram 这类平台上。独立进程，
活得比 Canvas 久（launchd 常驻），入站长轮询、出站 HTTP。类比：PilotGate 之于 Pilot agent
＝ Hermes 的 `gateway/` 之于 Hermes 的 `agent/`——**Canvas 不是这个类比里的一方**，
它是 Pilot 的画布能力供给方（见「Pilot（主体）」词条），不是宿主：Pilot 进程层面的
宿主是 PilotGate，Canvas 只在 Pilot 连着它时供给画布工具。
_Avoid_: 中转（已退役，方向相反）; CanvasGateway（它不随画布区消失，前缀该是 Pilot）; 远程通道（那是它服务的能力，不是它本身）
_Reference_: src/pilotGate/, src/main/pilot/gate/, docs/superpowers/specs/2026-09-07-pilot-gate-telegram-design.md

## Skill 注入源
Agent Canvas 内置 skill（agent-canvas-control/describe-node/close-node/capture-requirement/
relate-node/relation-review）不是人手写在磁盘上的 SKILL.md，而是 `materializeSkill.ts` 里
硬编码的模板字符串（`XXX_SKILL_SOURCE` 常量），经 `materializeXxxSkill()` 在每次 app 启动时
写入 `~/.claude/skills/<name>/SKILL.md`（部分还同时写入 Pilot 扩展目录）。写入前会 diff 内容，
相同则跳过——这意味着**直接手改磁盘上那份 SKILL.md 是脆弱的**：下次 app 启动，物化函数会
发现它和源码模板不一致，原样覆写回去，手改的内容悄悄消失；真正要改，必须连源码模板一起改。
_Avoid_: 用「装的 skill」「用户装的 skill」指代它——那类走的是 marketplace/plugin 安装路径，
物化 skill 不需要用户安装,且用户无法卸载它（重启即恢复）；提示注入（prompt injection，安全
领域的另一个概念，与此无关）
_Reference_: src/main/cli/materializeSkill.ts（各 XXX_SKILL_SOURCE 常量 + materializeXxxSkill
函数）、src/main/index.ts:258-263（app 启动时的调用点）

## 动作（action）
agent 能在一个节点上执行的一条操作，声明在能力主表 CANVAS_OPERATIONS 上，同一条动作在
Pilot / MCP / CLI 三个供给面各有一个名字。每条动作声明自己适用哪些 kind、以及可选的运行期
前置条件（如"进程还活着"）；目标不适用时报错并回传原因，不静默成功。动作**不是一等本体**
——没有 id、不落盘、没有运行期注册表，判据是"能在运行期长出新种类的东西才配有注册表"，
而一个新动作就是一段新代码。它与节点、关系平级的只有可内省性：节点能列、关系能查矩阵、
动作能查可用性。
_Avoid_: 工具（tool 是动作在 MCP/Pilot 供给面上的那张脸；讲适用性时混用，会把"参数级不适用"
和"上下文级工具被剥离"说成同一件事）; 动作注册表 / 动作类型（关系类型有注册表与升格流程，
动作明确不做）
_Reference_: src/shared/nodeActionAvailability.ts（适用性唯一声明处）；src/pilot/core/canvasTools.ts
（CANVAS_OPERATIONS 主表）；docs/explanation/architecture-north-star.md §5；
docs/explanation/capability-supply-surface.md J-E

## 关系（relation）
两个实体之间一条有类型、有方向、有来源的断言，与节点平级的一等本体：有 id、落盘、有
status（active / stale）——端点节点消失时转 stale，不剪枝只失效。画布上的连线只是它的可选
投影，关系可以永远不画出来但始终可查；不存在"纯视觉、无关系"的边。端点类型是 EntityRef
（声明了 node/file/session/requirement 四种，实际只构造过 node）。**关系类型本身是可演进的**：
RELATION_MATRIX 只是首次启动的种子，运行期权威是 ~/.agent-canvas/relation-types.json（全局）
与 <hash>.relation-types.json（项目级）两层注册表，配一套治理循环——矩阵外的主张走逃逸阀
（必填 reading + why）进待议区，聚类后经 promoteType 升格成正式 type。agent 建关系前用
relation-guide 查当前矩阵与上下文。
_Avoid_: 边 / edge（边是关系在画布区的画法；关系不因为没画线就不存在，"删掉这条边"多半
是想说"删掉这条关系"）; 把 RELATION_MATRIX 当权威校验依据（它自 spec §6.1 起只是种子）
_Reference_: src/shared/types.ts:110（Relation / EntityRef）；src/shared/relationMatrix.ts（种子表）；
src/main/canvas/RelationTypeStore.ts（两层注册表 + promoteType）；
docs/explanation/edge-relation-architecture.md；docs/explanation/architecture-north-star.md §10.4

## 测试专用-降级示例
人工构造条目，仅用于验证 lookup 命中数超过 3 条时的降级输出路径，不对应真实业务概念。
_Avoid_: 节点关系

## 测试专用-散文别名
人工构造条目，仅用于验证 Avoid 中长度不小于 20 字的散文片段不会被当成别名参与匹配。
_Avoid_: 关系改, 这是一段刻意写得很长用来验证别名清洗阈值确实生效而不会被当成短别名参与子串匹配的散文说明文字

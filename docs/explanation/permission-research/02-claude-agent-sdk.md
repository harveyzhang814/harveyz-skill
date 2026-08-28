# Claude Agent SDK 权限机制报告

## 元信息

- 分析对象：Claude Agent SDK
  - TypeScript：`@anthropic-ai/claude-agent-sdk`，实测版本 `0.3.236`（本次通过 `npm pack` 拉取）
  - Python：`claude-agent-sdk`，PyPI 当前最新版本 `0.2.141`（未拉取源码，仅核对版本号）
- 路线：黑盒 —— 官方文档 + 包类型定义（`.d.ts` 实读，无实现源码）
- 依据来源清单：
  - `https://code.claude.com/docs/en/agent-sdk/permissions`（权限评估六步流程、SDK 支持的权限模式）
  - `https://code.claude.com/docs/en/agent-sdk/user-input`（`canUseTool` 完整用法：批准/拒绝/改写/记住/建议/重定向）
  - `https://code.claude.com/docs/en/agent-sdk/hooks`（Hook 事件表、`hookSpecificOutput`、matcher、超时策略）
  - `https://code.claude.com/docs/en/agent-sdk/overview`（SDK 与 CLI / Client SDK / Managed Agents 的定位对比）
  - `https://code.claude.com/docs/en/permission-modes`（critical paths、protected paths、auto 模式分类器、`bypassPermissions` 的残余护栏 —— 该页面被 SDK permissions 页直接引用作为共享定义）
  - `https://code.claude.com/docs/en/permissions`（权限规则字符串语法、settings.json 层级与优先级、managed settings）
  - `https://code.claude.com/docs/en/sandboxing`（Bash 沙箱机制；未在正文中找到对 Agent SDK 的显式提及）
  - 类型定义实读：`package/sdk.d.ts`（8158 行）与 `package/sdk-tools.d.ts`，来自 `npm pack @anthropic-ai/claude-agent-sdk@0.3.236`，解包于 `/private/tmp/claude-501/.../scratchpad/sdk-pack/package/`
- 分析日期：2026-08-19

---

## 定位

Claude Agent SDK 是一个供宿主程序（TypeScript / Python 进程）内嵌的库，把 Claude Code 的 agent loop（模型调用、工具执行、上下文管理）暴露为可编程接口。官方文档明确用一张表把它和三个邻近产品区分开：

| 场景 | 对应产品 |
|---|---|
| 不想自己实现 tool loop，要在自己进程里跑 agent | **Agent SDK**（本报告对象） |
| 终端交互式一次性任务 | Claude Code CLI |
| 直接调 Anthropic API、自己实现 tool loop | Client SDK |
| 不想管沙箱/会话基础设施的长时任务 | Managed Agents（Anthropic 托管） |

`[读到]` `https://code.claude.com/docs/en/agent-sdk/overview`

与 CLI 的关键差异不是功能（工具、hooks、subagents、MCP、权限、session 全部复用同一套实现），而是**审批权的归属**：CLI 在终端里自己弹窗自己接受用户输入；Agent SDK 把"谁来批准"这一步整体让渡给宿主进程，通过一个回调（`canUseTool`）和一组静态规则来完成。

---

## 架构

从类型定义和注释可以还原出的进程拓扑：

- 宿主进程内嵌 SDK 库（`sdk.mjs` / TS 编译产物）。
- SDK 库在调用 `query()` 时，会拉起（或连接到）一个实际执行 agent loop 的子进程/子服务，代码注释中称之为 **"the bridge"**（例如 `sdk.d.ts:229-233` 对 `title` 字段的注释："Full permission prompt sentence rendered by the bridge"）。包内单独存在一个 15KB 的 `bridge.d.ts`，佐证这是一个独立的通信层，而不是宿主进程里的一段本地函数调用。`[读到]` `package/sdk.d.ts:229-233`
- 宿主与这个执行层之间用一套 **control_request / control_response** 协议通信，带 `request_id`，且文档承认响应可以"out-of-band"送达（例如"a signed HTTP POST echoing `requestId`"）。这意味着回答 `canUseTool` 的宿主逻辑不必与发起查询的进程是同一个——可以是一个远端审批服务。`[读到]` `package/sdk.d.ts:203-207`（`CanUseTool` 类型上的说明）
- 由此**推断**：Agent SDK 的权限体系设计前提是"审批方可以是异步、可能跨进程/跨网络的独立主体"，而不是一个同步内联的 if 判断。`[推断]`——推导链：out-of-band 响应 + `request_id` 去重字段 + "Fail-closed: an accidental null means...blocked indefinitely" 的告警一起出现，只有在审批可能来自另一个进程/服务时，这类幂等性与超时提示才有意义。

代价：这个架构把"谁来批准"变成了一个必须自己搭建可靠通信链路的工程问题——SDK 不提供审批请求的超时、重试、持久化队列，宿主必须自己保证 `canUseTool` 回调最终会被解决（见八切面第 8 条）。

---

## 宿主与 SDK 的职责分界

| 事项 | 谁做 | 证据 |
|---|---|---|
| 决定"这次调用属于哪条规则/哪个模式" | SDK（子进程内的评估引擎） | 六步评估流程由 SDK 执行，宿主看不到中间过程 `[读到]` permissions 页 |
| 静态规则文件的读取与合并（`~/.claude/settings.json`、项目 `.claude/settings.json`、`.claude/settings.local.json`、managed settings） | SDK，当 `settingSources` 包含对应层时 | `[读到]` `package/sdk.d.ts:2011`（`Options.settingSources?: SettingSource[]`）+ permissions 页 |
| 把"记住这个决定"写回磁盘（`.claude/settings.local.json` 等） | **SDK**，宿主只需要在 `canUseTool` 返回里带上 `updatedPermissions` 并选一个 `destination` | `[读到]` user-input 页："A suggestion with the `localSettings` destination writes the rule to `.claude/settings.local.json`" |
| 渲染审批 UI、收集用户输入 | 宿主，SDK 完全不管 UI | `[读到]` overview 页把"渲染"排除在 SDK 能力表之外；`canUseTool` 是纯函数回调 |
| 生成"这次调用可以泛化成的规则"（rule 的 pattern 字符串） | SDK，通过 `options.suggestions` 提供现成的 `PermissionUpdate[]`；宿主可以照抄，也可以自己造 `PermissionRuleValue` | `[读到]` `package/sdk.d.ts:212-220` |
| 给出人类可读描述 | SDK 提供 `title`/`displayName`/`description` 三个可选字段，宿主决定怎么呈现 | `[读到]` `package/sdk.d.ts:229-243` |
| 一次性/会话级/永久级授权的最终裁决 | 宿主（在 `canUseTool` 里选，或调用 `applyFlagSettings`/`setPermissionMode`） | `[读到]` `package/sdk.d.ts:2405` 起的 `Query` 接口方法 |
| 审计"当前到底授权了什么" | 双方都不完整：SDK 提供 `resolveSettings()`（标记 `@alpha`）读取磁盘上的规则合并结果；会话内动态授予的规则（`destination: 'session'`）不落盘，SDK 也不提供查询 API | `[读到]` `package/sdk.d.ts:2705-2759` |

分界处传递的东西：`canUseTool(toolName: string, input: Record<string, unknown>, options)` —— 工具名是原始字符串，参数是**未经裁剪的完整输入对象**，`options` 里还带 `suggestions`（SDK 预先算好的泛化规则候选）、`blockedPath`、`decisionReason`、`title`/`displayName`/`description`（人类可读文案）、`matchedAskRule`（如果是因为命中了一条 `ask` 规则才落到回调，会带上是哪条规则、哪个来源）。`[读到]` `package/sdk.d.ts:209-268`

---

## 八切面

### 1 拦截点

权限评估在**模型请求某个工具调用之后、工具真正执行之前**发生，由 SDK 一侧的执行子进程完成，宿主进程不参与中间步骤，只在最后一步（如果走到）被回调。官方文档给出固定的六步顺序：

```
工具调用请求
  v
[1] Hooks (PreToolUse)  -- 可直接拒绝，但 allow 不能跳过后面的 deny/ask
  v
[2] Deny rules          -- 命中即拒绝，bypassPermissions 也拦不住
  v
[3] Ask rules           -- 命中即落到 canUseTool，bypassPermissions 也拦不住
  v
[4] Permission mode     -- bypassPermissions/acceptEdits/dontAsk 等在此生效
  v
[5] Allow rules         -- 命中即放行
  v
[6] canUseTool callback -- 前面都没决出结果，才问宿主；dontAsk 模式下跳过，直接拒绝
```

`[读到]` `https://code.claude.com/docs/en/agent-sdk/permissions#how-permissions-are-evaluated`

拦的对象是**工具名 + 结构化参数**，不是工具名 + 拼好的自然语言。到达 hooks 和 `canUseTool` 的都是完整的 `tool_input` / `input: Record<string, unknown>`；到达静态规则（`allow`/`deny`/`ask` 数组）的是一条经过 SDK/CLI 归一化的字符串（`Tool` 或 `Tool(specifier)`）。`[读到]` `package/sdk.d.ts:209`；`https://code.claude.com/docs/en/permissions#permission-rule-syntax`

谁不信任谁：架构假设是"模型的工具调用请求不能被直接执行"，SDK 侧的执行子进程是强制的中间人；对于中间人自己无法用静态规则/hooks 决出结果的部分，SDK 进一步不信任自己（不做默认放行），把决定权交给宿主进程。

代价：六步里前五步（hooks、deny、ask、mode、allow）全部发生在宿主看不见的地方。如果宿主只实现了 `canUseTool` 而没意识到 `allowedTools`/`acceptEdits`/`bypassPermissions` 会在到达回调之前就把调用批准掉，宿主以为自己在"审批每一次工具调用"，实际上只审批了漏网的那一部分——文档专门为此设计了一个运行时警告（`CLAUDE_SDK_CAN_USE_TOOL_SHADOWED`）提醒这种误配置。`[读到]` permissions 页

### 2 决策单元

默认粒度是**这一次具体调用**：`canUseTool` 返回 `{behavior:'allow', updatedInput}` 且不带 `updatedPermissions` 时，只批准这一次（哪怕参数完全相同的下一次调用还会再触发回调）。`[读到]` `package/sdk.d.ts:2215-2227`（`PermissionResult` 定义）

宿主可以**升级**粒度（这次批准 -> 这一类批准），但升级的"类"由谁定义分两种情况：

- 直接采用 SDK 算好的建议：`options.suggestions: PermissionUpdate[]`，这是 SDK/CLI 自己对本次调用做归纳后给出的候选规则（例如把一条具体 Bash 命令归纳成一个命令前缀模式）。宿主只需要从中挑一个回填到 `updatedPermissions`。`[读到]` `package/sdk.d.ts:212-220`
- 宿主自己手写规则：`PermissionRuleValue = { toolName: string; ruleContent?: string }`，`ruleContent` 留空即"整个工具"级别，填字符串则要遵守该工具自己的 specifier 语法（Bash 是 glob，Read/Edit 是 gitignore 风格路径，WebFetch 是 `domain:` 前缀，MCP 是 `mcp__server__tool`）。`[读到]` `package/sdk.d.ts:2229-2232`；`https://code.claude.com/docs/en/permissions#permission-rule-syntax`

宿主没有**降级**的手段——没有"只批准这次调用的一部分参数"这种子调用级别的授权原语，`updatedInput` 只能整体替换这次调用的参数，不能表达"部分批准"。

代价：粒度的选择权名义上在宿主手里，但"怎么把一次具体调用归纳成一个安全的通用规则"这件事的默认实现（`suggestions`）是 SDK 黑盒算出来的，宿主如果偷懒直接照抄，就要为 SDK 归纳算法的宽严程度负责；如果宿主想要比 SDK 建议更细的粒度，必须自己读懂并正确构造每个工具专属的字符串语法（例如 Bash 的通配符边界规则、Read/Edit 的四种路径锚点），出错的直接后果是规则匹配到超出预期的范围。

### 3 生命周期

批准的存活时间完全由宿主在 `PermissionUpdate.destination` 里的选择决定，SDK 定义了五种目的地：

```
type PermissionUpdateDestination =
  'userSettings' | 'projectSettings' | 'localSettings' | 'session' | 'cliArg'
```

`[读到]` `package/sdk.d.ts:2263`

- `session`：只活在当前这次 `query()` 对应的执行子进程内存里，不写盘。进程退出（哪怕之后用 `resume` 恢复同一个会话）就消失，需要重新走一遍 `canUseTool`。`[读到]`（字段本身）+ `[推断]`（"进程重启后失效"是由"不落盘 + query 结束即销毁子进程"两点推出，文档未直接写"resume 后失效"这一句）
- `userSettings` / `projectSettings` / `localSettings`：**SDK 自己**把规则写进对应的 `settings.json` / `settings.local.json` 文件（宿主不需要自己去操作文件系统），下次任何会话只要 `settingSources` 包含该层，就会在启动时把这条规则重新读回来，从而跨进程重启存活。`[读到]` user-input 页原文："A suggestion with the `localSettings` destination writes the rule to `.claude/settings.local.json` so future sessions skip the prompt for matching calls."
- `cliArg`：类型上存在，但语义更接近"这条规则来自 `--allowedTools`/`allowedTools` 选项"的**只读标记**，而非宿主可以主动选择的持久化目的地。`[推断]`——文档正文未展开这个值的写入语义，只在类型里出现。

另有一条不经过 `canUseTool` 的整会话级"记住"路径：`Query.setPermissionMode(mode)` 把整个会话切到某个模式（例如切到 `acceptEdits`），持续到会话结束或再次调用；以及 `Query.applyFlagSettings({ permissions: {...} })`，把一组权限规则合并进一个介于 managed 和 user/project/local 之间的"flag settings"层，**只在本次进程运行期间生效，不落盘**。`[读到]` `package/sdk.d.ts:2405, 2461-2483`

谁负责记住：写盘由 SDK 代劳，但"要不要记、记多久、记给谁看"的决定权和触发时机在宿主。

代价：`session` 目的地没有暴露任何"提前失效/撤销"的 API（见第 6 条），一旦宿主给了 `session` 级别的宽松规则，唯一能收回的办法是结束这次 `query()`；如果宿主的进程是长时间运行的（比如常驻服务反复调 `query()` 而不重启），`session` 授权的"活多久"实际上等于"这个宿主进程觉得该不该重启底层 query"，边界很模糊。

### 4 持久化与作用域

SDK 会写盘，写到标准 Claude Code 配置文件体系里，作用域由文件路径决定，而不是由 SDK 单独设计一套存储：

- 用户级：`~/.claude/settings.json`
- 项目级：`<project>/.claude/settings.json`
- 本地/个人级：`<project>/.claude/settings.local.json`（惯例上不进 git）
- 组织级（只读，SDK/CLI 都不能覆盖）：managed settings，可通过 `Options.managedSettings` 由宿主注入一层，或来自 MDM/服务端下发

`[读到]` `https://code.claude.com/docs/en/permissions#managed-settings`；`package/sdk.d.ts:1995-2000`（`Options.managedSettings?: Settings`）

文件内格式：

```json
{
  "permissions": {
    "allow": ["Bash(npm test)", "Read(./.env)"],
    "deny": ["Bash(rm *)"],
    "ask": ["Bash(git push *)"],
    "defaultMode": "acceptEdits"
  }
}
```

`[读到]` `package/sdk.d.ts:5413-5429`（`Settings.permissions` 字段定义，与文档 JSON 示例一致）

索引 key 就是规则字符串本身（`Tool` 或 `Tool(specifier)`），不是某种 ID。宿主要索引/去重/展示"已授权了什么"，只能自己解析这些字符串，或调用 `resolveSettings()`（`@alpha`，合并各层文件并标注每个字段来自哪一层 `provenance`，但**不包含** `session`/flag 层的动态授权）。`[读到]` `package/sdk.d.ts:2705-2759`

代价：持久化范围是"整个项目/整个用户"，没有"按会话对象/按用户身份"的细分——如果宿主是多租户系统（一个进程给多个终端用户跑 agent），`localSettings` 写进的是同一个项目目录下的同一个文件，天然没有隔离；宿主如果不自己做额外隔离（比如给每个终端用户用独立的 `cwd`/`--add-dir`），会出现授权串号。

### 5 泛化与匹配

静态规则语法是文档化的、工具专属的字符串 DSL，核心语法 `Tool` 或 `Tool(specifier)`：

- 裸工具名：匹配该工具全部调用（deny 时会直接把工具从模型可见范围移除）
- 加 specifier：按工具类型有不同语法——Bash 是 `*` 通配 + `:*` 后缀 + 词边界规则；Read/Edit 是 gitignore 风格路径（`//` 绝对路径、`~/` 家目录、单斜杠相对于规则来源锚定、裸路径相对当前目录）；WebFetch 是 `domain:` 前缀；MCP 是 `mcp__server__tool`；Agent 是 `Agent(name)`
- deny/ask 规则额外支持按参数值匹配：`Tool(param:value)`，但**只能匹配工具输入的顶层标量字段**，且明确排除了"主要内容字段"（如 Bash 的 `command`、Read/Edit 的 `file_path`）以防止被绕过

`[读到]` `https://code.claude.com/docs/en/permissions#permission-rule-syntax`（含通配符边界、compound command 拆解等细节）

匹配优先级固定为 **deny > ask > allow**，先命中先决定，与规则的"具体程度"无关（一条宽泛的 deny 能拦住一条更具体的 allow）。`[读到]` 同上

归一化（"这一次" -> "这一类"）由谁做：默认由 SDK/CLI 内部逻辑做（体现为 `canUseTool` 第三参数里的 `suggestions`），宿主是消费者/挑选者；宿主也可以完全绕过 SDK 的归纳，自己写 `PermissionRuleValue.ruleContent`，但语法的合法性、通配符语义仍由 SDK 侧的匹配引擎解释和执行，宿主不能自定义匹配语法。`[读到]` 综合 `package/sdk.d.ts:2229-2232` 与 permissions 页

代价：字符串规则语法本身文档明确承认是"脆弱"的——例如试图用 `Bash(curl http://github.com/ *)` 限制域名会被大量变体绕过（换协议、加参数、走重定向、用变量拼 URL）。官方给的建议是改用 `WebFetch(domain:...)` 或 `PreToolUse` hook 做语义校验，而不是指望 Bash 规则字符串本身可靠。`[读到]` permissions 页 Warning 区块

### 6 撤销与可审计

撤销机制按存储位置分裂成三套,互不统一：

- 落盘的规则（userSettings/projectSettings/localSettings）：宿主只能自己去改/删对应的 `settings.json` 文件；`PermissionUpdate` 类型里虽然有 `type: 'removeRules'`，理论上可以用来撤销，但文档正文没有给出"如何在会话外主动发起一次 `removeRules`"的调用路径说明——它出现在 `canUseTool` 的返回类型里，天然绑定在一次工具审批的响应上，不是一个独立的"撤销 API"。`[读到]`（类型存在）+ `[未查]`（是否存在脱离 `canUseTool` 响应、由宿主主动发起的撤销调用）
- flag settings 层（`applyFlagSettings`）：可以传 `null` 清空某个顶层 key（如整个 `permissions` 对象），是宿主唯一明确文档化的、进程内可编程撤销手段，但只对这一层生效，不影响落盘规则。`[读到]` `package/sdk.d.ts:2461-2483`
- `session` 目的地的规则：没找到任何撤销 API，只能靠结束 `query()`。`[未查]`——不排除私有/未文档化的 control_request 支持撤销,但公开类型定义和文档都没有暴露。

审计：SDK 提供的唯一"查看已授权了什么"的公开能力是 `resolveSettings()`，且标注为 `@alpha`（不稳定 API），返回值带 `provenance`（每个顶层 key 由哪一层设置），但明确不包含 `session` 层的动态授权，也不是针对某个正在运行的 `Query` 实例的实时状态查询——它是一个独立的、读磁盘配置的静态函数。`[读到]` `package/sdk.d.ts:2705-2759`；正文注释"This reports the raw settings cascade, not a security decision"

`Query` 接口本身没有 `listPermissions`/`getGrantedRules` 一类方法（在 `sdk.d.ts` 中搜索未命中）。`[读到]`（缺失的确认基于对 `sdk.d.ts` 的穷举 grep）

代价：宿主如果想做"权限审计面板"（列出这个 agent 当前被允许做什么），没有单一权威数据源——落盘规则要读文件（或用 `@alpha` API），会话内动态授权要自己在 `canUseTool` 回调里旁路记录（SDK 不会主动告诉宿主"我刚刚把这条规则记住了"，宿主必须自己在返回 `updatedPermissions` 的同一次调用里同步维护自己的账本）。

### 7 审批 UX

SDK 完全不管 UI 渲染，但给宿主的信息足以拼出一张过得去的审批卡片：

- `toolName`、`input`（完整参数）
- `title`：SDK/bridge 预先渲染好的一句自然语言（如 "Claude wants to read foo.txt"），文档建议宿主优先用这个而不是自己拼 `toolName`+`input`
- `displayName`：适合按钮标签的短语（如 "Read file"）
- `description`：更长的人类可读说明（如 "Claude will have read and write access to files in ~/Downloads"）
- `decisionReason` / `blockedPath`：解释这次为什么触发了审批（比如访问了允许目录之外的路径）
- `matchedAskRule`：如果是因为命中一条用户配置的 `ask` 规则才落到回调，会带上具体是哪条规则（来源、工具名、规则内容）
- `suggestions`：可直接采纳的"记住"候选规则

`[读到]` `package/sdk.d.ts:209-268`

没有找到的：一个正式的风险等级字段（枚举/分数）。对 `sdk.d.ts` 全文搜索 "risk"/"Risk" 没有命中。`[读到]`（缺失基于穷举 grep 的确认）——CLI 交互界面里有一个按 `Ctrl+E` 触发、由模型现算的 Low/Med/High 风险解释，但那是 CLI 终端 UI 的专属功能，不是 `canUseTool` 回调会拿到的结构化字段。`[读到]` `https://code.claude.com/docs/en/permissions`（"labeled **Low risk**, **Med risk**, or **High risk**"一节，明确描述的是 Bash/PowerShell 权限提示的终端交互，未见其作为 SDK 回调参数出现）

另有一个辅助信号：`Notification` hook 会在 `canUseTool` 已经挂起约 6 秒后收到 `permission_prompt` 通知，宿主可以用它去做"审批超时提醒"（例如转发到 Slack），需要 TS SDK v0.3.233+ 或 Python SDK v0.2.139+。`[读到]` hooks 页

代价：`title`/`displayName`/`description` 都是 SDK/bridge**代宿主生成**的文案，宿主如果直接展示这些文案而不做二次审视，实际上是把"怎么描述风险"的话语权交还给了被审批的同一套系统——文案生成逻辑本身是黑盒，宿主无法验证它是否会低估某次调用的破坏性。

### 8 无人值守降级

SDK 支持的六种权限模式里，专门为"无人值守"设计的是 `dontAsk` 和 `bypassPermissions`：

- `dontAsk`：任何原本要走到 `canUseTool` 的调用直接拒绝，**`canUseTool` 完全不会被调用**（不是调用了拿到 deny，是根本不触发）。`AskUserQuestion`、要求用户交互的 MCP 工具、命中显式 `ask` 规则的调用、指向 critical path 的 `rm`/`rmdir`，即使已经在 `allow` 列表里也照样被拒绝。`[读到]` permissions 页
- `bypassPermissions`：需要在 `Options` 里显式再确认一次 `allowDangerouslySkipPermissions: true`（仅设置 `permissionMode: 'bypassPermissions'` 不够），且即便打开，仍有一组硬编码的例外**不受这个模式覆盖**：指向 critical path 的 `rm`/`rmdir`、要求用户交互的工具、命中显式 `ask` 规则的调用、跨会话消息（cross-session messaging）的两条安全阀。这些例外是 CLI/执行子进程内置的，宿主的模式配置无法关闭它们；组织侧可以用 managed settings 的 `permissions.disableBypassPermissionsMode` 整体禁用这个模式。`[读到]` `package/sdk.d.ts:1795-1798`；permission-modes 页

SDK 层面的失败默认值（不是模式，是"回调没答"这种异常情况）：`CanUseTool` 类型的官方注释明确写 "Fail-closed: an accidental null means no control_response is sent and the tool stays blocked indefinitely — permission prompts have no park deadline"。也就是说，宿主回调如果因为 bug 返回了 `null`（或者永远 pending），SDK **不会**有超时兜底去自动拒绝或自动放行——它会让这次工具调用永久挂起。`[读到]` `package/sdk.d.ts:203-207`

沙箱（Bash sandbox）是另一层独立的、OS 级别的防护，和权限模式并行工作而不是替代它：即使命令通过了权限评估，沙箱仍按文件系统/网络白名单限制它实际能碰到什么。但检索到的沙箱文档正文全篇没有出现 "Agent SDK" 字样，无法确认 `sandbox.*` 配置在 Agent SDK 会话里是否与 CLI 会话行为完全一致（例如是否同样通过 `settingSources` 加载）。`[未查]`——缺口：需要专门核对 `code.claude.com/docs/en/sandboxing` 是否有针对 SDK 场景的专门段落，或直接用 SDK 起一个会话实测 `sandbox.enabled` 是否生效。

代价：`dontAsk` 的"全部拒绝"策略对全自动流水线是安全的，但要求宿主提前把所有需要的工具通过 `allowedTools`/`permissions.allow` 精确列全，否则整条流水线会在第一个未列出的工具调用上直接失败而不是暂停等待——这是"fail closed 但不优雅"的降级：没有排队、没有重试提示，只有拒绝。而 `canUseTool` 本身的"无超时永久挂起"设计，意味着宿主如果没有自己在业务层加超时/看门狗，一个卡死的审批 UI 会让整个 agent 无限期挂起而不会自动降级为拒绝——这与很多人直觉里"没人批准就应该超时拒绝"的预期相反。

---

## 时序

```
Host process                SDK library              Execution subprocess ("bridge")
    |                             |                              |
    |--- query(options) -------->|                              |
    |                             |--- spawn / connect --------->|
    |                             |                              |
    |                             |         model requests tool call
    |                             |                              |
    |                             |<---- PreToolUse hooks run ---|
    |                             |         (deny short-circuits here)
    |                             |                              |
    |                             |<---- deny/ask/mode/allow  ---|
    |                             |      rules evaluated in order
    |                             |      (may resolve here, skip host)
    |                             |                              |
    |<--- control_request --------|<---- canUseTool needed ------|
    | (toolName, input,           |                              |
    |  suggestions, title, ...)   |                              |
    |                             |                              |
    | [host renders UI / logic]   |                              |
    |                             |                              |
    |--- control_response ------->|                              |
    | PermissionResult             |                              |
    | { allow/deny, updatedInput,  |                              |
    |   updatedPermissions? }      |                              |
    |                             |--- apply updatedPermissions ->|
    |                             |    (session: memory only;     |
    |                             |     userSettings/project/     |
    |                             |     local: SDK writes file)   |
    |                             |                              |
    |                             |<---- tool executes ----------|
    |                             |<---- PostToolUse hook -------|
    |                             |                              |
    |<--- SDKMessage stream ------|<---- result -----------------|
```

关键节点：`updatedPermissions` 一旦被采纳，后续同类调用会在"deny/ask/mode/allow"这一段被直接决出结果，不再触达宿主——这正是"下次别再问"的实现位置，而不是在宿主这一侧维护一份缓存。`[读到]`（综合 permissions 页评估顺序 + user-input 页 "Approve and remember" 段）

---

## 明确不做什么

- 不提供审批 UI，`title`/`displayName`/`description` 只是文案素材，渲染完全是宿主的事。`[读到]` overview 页能力表里没有"UI 渲染"这一项
- 不对 `canUseTool` 回调设超时或看门狗，回调不返回就永久挂起，SDK 不会替宿主兜底拒绝。`[读到]` `package/sdk.d.ts:203-207`
- 不提供一个统一的"当前已授权清单"查询接口；`resolveSettings()` 只读磁盘、标注为 `@alpha`、不含会话内动态授权。`[读到]` `package/sdk.d.ts:2705-2759`
- 不允许宿主定义超出内置字符串 DSL 之外的自定义匹配语法；宿主能选目的地、能挑规则，但不能改匹配引擎本身怎么解释一条规则。`[推断]`——未见任何"自定义 matcher 插件"接口
- 不在 `bypassPermissions` 下真正跳过全部检查：critical path 删除、需要用户交互的工具、显式 `ask` 规则、跨会话消息安全阀，这几类由执行子进程硬编码保留，宿主的模式配置管不到。`[读到]` permission-modes 页

---

## 未确认项汇总

1. `PermissionUpdate` 的 `removeRules` 是否存在脱离一次 `canUseTool` 响应、由宿主主动发起的独立撤销调用路径（例如某个 `Query` 方法），还是只能作为审批响应的附带效果。—— 去处：向 Anthropic 支持 / GitHub issue 追问，或实测一次 `canUseTool` 交互后看是否有额外的 control_request 可发起撤销。
2. `sandbox.*` 设置（文件系统/网络隔离）在 Agent SDK 会话里的生效范围与行为是否与 CLI 完全一致；沙箱文档正文未出现 "Agent SDK" 字样。—— 去处：起一个最小 SDK 会话，配置 `.claude/settings.json` 的 `sandbox.enabled: true`，实测 Bash 调用是否真的被隔离。
3. `PermissionUpdateDestination` 里的 `'cliArg'` 具体语义（宿主能否主动写入，还是纯粹只读标记）——文档正文未展开，仅在类型定义中出现。—— 去处：查看是否有更细的 changelog 条目，或用最小复现代码尝试用 `'cliArg'` 作为 destination 发起一次 `updatedPermissions`，观察行为。
4. Python SDK（`claude-agent-sdk` on PyPI）的类型定义未做同等深度的实读（本次仅通过文档代码示例交叉验证了字段名一致性，未拉取 `.pyi`/源码逐行核对）。—— 去处：`pip download claude-agent-sdk` 后读其类型 stub 或源码。
5. `resolveSettings()` 被标记为 `@alpha`，其字段和行为随时可能变化，本报告引用的字段（`effective`/`provenance`/`sources`）截至 `0.3.236` 有效，不保证长期稳定。—— 去处：关注 TypeScript SDK 的 `CHANGELOG.md`（`github.com/anthropics/claude-agent-sdk-typescript`）。

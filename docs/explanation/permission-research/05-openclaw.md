# OpenClaw 权限模块机制报告

## 元信息

- 分析对象：OpenClaw
- 版本：commit `09e471f32e25370ebc483224de377fe0f60f6528`
- 路线：纯源码（`~/Repositories/openclaw`）
- 分析日期：2026-08-19
- 分析覆盖的文件清单：
  - 文档：`docs/tools/exec-approvals.md`、`docs/tools/exec-approvals-advanced.md`、`docs/cli/approvals.md`
  - 核心策略与存储：`src/infra/exec-approvals.ts`、`exec-approvals.types.ts`、`exec-approvals-effective.ts`
  - 泛化与匹配（重点）：`src/infra/exec-allowlist-pattern.ts`、`exec-allowlist-matching.test.ts`、`exec-approvals-analysis.ts`、`exec-approvals-allowlist.ts`、`exec-command-resolution.ts`、`exec-wrapper-trust-plan.ts`、`dispatch-wrapper-resolution.ts`、`exec-safe-bin-policy.ts`、`exec-safe-bin-trust.ts`、`exec-safe-bin-semantics.ts`、`command-analysis/inline-eval.ts`、`command-analysis/risks.ts`
  - 拦截与执行链：`src/infra/exec-host.ts`、`exec-safety.ts`、`permissions.ts`、`approval-gateway-resolver.ts`、`approval-types.ts`、`system-run-approval-binding.ts`、`src/node-host/invoke-system-run.ts`、`src/node-host/exec-policy.ts`、`src/agents/bash-tools.exec-host-gateway.ts`、`bash-tools.exec-host-node-phases.ts`、`bash-tools.exec-host-shared.ts`、`src/gateway/node-invoke-system-run-approval.ts`、`node-invoke-system-run-approval-match.ts`、`exec-approval-manager.ts`
  - UX 与转发：`src/infra/approval-view-model.ts`、`approval-view-model.types.ts`、`exec-approval-channel-runtime.ts`、`exec-approval-reply.ts`、`exec-approval-command-display.ts`、`exec-approval-forwarder.ts`、`approval-request-account-binding.ts`、`plugin-approvals.ts`
  - CLI 与配置：`src/cli/exec-approvals-cli.ts`、`src/config/types.tools.ts`、`src/config/zod-schema.agent-runtime.ts`

## 定位

Exec approvals 是沙盒 agent 与真实执行主机（gateway 或 node host）之间的守护层：agent 自身运行在沙盒里，任何需要落到真实主机文件系统 / 网络的命令都必须先穿过这一层。没有它，agent 发出的 shell 命令会直接在真机上无条件执行。它只在 `tools.exec` 把命令路由到真实主机、且 `elevated` 不是 `full`（`elevated full` 会整体跳过 approvals）时才被触发；纯沙盒内执行不经过这条链路。

## 架构

```
[sandboxed agent]
      |  exec request (argv, cwd, env)
      v
[gateway] <---- reads local ~/.openclaw/exec-approvals.json (gateway-host policy)
      |  host=node ? -> non-authoritative allowlist precheck (RPC exec.approvals.node.get)
      |  policy says "ask" ? -> broadcast exec.approval.requested
      v
[operator UI / Control UI / chat channels (Slack, Discord, Telegram, Matrix, Teams)]
      |  human replies allow-once / allow-always / deny,
      |  or askFallback auto-resolves on timeout / no route
      v
[gateway] -- exec.approval.resolve --
      |  sanitizeSystemRunParamsForForwarding:
      |  strip client-supplied approved/approvalDecision, re-bind to the
      |  ORIGINAL request's nodeId + connection + argv/cwd/agentId/sessionKey/env-hash
      v
[node host service] -- IPC (UDS, same-uid check, HMAC token, TTL) --> [macOS app]
      |  re-derive policy from its OWN local ~/.openclaw/exec-approvals.json
      |  independent allowlist/security re-check (does NOT trust gateway's precheck)
      v
[real command execution on host filesystem]
```

三层互不完全信任：(1) 沙盒 agent 与执行主机之间靠 socket 请求上的 HMAC 签名建立信任，主机不信任 agent 自称的任何字段；(2) gateway 对 `host=node` 请求做的 allowlist 预检是非权威的，仅用来决定要不要弹审批，源码注释直接写明 "may diverge"；(3) node host 收到 gateway 转发的批准结果后，重新从自己本地文件推导一遍策略，但对"这个批准到底是谁点的"这件事，最终仍然只信任 gateway 转发过来的、经过字段绑定校验的标记，没有二次验证人身份的机制。

## 八切面

### 1 拦截点

**结论：** 拦截发生在三个不完全互信的位置。(a) 沙盒执行主机之间的 socket 请求带 HMAC 签名（`src/infra/exec-host.ts:35-60`，HMAC 计算见 49-52 行）；(b) `host=node` 场景下 gateway 先做一次非权威的 allowlist 预检（RPC `exec.approvals.node.get`，`src/agents/bash-tools.exec-host-node-phases.ts:313-345`，328 行注释明确写 "Allowlist-only precheck; safe bins are node-local and may diverge"）；(c) node host 收到转发请求后，独立地从自己本地 `~/.openclaw/exec-approvals.json` 重新推导整套策略（`resolveExecApprovals()`，`src/node-host/invoke-system-run.ts:379`，`evaluateSystemRunPolicyPhase` 369-460 行），不信任 gateway 缓存的判断。拦截拦的是**工具名 + 解析后的 argv / 已解析可执行文件路径**，不是工具名单独（`matchAllowlist`，`src/infra/exec-command-resolution.ts:342-386`）。
**代价：** gateway 的预检可能与 node 的权威复核结果不一致（源码自己承认 "may diverge"）——用户可能在操作界面上被告知"无需审批"，而 node 端实际独立拒绝了执行（或反过来）。
**把握度：** [读到]

**结论：** 批准落地后，gateway 对"任意 RPC 客户端"这一信任边界也做了单独处理：`sanitizeSystemRunParamsForForwarding`（`src/gateway/node-invoke-system-run-approval.ts:116-324`）会剥离调用方自带的 `approved`/`approvalDecision` 字段，只有在能匹配到一条真实、未过期、绑定同一 `nodeId`/连接/argv/cwd/agentId/sessionKey/env-hash 的 `exec.approval.*` 记录时才重新写回（匹配逻辑见 `src/infra/system-run-approval-binding.ts:126-136,201-223`）；源码注释（111-115 行）明确说这是为了防止只有 `operator.write` 权限的用户通过往 `node.invoke` 里塞控制字段来绕过 node-host 审批。
**代价：** 这堵住了"批准 A 命令、悄悄换成 B 命令"的混淆代理漏洞，但 node host 最终的执行门（`src/node-host/exec-policy.ts:76`，`approvedByAsk = params.approvalDecision !== null || params.approved === true`）本质上是相信 gateway 转发过来的标记是合法的——node 不会独立复核"这个人真的批准了吗"，只复核"这个字段和原始请求是否绑定一致"。
**把握度：** [读到]

### 2 决策单元

类型定义（直接引用，行号见下）：

```ts
// src/infra/exec-approvals.ts:24-25
export type ExecSecurity = "deny" | "allowlist" | "full";
export type ExecAsk = "off" | "on-miss" | "always";

// src/infra/exec-approvals.ts:1234-1239
export type ExecApprovalDecision = "allow-once" | "allow-always" | "deny";

// src/infra/exec-approvals.types.ts:1-10
export type ExecAllowlistEntry = {
  id?: string; pattern: string; source?: "allow-always";
  commandText?: string; argPattern?: string;
  lastUsedAt?: number; lastUsedCommand?: string; lastResolvedPath?: string;
};
```

**结论：** 一次审批回应只能是三选一：`allow-once`（仅这一次，`manager.consumeAllowOnce(runId)` 消费）、`allow-always`（落盘为一条 `ExecAllowlistEntry`）、`deny`。类型系统里没有"批准这个会话/接下来 N 分钟"这种中间粒度。
**代价：** 任何"有限次但要重复"的场景（比如"接下来一小时内的构建脚本都别问了"）没有原生表达，操作者只能在"每次都重新点"和"永久信任"之间二选一。
**把握度：** [读到]

**结论：** `allow-always` 默认落地的粒度不是"这一次调用"，而是**PATH 解析后的绝对可执行文件路径**，且在非 Windows 主机上参数完全不受限。`collectAllowAlwaysPatterns`（`src/infra/exec-approvals-allowlist.ts:962-976`）持久化的 `pattern` 就是 `resolveExecutionTargetCandidatePath` 返回的已解析路径；`argPattern` 的构造函数 `buildArgPatternFromArgv` 在非 `win32` 平台直接 `return undefined`（`exec-approvals-allowlist.ts:910-913`）；匹配时无 `argPattern` 的条目被视为"路径匹配即通过，忽略当前 argv"（`pathOnlyMatch`，`exec-command-resolution.ts:374-378`）。
**代价：** 在 macOS/Linux 上，对 `git log` 点一次"allow always"，之后 `git` 的任意参数组合（包括 `git push --force`、`git reset --hard`）都不再弹窗——授予的信任范围比用户实际看到并批准的那一条命令宽得多。
**把握度：** [读到]

**结论：** 还存在一个"整个信任域"级别的单元——裸 `"*"` 通配符条目。`matchAllowlist` 专门对 `pattern.trim() === "*" && !argPattern` 的条目做了特判，匹配任意已解析的可执行文件（`exec-command-resolution.ts:354-357`），CLI 文档也直接给出 `openclaw approvals allowlist add --agent "*" "/usr/bin/uname"` 这类用法（`src/cli/exec-approvals-cli.ts:556-573`）。
**代价：** 一条手写的 `"*"` 记录可以把某个 agent 的 `security=allowlist` 静默变成事实上的 `security=full`，而配置里可见的 `security` 字段本身没有变化——这是一个配置审查盲区。
**把握度：** [读到]

**结论：** 零配置时的默认策略本身就是最宽的单元：`DEFAULT_SECURITY = "full"`、`DEFAULT_ASK = "off"`（`src/infra/exec-approvals.ts:205-206`，已直接核对源码）。跨"请求策略"与"主机本地文件"两个来源取最严的一方合并（`minSecurity`/`maxAsk`，`exec-approvals.ts:1224-1232`）。
**代价：** 安全姿态是完全 opt-in 的——任何没有主动收紧过配置的 agent，默认就是不受限执行。
**把握度：** [读到]

**结论：** 用户可以通过 CLI 独立于审批弹窗手动升降级：`openclaw approvals allowlist add/remove <pattern> [--agent <id>]`（`src/cli/exec-approvals-cli.ts:556-608`），既可以写窄 glob（`~/Projects/**/bin/rg`），也可以写最宽通配。
**代价：** 代价未识别（这是一条显式、有意识的操作者动作，风险已经在上面"路径匹配、参数不受限"这条里体现）。
**把握度：** [读到]

**结论：** 当 `ask="always"` 时，提供给用户的决策集合会收窄——`allow-always` 被排除在候选之外（`resolveExecApprovalAllowedDecisions`，`exec-approvals.ts:1241-1249`，数组字面量里没有 `"allow-always"`）。也就是说粒度的"天花板"本身也受策略控制。这里没有在真正的决策校验落地点（resolve handler）里逐行确认拒绝逻辑，因此标记为推断。
**代价：** 代价未识别。
**把握度：** [推断]（推导链：数组字面量在 `ask=always` 分支省略了 `"allow-always"` → `isExecApprovalDecisionAllowed` 按此数组做成员校验 → 未直接追踪到实际 resolve 调用点是否严格执行这一校验）

### 3 生命周期

**结论：** 决策模型是固定三档，没有"用了 N 次自动升级为永久信任"的机制。`allow-always` 只能由调用方/人类显式返回该决策字符串触发（持久化调用点：`src/node-host/invoke-system-run.ts:620`、`src/agents/bash-tools.exec-host-gateway.ts:488`），`exec-approvals.ts` 与 `exec-approvals-allowlist.ts` 中未发现任何计数/阈值自动提升逻辑。
**代价：** 每一次 `allow-always` 都是一次未经二次确认的单击，会立刻生成永久信任的模式——没有冷静期或重复确认步骤。
**把握度：** [读到]

**结论：** 只有"等待中的单次审批请求"会过期，落盘后的 allowlist 条目永不过期。待处理请求存在内存 `Map` 里（`src/gateway/exec-approval-manager.ts:55`），默认超时 30 分钟（`DEFAULT_EXEC_APPROVAL_TIMEOUT_MS = 1_800_000`，`src/infra/exec-approvals.ts:203`，已直接核对源码）。已落盘的 `ExecAllowlistEntry` 唯一会变化的字段是 `lastUsedAt`/`lastUsedCommand`/`lastResolvedPath`（`recordAllowlistUse`，`exec-approvals.ts:1068-1093`），未发现任何过期/清理/降级逻辑。
**代价：** 一条几个月前批准的 `allow-always` 授权（哪怕同路径下的脚本内容/含义已经变了）会永远保持被信任，没有任何自动重新审查的触发点。
**把握度：** [读到]

**结论：** 同机重启：待处理审批（内存态）会丢失，已批准的 allowlist（磁盘态）会保留——每次检查都从磁盘重新加载（`resolveExecApprovals()` → `ensureExecApprovals()` → `loadExecApprovals()`，`exec-approvals.ts:895-899、745-758、684-699`）。
**代价：** 代价未识别（超出"等待中的请求需要重新发起"这一显而易见的摩擦之外，未发现更深的问题）。
**把握度：** [读到]

**结论：** 换机会丢失整个 `allow-always` 层级。审批文件路径通过 `expandHomePrefix` 展开到当前机器的 `HOME`（`exec-approvals.ts:219-221`），gateway 和 node 各自维护独立文件、互不同步；新机器上找不到文件时直接回落到 `{version:1, agents:{}}`（`exec-approvals.ts:687` 附近的回退逻辑）。未发现导出/导入机制。
**代价：** 迁移机器或新增第二台执行主机时，之前一点一点攒起来的 `allow-always` 模式必须从零重建。
**把握度：** [推断]（推导链：家目录展开逻辑 + 两份文件从不同步的既有事实 + 未找到 export/import 代码路径）

### 4 持久化与作用域

**结论：** 存储是每台执行主机一份本地 JSON 文件，没有数据库。文件路径 `~/.openclaw/exec-approvals.json`（`DEFAULT_FILE`，`exec-approvals.ts:210`），写入走临时文件+原子 rename，并 `chmod 0o600`（`saveExecApprovals` → `writeExecApprovalsRaw`，`exec-approvals.ts:701-731`，`mode: 0o600, flag: "wx"` 在 713 行）。
**代价：** 代价未识别（写入机制本身是合理的原子写保护；真正的代价出现在下面的冷启动重建失败场景）。
**把握度：** [读到]

**结论：** 索引 key 是 `agentId`（默认 `"main"`），外加一个可选的 `"*"` 通配层；同一个 agent 下的 allowlist 是一个数组，逐条线性扫描匹配，没有对"主机"或"命令哈希"建索引（`resolveExecApprovalsFromFile` 的 agentKey 解析在 `exec-approvals.ts:921-925`；线性扫描见 `evaluateExecAllowlist`，`exec-approvals-allowlist.ts:646-693`）。
**代价：** 性能代价未经验证——大量条目意味着每次 exec 调用都要做 O(n) 次正则匹配，但源码里没有找到这在实际规模下是否构成问题的证据。
**把握度：** [读到]

**结论：** 作用域是"每台执行主机隔离，同一 agentId 下跨会话/跨项目共享"。`exec-approvals-effective.ts` 里把请求策略与主机文件按"更严格者优先"合并（`minSecurity`/`maxAsk` 调用，151-305 行区间）；`ExecAllowlistEntry` 类型里完全没有 `sessionId`/`projectId` 字段（`exec-approvals.types.ts:1-10`）。
**代价：** 在项目 A 里工作时点的 `allow-always`，会对同一 agentId 在这台主机上的所有其他项目/会话静默生效——索引 key 里没有任何东西把它限定在某个工作目录内。
**把握度：** [读到]

**结论：** 冷启动加载失败（文件缺失、JSON 解析失败、`version` 不为 1）时，`loadExecApprovals()` 会静默回落到空状态 `{version:1, agents:{}}`，不抛出任何错误（`exec-approvals.ts:684-699`）。更关键的是，几乎每次 exec 检查都会调用的 `ensureExecApprovals()`（`src/agents/bash-tools.exec-host-shared.ts:199`、`src/node-host/invoke-system-run.ts:379`）在结尾会**无条件**调用 `saveExecApprovals(updated)`（`exec-approvals.ts:745-758`）——哪怕刚刚加载到的就是那个空回退状态。
**代价：** `~/.openclaw/exec-approvals.json` 一旦损坏（JSON 格式错误、手改出错、version 不匹配），下一次执行任何命令时，整份文件（所有 agent 的 allowlist、defaults、socket token）会被静默清空并用空默认值覆盖写回——没有警告，没有备份。
**把握度：** [读到]

### 5 泛化与匹配

**结论（pattern 语法）：** allowlist 的 pattern 不是接入某个通用 glob 库，而是一个手写的迷你 glob 编译器：`*` → `[^/]*`（单层路径段）、`**` → `.*`（任意深度）、`?` → `[^/]`（单字符），其余字符原样正则转义，整体加 `^...$` 锚定（`compileGlobRegex`，`src/infra/exec-allowlist-pattern.ts:28-66`）。大小写归一化和反斜杠归一化**只在 `win32` 上生效**（`normalizeMatchTarget`，8-14 行；正则 flag 在 60 行）；符号链接归一化同样只在 Windows 且仅对无通配符的 pattern 生效（`tryRealpath` 调用，78-81 行）。测试直接确认了大小写敏感：`{pattern:"RG"}` 不匹配 `rg`（`exec-allowlist-matching.test.ts:12`）。
**代价：** 在默认大小写不敏感的 macOS 文件系统上，写成 `/Opt/Homebrew/bin/rg` 的 pattern 永远匹配不到实际解析出的 `/opt/homebrew/bin/rg`，没有任何归一化兜底；同一个真实二进制文件通过两条不同的符号链接路径调用，会被当成两个互不相关的信任对象（非 Windows 上没有 realpath 等价类归并）。
**把握度：** [读到]

**结论（两级匹配：裸命令名 vs 路径 pattern）：** `matchAllowlist`（`src/infra/exec-command-resolution.ts:342-386`）按 pattern 是否含路径分隔符（`/`、`\`、`~`）分流：含分隔符则对完整已解析路径做匹配；不含则只匹配 PATH 解析出的可执行文件 basename，**且要求调用命令本身也不含路径分隔符**（`matchesExecutableBasenamePattern` 在 322-340 行里对 `resolution.rawExecutable` 含路径选择符时直接拒绝，329-331 行）——也就是说 `./rg` 或 `/tmp/rg` 永远无法满足裸 `rg` 条目，哪怕它们解析到的是同一个真实二进制。测试用例已确认这一点（`exec-allowlist-matching.test.ts:27-41`）。裸 `"*"` 是唯一的全放行例外（354-357 行）。
**代价：** 这是刻意的反提权设计（工作区里的 `./rg` 不能继承全局 `rg` 授权），但代价是：同一个真实二进制通过两种不同方式调用，需要两条不同的 allowlist 条目——尽管背后执行的风险完全一致，系统并不做统一。
**把握度：** [读到]

**结论（argPattern：对 argv[1:] 的正则匹配，排除 argv[0]）：** `argPattern` 是一段针对 `argv.slice(1)` 拼接字符串做匹配的原生正则；存在两种拼接约定并存——手写条目用空格拼接（`matchArgPattern`，`exec-command-resolution.ts:263-316`），自动生成的 Windows 条目用 `\x00` 拼接并加哨兵位区分零参/单参情况（`buildArgPatternFromArgv`，`exec-approvals-allowlist.ts:910-921`；拼接方式的识别逻辑在 `exec-command-resolution.ts:264-274` 注释里说明）。额外有一次针对 Windows 目标的 `/` → `\` 归一化重试，以及仅对"空格拼接"这一种手写风格生效的、去除末尾 shell 重定向（`2>&1` 等）后的重试（288-311 行）。
**代价：** 手写 `argPattern` 若不加锚定，会退化为对整段拼接字符串的子串匹配，可能匹配到意料之外的参数组合；而"去重定向后重试"这条容错只覆盖手写风格，自动生成的 `\x00` 拼接条目对 argv 的微小漂移更脆弱。
**把握度：** [读到]

**结论（从"这一次"到"这一类"的核心转换：allow-always 默认不生成 glob，而是精确路径捕获）：** `collectAllowAlwaysPatterns`（`exec-approvals-allowlist.ts:936-1036`）持久化的 pattern 就是 `resolveExecutionTargetCandidatePath` 返回的 PATH 解析绝对路径（`exec-command-resolution.ts:205-213`，取的是 `resolvedPath`，**不是** `resolvedRealPath` 符号链接目标）——不会自动插入任何通配符。非 Windows 平台上连 `argPattern` 都不生成（同上，`buildArgPatternFromArgv` 直接 `return undefined`），条目退化为"路径匹配、参数完全不限"。要把"这一次"变成"这一类"（比如文档示例里的 `~/Projects/**/bin/rg`），必须由用户手动编辑配置或在 UI 里操作——`allow-always` 的自动路径从不合成 glob。当连单个可执行文件路径都推导不出来时，系统退到另一个极端：对**整段命令原文**做 sha256 哈希（截断 16 位十六进制，前缀 `=command:`，`buildDurableCommandApprovalPattern`，`exec-approvals.ts:1035-1038`），归一化仅有 `.trim()`（`exec-approvals.ts:1044、1187`），没有空白折叠、大小写归一化或引号风格归一化。
**代价：** 同一个机制里同时存在两个方向的失效：(a) 偏宽——path-only 的 `allow-always` 授权参数不受限（`rg` 变成"rg，做任何事都行"）；(b) 偏窄——哈希兜底精确到连多敲一个空格都会导致缓存未命中、重新弹窗，让"永久允许"对这一档完全失效。
**把握度：** [读到]

**结论（复合命令拆分：shell chain 和管道被拆成独立分段分别校验）：** `analyzeShellCommand`（`exec-approvals-analysis.ts:1073-1112`）先按 `&&`/`||`/`;` 切链，链内每段再按 `|` 切管道；`evaluateExecAllowlist`/`evaluateSegments`（`exec-approvals-allowlist.ts:581-693`）要求**每条链的每个分段**（`segments.every(...)`，597 行）都独立满足 allowlist/safeBins/skills 之一——所以 `echo ok && pwd` 需要 `echo` 和 `pwd` 都在名单里，`foo | bar` 需要管道两端都在名单里。
**代价：** 代价未识别（这是偏保守/偏安全的设计方向；真正的代价体现在下面的解析器拒绝清单里）。
**把握度：** [读到]

**结论（已知绕过路径与对应防护，按归一化维度列举）：**

- 命令替换（`$(...)`、反引号）在 allowlist 模式解析阶段被直接拒绝，因为 `(` 和反引号都在 `DISALLOWED_PIPELINE_TOKENS` 集合里（`exec-approvals-analysis.ts:45`），从而阻断了 `$(...)` 的构造；重定向符 `>`/`<` 同属该集合，同样被拒绝。
- 大小写：非 Windows 上不做任何归一化（见上）。
- 相对路径/家目录展开：`~` 会在 pattern 编译前通过 `expandHomePrefix` 展开（`exec-allowlist-pattern.ts:74`）；绝对路径与相对路径的区分是刻意保留的反提权控制，不是漏洞。
- shell 展开（`$VAR`、花括号/通配符展开）：在读到的文件范围内没有找到"模拟真实 shell 展开后再匹配"的代码——匹配始终作用在 OpenClaw 自己语法层面解析出的 argv 上，不是真实 shell 最终会执行的内容。这是基于"未找到"的推断，未穷尽阅读 `shell-inline-command.ts`/`exec-wrapper-tokens.ts`/`executable-path.ts` 全文，故单独列入未确认项。
- 派发型 wrapper（`env`、`ionice`、`nice`、`nohup`、`stdbuf`、`timeout`）和 shell 多路复用器（`busybox`/`toybox` 类）会被拆解，最多 4 层（`MAX_DISPATCH_WRAPPER_DEPTH = 4`，`dispatch-wrapper-resolution.ts:11,351-385`；循环逻辑见 `exec-wrapper-trust-plan.ts:65-146`），使得 `allow-always` 持久化的是内层可执行文件而不是 wrapper 本身；如果链条在深度限制内无法安全拆解或遇到未识别的 wrapper，整个 plan 会被标记 `policyBlocked`，不生成任何 pattern（`blockedExecWrapperTrustPlan`，`exec-wrapper-trust-plan.ts:22-37,75-82,96-102,121-142`）。
- 解释器/内联求值防护：`command-analysis/inline-eval.ts:35-153` 维护了一份固定的"解释器类"二进制名单（python 系、node/bun/deno、awk 系、ruby、perl、php、lua、osascript、find、make、sed 系、xargs）。`isInterpreterLikeAllowlistPattern`（294-307 行）命中该名单时，`collectAllowAlwaysPatterns`（`exec-approvals-allowlist.ts:966-971`）里的判断是：`params.strictInlineEval !== true || detectInlineEvalArgv(effectiveArgv) !== null` 满足其一即直接 `return`（不持久化）。也就是说**在 `strictInlineEval` 默认关闭（`tools.exec.strictInlineEval` 是可选布尔字段，zod schema 里未设默认值，`src/config/zod-schema.agent-runtime.ts:471`）的情况下，名单里任何一个解释器，无论具体这次调用是不是内联求值，`allow-always` 都不会生成任何 allowlist 条目**——只有显式打开 `strictInlineEval:true` 且这次调用**不是**内联求值（`detectInlineEvalArgv` 判定，`command-analysis/risks.ts:80-127`）时才会持久化。
- 安全兜底 bin（safe bins）是第三种、结构不同的匹配档位：`isSafeBinUsage`（`exec-approvals-allowlist.ts:65-`）要求可执行文件 basename 在配置的 `safeBins` 集合里、其解析路径所在目录在一个显式信任目录集合里（默认仅 `/bin`、`/usr/bin`，且明确声明"不从 PATH 派生"，`exec-safe-bin-trust.ts:6,58-68`），并通过一张按具体 bin 名硬编码的语义规则表（`jq` 对 `env`/`$ENV` token 做正则拒绝；`awk`/`gawk`/`mawk`/`nawk`/`sed`/`gsed` 无论是否被配置进 `safeBins` 都被硬编码永久拒绝，`exec-safe-bin-semantics.ts:15,23-55`）。

**代价：** 上述三处防护（wrapper 拆解名单、解释器名单、safe-bin 语义规则表）都是同一种模式的重复——**封闭枚举清单**。不在名单里的 wrapper、解释器或 safe bin 不会获得对应的特殊处理：未识别的 wrapper 要么拒绝持久化，要么把 wrapper 自身路径当成被信任对象；未列入解释器名单的新兴脚本语言/REPL 不受"默认不持久化"这条保护，反而会按普通二进制走"路径匹配、参数不受限"的宽松通道；safe bin 语义规则表只覆盖 `jq`/`awk`/`sed` 三个家族，其余 bin 只有通用的 argv 结构校验，没有针对性语义审查（`openclaw security audit` 的 `safe_bins_interpreter_unprofiled` 提示是可选 lint，不是强制门）。此外，"clicking allow-always on `python3 script.py` 却不落盘"这件事本身没有任何用户可见的解释，是本次调研中最反直觉的行为。
**把握度：** [读到]

**归类小结：** 报告开头列出的六档泛化方式（不泛化/精确匹配/前缀 glob/结构化 pattern/规则 DSL/模型判定）在 OpenClaw 里的映射是——`allow-always` 默认落地效果 = 精确路径匹配（但参数不受限，不是严格意义的精确匹配）；手写 allowlist 条目支持前缀 glob（`*`/`**`），但这是用户驱动而非系统生成；`argPattern` = 结构化 pattern（对已解析 argv 的正则）；safe bins = 结构化 pattern + 规则 DSL 混合；内联求值检测 = 规则 DSL（固定 flag 规格表），但它只用来决定"是否允许持久化"，不参与生成 pattern 的形状；在已读范围内没有找到任何模型判定（LLM 分类）参与匹配或生成 pattern 的代码路径。
**把握度：** [推断]（后半句"没有模型判定参与"是基于未找到相关代码的推断，已列入未确认项）

### 6 撤销与可审计

**结论：** 撤销走 CLI，`openclaw approvals allowlist remove <pattern>` 只按 `pattern` 字符串过滤，不看 `argPattern`（`src/cli/exec-approvals-cli.ts:380-383,593-619`）。而授权时可以生成 `(pattern, argPattern)` 不同组合的多条独立记录（`exec-approvals.ts:1131-1180,1196-1220`）。
**代价：** 撤销一个 pattern 会连带删掉所有共享该 pattern、不同 `argPattern` 的授权——无法只收回其中一条窄参数授权而保留其他。撤销粒度比授权粒度粗，二者不对称。
**把握度：** [读到]

**结论：** 没有持久化的单次审批请求审计日志。`ExecApprovalManager` 只在进程内存 `Map` 里保存待处理/已解决记录，已解决记录在 15 秒后被清除（`RESOLVED_ENTRY_GRACE_MS = 15_000`，`src/gateway/exec-approval-manager.ts:8,118-160`）。唯一的持久痕迹是 allowlist 条目的 `lastUsedAt`/`lastUsedCommand`/`lastResolvedPath`，且每次复用都会被覆盖（`exec-approvals.ts:1068-1093`）——只保留"最近一次使用"快照，不是日志。事后唯一的记录形式是转发到聊天频道的一条纯文本消息（`"✅ Exec approval {decision}. Resolved by {resolvedBy}. ID: {id}"`，`src/infra/exec-approval-forwarder.ts:299-306`），存在于第三方聊天历史里，不可在 OpenClaw 内部查询或导出。另外，持久化的 `ExecAllowlistEntry` 类型本身没有 `resolvedBy` 字段（`exec-approvals.types.ts:1-10`，已核对源码），而 `resolvedBy` 只存在于临时的 `ExecApprovalResolved` 事件类型上（`exec-approvals.ts:153`）——`addAllowlistEntry` 构造持久条目时（`exec-approvals.ts:1167-1176,1216-1219`）从未写入这个字段，也就是说一旦某次批准变成永久授权，"是谁批准的"这一信息不会随之保留。在 `src/infra/exec-approvals.ts`/`exec-approvals-allowlist.ts` 里搜索 "audit"/"log" 关键字均无命中。
**代价：** 误批一条过宽规则后，恢复路径只有"删掉整条 pattern"（粒度比授权粗，见上）；15 秒后连"这次批准是谁点的"都查不到，只能靠聊天频道自己的历史记录（如果频道还留着）。
**把握度：** [读到]（"没有专门审计日志文件"这一结论基于对两个最相关文件的关键字检索，未排除应用日志系统里可能存在的通用日志记录，已列入未确认项）

### 7 审批 UX

**结论：** 聊天审批提示包含：可选的风险警告文字、以 `/approve <id> <decision>` 为主命令的操作块、脱敏+截断后代码块形式的待执行命令、其余可选决策项、`Host:`、`Node:`（如有）、格式化后的 `CWD:`、`Expires in: ...` 剩余时间、完整审批 id（`src/infra/exec-approval-reply.ts:287-353`）。风险指示来自静态启发式规则产出的 `commandAnalysis.riskKinds`（如 `"inline-eval"`、`"command-carrier"`，`src/infra/command-analysis/explain.ts:7-79`，展示逻辑在 `approval-view-model.ts:70-75`）。
**代价：** 命令脱敏是启发式模式匹配（`redactSensitiveText`，`exec-approval-command-display.ts:96-129`）——不匹配已知模式的密钥不会被脱敏，会原样出现在外部聊天平台上并长期留存；风险提示同样只覆盖已识别的危险构造，用不认识的方式达成同样效果的命令看起来和普通命令毫无区别。
**把握度：** [读到]

**结论：** 选项集合固定为 `allow-once`/`allow-always`/`deny` 三选一，`ask=always` 时候选集合收窄为 `["allow-once","deny"]`（`exec-approvals.ts:1234-1249`）。文本 UI 里始终把 `allow-once` 排在最前作为主推荐命令（`exec-approval-reply.ts:108-153,296`），但按钮式 UI 给三个选项分别标了 `success`/`primary`/`danger` 三种样式，`allow-always` 恰好是 `primary`（108-151 行区间）。
**代价：** 文字说明把 `allow-once` 当作"该做的事"，按钮样式却把更宽松、更持久的 `allow-always` 标记为 `primary`——如果某个聊天平台的渲染层恰好用视觉更突出的方式呈现 `primary` 按钮，会在无意中把操作者引导向风险更高的选项。具体各平台是否真的这样渲染未核实。
**把握度：** [读到]（按钮样式与文案顺序的不一致本身已直接读到；"是否真的造成视觉误导"这一后果是推断，因为渲染代码在 `../interactive/payload.js` 及各渠道适配器里，不在本次阅读范围内）

**结论：** 默认超时 30 分钟（`DEFAULT_EXEC_APPROVAL_TIMEOUT_MS = 1_800_000`，已核对源码）。超时后 `ExecApprovalManager.expire()` 把等待结果置为 `null`，随后由 `askFallback` 分支处理：`full` 视为已批准通过、`deny` 按 `"approval-timeout"` 理由拒绝、`allowlist` 转入普通 allowlist 匹配（`resolveBaseExecApprovalDecision`，`src/agents/bash-tools.exec-host-shared.ts:170-191`）。
**代价：** 同一个 `askFallback` 开关同时管两种截然不同的场景——"完全没人在看审批频道"和"有人在看但超过 30 分钟才回复"。想只针对无人值守场景设 `askFallback:"deny"` 的操作者，会顺带把所有"只是回复慢了"的正常人工审批也自动拒绝掉，没有重新通知或延长等待的机制。
**把握度：** [读到]

**结论：** 没有批量审批 UI。每条 `exec.approval.requested` 事件独立处理，按 id 去重后各自投递一条消息/卡片（`exec-approval-channel-runtime.ts:137-198`，去重逻辑 148-151 行），重连后的重放也是逐条重放（`replayPendingApprovals`，245-268 行）。
**代价：** agent 同时发起多个并行 exec 调用时，会在审批频道里刷出多条独立提示，没有"当前有 3 条待批准"的汇总视图或批量操作。
**把握度：** [读到]

### 8 无人值守降级

**结论：** 默认策略是失败开放（fail-open）而不是保守方向：零配置时的 `security="full"`、`ask="off"`、`askFallback="full"` 全部已在源码里直接确认（`exec-approvals.ts:205-207`）。文档也印证了这一点："YOLO is the default host behavior unless you tighten it explicitly"（`docs/tools/exec-approvals.md:176`）；文档里出现的 `"askFallback": "deny"` 只是示例 schema，不是实际出厂默认值。
**代价：** 全新安装的 OpenClaw 在 host exec 上零提示、零人工介入门槛；如果操作者默认假设"审批默认是开着的，需要主动选择 YOLO"，这个假设从一开始就是反的，必须主动收紧 `security`/`ask`/`askFallback` 才能获得任何门控。
**把握度：** [读到]

**结论：** 一旦收紧之后，"没有可用 UI"和"人回复太慢超时"这两种场景走的是同一套 `askFallback` 分支（见切面 7）——`askFallback` 若仍留在默认值 `full`，即便 `ask` 被打开做纵深防御，只要审批通道一时不可达（网络抖动、聊天 app 挂了），这层防御会被静默清空，全部放行、无提示、无告警。
**代价：** 同上（"防御被静默清空"本身就是代价）。
**把握度：** [读到]

**结论：** 没有针对无人值守场景的、有范围/有时限的预授权机制——只有标准 allowlist 或整体 `ask=off`。转发到聊天里的提示文案自己写明："Background mode note: non-interactive runs cannot wait for chat approvals; use pre-approved policy (allow-always or ask=off)"（`src/infra/exec-approval-forwarder.ts:283-286`）。
**代价：** 想跑无人值守任务的操作者，只能在"维护一份长期 allowlist（宽且持久）"和"整体关闭询问"之间选，没有"只批准这一批/这一次运行"的窄范围无人值守 token。
**把握度：** [读到]

**结论：** 对于"完全没有可用审批路由"的 headless/cron 场景，系统会给出明确解释性拒绝（区别于普通超时路径）：`shouldResolveExecApprovalUnavailableInline` 只在触发方式是 cron/headless 类且 `unavailableReason === "no-approval-route"` 时命中，给出具体拒绝原因和补救建议（`openclaw doctor`、`openclaw approvals get --gateway`）（`bash-tools.exec-host-shared.ts:372-401`）。但这条路径只覆盖"压根没配置审批客户端"这一种情况，不覆盖"配置了但 30 分钟没人回复"的普通超时路径。
**代价：** 降级后用户能不能事后知情，取决于具体走的是哪条分支——headless 场景有明确解释，普通超时场景没有。普通超时/`askFallback` 自动解决后，聊天侧的文案是固定模板（"Resolved by {resolvedBy}"或"Exec approval expired"），超时场景下 `resolvedBy` 始终是 `null`（`gateway/exec-approval-manager.ts:102,143-160`），措辞和真人批准/拒绝几乎一样——从审批频道本身很难分辨"是人点的 deny"还是"系统按 askFallback 自动决定的"，除非用户本来就知道要去查策略配置。
**把握度：** [读到]

## 时序

审批流程有四个会"等待"或"失败"的节点，以及失败后系统各自处于什么状态：

1. **等待人工决策**：请求进入 gateway 内存态 `Map`（`exec-approval-manager.ts:55`），带一个 30 分钟 `setTimeout`。等待期间，node host 一侧的原始 `system.run` 调用被挂起，agent 拿到一个审批 id 立即返回（`docs/tools/exec-approvals-advanced.md:162-164`）。
2. **超时无人响应**：`expire()` 把等待结果置为 `null`，`resolvedBy` 保持 `null`；随后交给 `askFallback` 分支决定 full/deny/allowlist 三选一（见切面 7、8）。系统状态：待处理记录被清空，聊天侧收到一条格式固定的过期提示。
3. **审批渠道完全不可达（无路由）**：headless/cron 触发时给出显式拒绝原因和补救建议（切面 8）；非 headless 场景下则退化为普通超时路径。
4. **批准后但请求已被篡改**：gateway 转发前用 `sanitizeSystemRunParamsForForwarding` 校验 argv/cwd/agentId/sessionKey/env-hash 与原始请求是否一致，不一致则直接拒绝转发（`node-invoke-system-run-approval.ts:116-324`，匹配逻辑 `node-invoke-system-run-approval-match.ts:26-54`）。系统状态：本次执行被拒绝，原始批准记录不会被复用到别的命令上。
5. **本地配置文件本身损坏（冷启动失败）**：见切面 4——不是"等待"或显式"失败"，而是静默重建为空状态并覆盖写回磁盘，用户唯一能观察到的现象是"之前配置的所有 allowlist 都消失了"，没有报错提示这次重建发生过。

## 明确不做什么

- 官方文档明确声明：exec approvals "reduce accidental execution risk, but are **not** a per-user auth boundary or filesystem read-only policy"，批准后的命令可以按所选主机/沙盒文件系统权限任意改写文件（`docs/tools/exec-approvals.md:59-60`）。
- 文件绑定是尽力而为，不是对所有解释器/运行时加载路径的完整语义建模；无法唯一确定绑定文件时直接拒绝签发批准，而不是假装覆盖了这种情况（`docs/tools/exec-approvals.md:62-63`；`docs/tools/exec-approvals-advanced.md:155-160`）。
- YOLO 模式下不会额外叠加一层启发式的"命令混淆检测"或脚本预检拒绝层——批准逻辑就是配置好的 host exec policy 本身，没有隐藏的兜底智能层（`docs/tools/exec-approvals.md:189`）。
- safe bins 的 argv 校验是纯 argv 形状判定，不做任何主机文件系统存在性检查，明确是为了避免造成"文件是否存在"的信息泄露（`docs/tools/exec-approvals-advanced.md:45-49`）。
- 没有找到专门的、独立于聊天转发消息之外的持久审批审计日志（切面 6，基于关键字检索的推断结论）。
- 在已阅读的匹配/生成流水线代码里，没有找到任何基于模型（LLM）判定来生成或泛化 pattern 的代码路径（切面 5 归类小结，基于未找到相关代码的推断）。

## 未确认项汇总

- **Control UI 的撤销粒度**：文档提到 Control UI 可以编辑/删除 allowlist 条目，是否比 CLI 的"按 pattern 整体删除"更细（比如支持只删某个 `argPattern` 组合）未核实。缺口：Control UI 前端源码不在 `src/infra` 范围内，需要另行定位并阅读。
- **按钮样式是否真的造成视觉误导**：`allow-always` 按钮样式为 `primary`、`allow-once` 为 `success`，但具体各聊天平台（Slack/Discord/Matrix 等）是否会让 `primary` 视觉上更突出未核实。缺口：需要阅读 `../interactive/payload.js` 及各渠道适配器渲染代码。
- **`ask=always` 下 `allow-always` 是否在实际 resolve 调用点被拒绝**：目前只确认了候选决策数组本身排除了 `allow-always`，没有追踪到实际处理审批回复的 handler 是否严格按此数组校验。缺口：需要阅读 `gateway/server-methods/exec-approval.ts` 的 resolve 处理逻辑。
- **shell 展开是否在任何地方被模拟**：在已读文件范围内没有发现"模拟真实 shell 展开 `$VAR`/花括号/通配符后再匹配"的代码，但未穷尽阅读 `shell-inline-command.ts`、`exec-wrapper-tokens.ts`、`executable-path.ts` 全文。缺口：需要完整阅读这三个文件确认。
- **是否存在更通用的应用级结构化日志记录审批事件**（不是专门的审计日志文件，而是普通操作日志里附带审批信息）：目前只在 `exec-approvals.ts`/`exec-approvals-allowlist.ts` 两个文件里检索了 "audit"/"log" 关键字，未检查是否存在独立的日志模块（如 `src/logging` 或类似目录）记录审批相关的结构化日志行。缺口：需要定位并检索日志模块。
- **大规模 allowlist 下线性扫描的实际性能影响**：源码里没有发现相关基准测试或性能测试，无法判断在几十条 vs 几千条 allowlist 条目规模下是否构成实际问题。缺口：需要查找是否存在专门的性能测试文件，或者以实际部署规模做压测。

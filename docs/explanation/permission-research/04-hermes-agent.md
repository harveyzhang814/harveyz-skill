# Hermes Agent 权限模块机制报告

## 元信息

- 分析对象：Hermes Agent（Python 项目）
- 版本：commit `81928f03ab5841362e526df011e3eb74159aea8b`
- 路线：纯源码（`~/Repositories/hermes-agent`）
- 分析日期：2026-08-19
- 分析覆盖的文件清单：
  - `tools/approval.py`（1258 行，全读）—— 危险命令检测、审批状态、审批 UX 的唯一实现
  - `tools/skills_guard.py`（933 行，全读）—— skill 安装期安全扫描 + trust_level 安装策略
  - `tools/terminal_tool.py`（部分：约 240-330 行、1600-1860 行、2270-2330 行）—— 审批的唯一调用点、`force` 参数、工具 schema
  - `acp_adapter/permissions.py`（80 行，全读）—— ACP 协议下的审批回调桥接
  - `gateway/session_context.py`（155 行，全读）—— 审批 session_key 的读取解析
  - `gateway/session.py`（约 580-651 行）—— `build_session_key` 的构造规则
  - `gateway/run.py`（约 14020-14100 行；另检索 `session_key=` 相关调用点）—— 网关侧审批通知与文本降级提示
  - `gateway/platforms/slack.py`（相关行号：647-650、2174-2451）—— 消息平台按钮式审批 UX
  - `hermes_cli/config.py`（相关行号：255-257、3978-4106、1200-1220 附近）—— `config.yaml` 路径与 `command_allowlist` 默认值
  - `hermes_cli/skills_hub.py`（相关行号：425、540-575、2660-2673）—— skill 安装 CLI 流程、审批策略调用点、审计日志写入
  - `tools/skills_hub.py`（相关行号：48-51、2660-2673）—— `AUDIT_LOG` 路径定义
  - `tools/skill_manager_tool.py`（相关行号：51-90 附近）—— agent 自建 skill 的 guard 开关（默认关闭）
  - `hermes_state.py`（全文关键词检索，无匹配）—— 确认 `state.db` 不涉及审批持久化
  - `website/docs/user-guide/security.md`（全文，作为源码之外的官方文档佐证，标注为辅助来源，不作为一手证据）
  - 命令行检索确认的负向证据：`cli.py`、`run_agent.py`、`hermes_state.py` 中均无 `trust_level` 或审批持久化引用

## 定位

Hermes Agent 的"权限/审批"实际上是**两套完全独立、互不感知的系统**：

1. **危险命令审批（`tools/approval.py`）**：运行时拦截，只作用于 `terminal` 这一个工具的命令字符串，基于约 30 条固定正则模式做类别匹配，决定是否需要用户在本次调用前点头。
2. **Skill 安装期扫描（`tools/skills_guard.py`）**：静态扫描，只在"从注册表安装一个 skill"这个动作发生时跑一次，基于源头身份（`trust_level`）+ 扫描结果（`verdict`）查一张二维策略表决定 allow/block/ask。

`trust_level` 体系完全属于第二套系统，只出现在 skill 安装相关文件（`tools/skills_guard.py`、`tools/skills_hub.py`、`hermes_cli/skills_hub.py`）中；在 `run_agent.py`（主循环，14672 行）、`tools/approval.py`、`hermes_state.py` 中检索均无 `trust_level` 引用 `[读到]`（negative grep across 全仓库）。两套系统没有共享的状态存储、没有共享的决策函数，也没有交叉引用。

危险命令审批本身也是"薄"的：只挂在 `terminal` 工具上。检索 `check_all_command_guards`/`check_dangerous_command`/`from tools.approval` 在 `tools/*.py` 中的引用，只有 `tools/terminal_tool.py` 一处消费方 `[读到]`（`tools/terminal_tool.py:317-325`）。`execute_code`、文件写入类工具、MCP 工具调用、浏览器/网页工具均不经过这套审批——它们各自有独立、不重叠的防护机制（环境变量过滤、SSRF 域名黑名单等，见 `website/docs/user-guide/security.md:421-517`，这部分未逐行核对源码，标注 `[未查]`，仅作为存在性线索）。

## 架构

```
LLM 决定调用工具
  v
run_agent.py::_execute_tool_calls_concurrent (行 9784)  -- 通用工具分发
  v
tools/registry.py 按工具名查表，转发到具体工具的 handler
  v
tools/terminal_tool.py::_handle_terminal -> terminal_tool()
  v
若 force!=True (LLM 不可控制此参数, 见八/1):
  tools/terminal_tool.py:1831  approval = _check_all_guards(command, env_type)
  v
tools/approval.py::check_all_command_guards()
  1. 容器后端(docker/singularity/modal/daytona/vercel_sandbox) -> 直接放行,不检测
  2. HARDLINE_PATTERNS 匹配 -> 无条件拒绝(yolo/off/cron-approve都压不过)
  3. --yolo / /yolo / approvals.mode=off -> 放行(但已过 hardline 关卡)
  4. is_cli / is_gateway / is_ask 均为假 且非 cron -> 直接放行,不做后续检测(见八)
  5. tirith 内容扫描 + DANGEROUS_PATTERNS 正则匹配 -> 收集 warnings
  6. approvals.mode=smart -> 辅助 LLM 判定 approve/deny/escalate
  7. 手工审批 prompt (CLI阻塞input / 网关阻塞队列+回调)
  v
批准 -> 按 once/session/always 写回状态 -> 命令真正执行
```

skill 安装是完全独立的一条链路，不经过上图：

```
hermes skills install <id>  (hermes_cli/skills_hub.py:425 附近)
  v
scan_skill(path, source)  tools/skills_guard.py:599
  v
_resolve_trust_level(source) -> builtin|trusted|community|agent-created
  v
should_allow_install(result)  查 INSTALL_POLICY 表 -> allow/block/ask(None)
  v
append_audit_log(...)  写入 skills/.hub/audit.log
```

## 八切面

### 1 拦截点

结论：拦截发生在具体工具实现函数内部（`tools/terminal_tool.py:1830-1831`），紧挨着"创建/复用执行环境"之后、"把命令交给后端环境执行"之前；不是在通用工具分发层（`run_agent.py:9784` 的 `_execute_tool_calls_concurrent`）统一拦截，因此其他工具完全不经过这层检查。

拦的对象是**整条命令字符串**（`command` 参数原文，经 ANSI 剥离 + Unicode NFKC 归一化 + 小写化后拿去做正则匹配，`tools/approval.py:329-344`），不是"工具名"，也不是结构化参数——它不解析 shell 语法，只在归一化后的字符串上做子串/正则搜索（`tools/approval.py:347-358`, `920-940`）。

谁不信任谁：系统不信任 LLM 生成的 shell 命令内容本身，信任"用户在提示出现时给出的实时确认"。执行环境是否被信任由 `env_type` 决定——容器类后端（docker/singularity/modal/daytona/vercel_sandbox）被判定为足够隔离，整个审批检查直接跳过（`tools/approval.py:805-806`, `930-931`），信任的是容器边界而非命令内容。

有一个关键的信任缺口：`terminal_tool()` 暴露 `force: bool = False` 参数，文档明确写"internal only, not exposed to model API"（`tools/terminal_tool.py:1637, 1667`），且 `TERMINAL_SCHEMA`（`tools/terminal_tool.py:2276-2318`）与 `_handle_terminal`（`tools/terminal_tool.py:2321-2330`）均不包含/不读取 `force` 字段——`[读到]` LLM 通过工具调用 API 确实无法设置它。但在本次读取范围内，全仓库检索 `force=True` 也**没有找到任何内部调用点**把 `terminal_tool(force=True)` 用起来（`[读到]`，grep 覆盖 `run_agent.py`、`tools/`、`gateway/`、`acp_adapter/`）——即这个绕过通道当前处于"存在但未使用"的死代码状态，去向不明。`[未查]`：是否在某个未检索到的调用路径（如批处理脚本、测试 harness）中被实际触发。

代价：审批逻辑与工具实现耦合在一起，意味着任何新增的、能执行副作用的工具（写文件、调用外部 API、执行代码）默认不经过这层检查，除非该工具的作者主动照抄一份类似逻辑——这是一种"opt-in 式安全"，容易随着工具数量增长而出现遗漏。

### 2 决策单元

结论：一次"同意"作用于**一个正则模式匹配到的类别描述**（如 `"recursive delete"`、`"delete in root path"`），不是一次具体调用，也不是具体的资源路径/参数。`DANGEROUS_PATTERNS`（`tools/approval.py:226-292`）共 ~30 条 `(pattern, description)` 二元组，`description` 字符串本身就是审批状态的索引 key（`pattern_key`，见 `detect_dangerous_command`, `tools/approval.py:347-358`）。approve 一次"recursive delete"，覆盖的是**所有**未来匹配到同一正则的命令，无论目标路径是什么。

默认级别：手动模式（`approvals.mode: manual`，`hermes_cli/config.py` 中 `_normalize_approval_mode` 默认落到 `"manual"`，`tools/approval.py:690-702, 716-719`）——每次匹配都要问一次，没有默认自动放行的粒度。用户在每次提示里可以选 4 档中的一档来"升级"作用范围：`once`（仅这次）→ `session`（本会话内该模式免问）→ `always`（永久写入 `config.yaml`）；没有"降级"操作（见切面 6）。

代价：决策单元是"类别"而非"这一次调用"或"这一个资源"，选 `always` 相当于给整台机器上所有会话、所有项目的"recursive delete"类命令开永久绿灯——用户以为自己批准的是"这一次删 `/tmp/x`"，实际批准的是"以后任何 `rm -r` 形态的命令都不再问"，粒度错配的风险集中在这一步。

### 3 生命周期

结论：
- `once`：仅本次调用生效，不写入任何状态。
- `session`：写入进程内存中的 `_session_approved: dict[str, set]`（`tools/approval.py:367`），按 `session_key` 分桶，寿命等于**当前 Python 进程的存活时间**——没有过期时间、没有升迁触发器，纯粹是"进程活着就有效，进程退出就清空"。`clear_session()`（`tools/approval.py:482-495`）可在会话边界主动清空并把队列中未决的审批全部标记为 `deny`。
- `always`：写入 `_permanent_approved: set`（内存）并同步落盘到 `config.yaml` 的 `command_allowlist`（`tools/approval.py:525-534, 560-568`），没有过期时间、没有自动降级路径——只能靠人工编辑 `config.yaml` 删除。

层级升迁完全由**用户在提示里选择的选项**触发（`o/s/a/d` 四选一），系统不会自动把 `session` 提升为 `always`，也不会有内置逻辑做反向降级。

重启/resume/换机分别丢什么：
- **同机重启进程**：`session`/`once` 全部丢失（纯内存字典，模块重新 import 后 `_session_approved = {}`，`tools/approval.py:367`）；`always` 保留，因为进程启动时会执行 `load_permanent_allowlist()`（模块级调用，`tools/approval.py:1258`）从 `config.yaml` 重新灌入内存。
- **resume 同一会话**（例如网关重连同一对话）：即使 `build_session_key()`（`gateway/session.py:594-651`）会为同一个 platform/chat/thread/user 组合确定性地生成同一个 `session_key` 字符串，只要进程重启过，`_session_approved` 已被清空——`session` 级批准不会因为"session_key 相同"而复活。
- **换机**：`session`/`once` 天然不跨机；`always` 只有在用户手动把 `~/.hermes/config.yaml`（或整个 `HERMES_HOME`）搬到新机器时才会带过去，否则从零开始。

代价：`session` 与用户直觉中的"会话"概念脱节——尤其在纯 CLI 模式下，`get_current_session_key()` 默认回落到硬编码字符串 `"default"`（`tools/approval.py:72-84`，`cli.py` 全文检索未发现任何 `HERMES_SESSION_KEY` 赋值，即 CLI 从不设置这个 env/contextvar），意味着同一进程内所有 CLI "会话"共享同一个批准桶；这既可能造成"我以为换了个话题就该重新问"的困惑，也可能造成"进程一直不退出，批准状态越攒越多、永不清理"的另一面问题。

### 4 持久化与作用域

结论：
- 存储介质只有一个：`~/.hermes/config.yaml`（更准确地说是 `get_hermes_home() / config.yaml`，`hermes_cli/config.py:255-257`）里的 `command_allowlist` 列表字段，只承载 `always` 级批准。`session`/`once` 完全不落盘，纯内存。
- 索引 key 就是 `pattern_key`（即 `DANGEROUS_PATTERNS` 里的英文描述字符串，如 `"recursive delete"`），另外保留一套"legacy key"兼容别名机制（`_legacy_pattern_key`、`_PATTERN_KEY_ALIASES`，`tools/approval.py:302-323`）用于兼容旧版本用正则片段做 key 的历史数据。索引 key **不包含**会话、用户、项目、路径信息——`always` 列表是一个扁平集合，没有任何作用域字段。
- 作用域：`always` 是**整个 `HERMES_HOME` 实例级**共享——同一台机器上跑的所有 CLI 会话、所有网关平台（Telegram/Discord/Slack/...）的所有用户、所有项目目录，只要用的是同一个 `~/.hermes/`，就共享同一份 `command_allowlist`。`[推断]`：推导链条——`load_config()`/`save_config()` 读写的是单一 `config.yaml` 路径（`hermes_cli/config.py:3978, 4106`），而 `check_all_command_guards` 判断"是否已批准"时用的 `is_approved(session_key, pattern_key)`（`tools/approval.py:511-522`）虽然接收 `session_key` 参数，但对 `_permanent_approved` 的检查完全不看 `session_key`（`tools/approval.py:519`：`if any(alias in _permanent_approved for alias in aliases)`），说明 `always` 批准与"谁批准的、在哪个会话批准的"无关。
- `~/.hermes/state.db`（`hermes_state.py`）：全文检索 `approval`/`allowlist` 关键词无任何匹配 `[读到]`——确认 state.db 只存 session/message/tool-call 历史（`hermes_cli/config.py:1332-1333` 注释印证），与审批持久化无关，任务描述中提到的这个文件不是本系统的证据源。
- 冷启动重建：进程启动时模块级代码 `load_permanent_allowlist()`（`tools/approval.py:1258`）执行 `load_config()` 读取 `config.yaml`，若读取失败会 `logger.warning` 后返回空 set（`tools/approval.py:542-557`）——即**失败静默降级为"没有任何永久批准"，而不是报错阻断启动**，进程继续跑，只是之前攒的 `always` 白名单全部形同虚设，用户不会收到任何提示。

代价：`always` 批准的作用域粒度是"整台机器/整个 HERMES_HOME"，而不是"这个项目"或"这个用户"——在一台跑多平台网关、服务多个消息用户的 Hermes 实例上，任何一个用户在任意会话里把某个危险模式点了"always"，会立刻对所有其他用户的所有会话生效，且没有告警。`config.yaml` 解析失败时静默清空永久白名单，也意味着"曾经点过 always"这件事可能在配置文件损坏后无声消失，用户毫无感知地退回到每次都要问的状态。

### 5 泛化与匹配

结论：泛化档位是**固定正则模式库**（枚举式，非可配置 DSL、非模型判定的默认路径），落在"结构化 pattern"和"精确类别匹配"之间偏向前者：`DANGEROUS_PATTERNS`（`tools/approval.py:226-292`，约 30 条）和更严格的、不可绕过的 `HARDLINE_PATTERNS`（`tools/approval.py:156-178`，约 12 条）都是硬编码正则，不支持用户自定义扩展匹配规则（只能整条命令字符串级别的"是否命中"判断，命中后的 key 就是这条规则的固定描述）。

归一化规则（`_normalize_command_for_detection`，`tools/approval.py:329-344`）：
- 剥离 ANSI 转义序列
- 剥离空字节
- Unicode NFKC 归一化（防全角字符绕过）
- 全字符串转小写后做 `re.IGNORECASE` 匹配（双重保险，其实冗余）

**不做**的归一化：不解析/不展开 shell 语法（不识别 `&&`/`;`/管道之外的语义、不识别子 shell、不展开变量），不解析复合命令的独立子命令边界（好处是正则 `.search()` 天然能在整条字符串任意位置命中，所以 `safe_cmd && rm -rf /tmp/x` 这种复合命令依然会被命中；坏处见下），不做符号链接解析，不做相对路径到绝对路径的归一化，不做 shell 变量展开后再匹配。

已知绕过路径与对应防护（`[读到]`，源码注释直接承认）：
- `tools/approval.py:267-272` 的注释明确写道：`kill -9 $(pgrep -f hermes)` 这种通过命令替换（`$(...)`）间接拼出目标名的写法，对正则是"opaque"（不透明）的——常规按名字匹配的模式（`pkill|killall.*hermes`）抓不到，团队是针对这一个具体案例**追加了一条结构性正则**（`kill.*\$\(\s*pgrep\b`）来补丁，而不是解决"动态拼接绕过正则"这个根问题。这说明系统对"变量/命令替换构造出的危险字符串"存在结构性盲区，目前的应对策略是逐案例打补丁，不是通用防御。
- `approvals.mode: smart` 引入辅助 LLM 做风险判定（`_smart_approve`, `tools/approval.py:743-787`）：这条路径本身就是一个新的攻击面——LLM 的判定基于命令文本，如果命令文本或上下文中含有针对这个"安全审查 LLM"的提示注入（例如伪装成"这只是打印 hello world"的说明性文字），有被误判为 `APPROVE` 的风险；`[推断]`：推导链条——`_smart_approve` 的 prompt 模板（`tools/approval.py:755-767`）把原始命令和检测理由原样拼进去发给辅助模型，没有任何针对该输入做的注入防护提示或结构化隔离，属于典型的"用 LLM 审查 LLM 输出"的自指风险，源码没有专门的缓解措施。

代价：正则库覆盖的是"作者能想到的危险命令写法"，天然滞后于攻击面（新的 shell 特性、新的 LLM 生成的隐蔽写法都可能不在列表里）；`smart` 模式用 LLM 兜底"是否误报"，但没有反过来加固 LLM 判定本身抗提示注入的能力，等于用一个可被操纵的判定者去放行另一个可能被操纵的执行者。

### 6 撤销与可审计

结论：
- **撤销粒度 vs 批准粒度**：不对称。批准可以细到"once"（单次不留痕），但撤销**没有专门的命令**——文档承认只能靠 `hermes config edit` 手工打开编辑器改 `config.yaml`（`website/docs/user-guide/security.md:185-187`，辅助来源）。源码检索确认 `command_allowlist` 在全仓库只有写入/读取两处逻辑（`tools/approval.py:551, 565`），没有任何 `remove`/`revoke` 函数 `[读到]`（grep `command_allowlist` 全仓库无第三个使用点）。`session` 级批准可以被 `clear_session()`（`tools/approval.py:482-495`）整体清空，但这是"清空整个会话的所有批准"，不是"撤销某一条"。
- **可视化**：没有找到任何"列出我已经批准了什么"的命令或 UI 入口 `[未查]`——检索范围内（`hermes_cli/main.py`、`hermes_cli/config.py`、`tools/approval.py`）未发现专门的 `hermes approvals list` 之类命令；用户想知道现状只能直接读 `config.yaml` 的 `command_allowlist` 字段原文。
- **误批一条过宽规则的恢复路径**：手工从 `command_allowlist` 数组里删掉对应字符串，保存后**需要重启进程**——因为 `_permanent_approved` 只在模块 import 时通过 `load_permanent_allowlist()`（`tools/approval.py:1258`）读取一次，没有热重载逻辑 `[推断]`：推导链条——`load_permanent`/`load_permanent_allowlist` 均无被 watch/reload 触发器调用的迹象（仅在模块顶层调用一次）。
- **审计日志**：危险命令审批这条路径**没有内置持久化审计日志**。`_fire_approval_hook`（`tools/approval.py:36-58`）会在审批请求/响应前后触发 `pre_approval_request`/`post_approval_response` 两个插件钩子，但这是"opt-in"机制——检索 `plugins/` 目录下所有 Python 文件，没有一个内置插件订阅这两个钩子 `[读到]`（`grep -rln "pre_approval_request|post_approval_response" plugins/` 返回空）。也就是说默认安装下，一条危险命令被谁在什么时候批准/拒绝，除了进程日志里零散的 `logger.warning`/`logger.debug` 调用（无结构化字段、无固定落盘位置声明），没有任何专门记录。

与此形成鲜明对比的是 **skill 安装审批有审计日志**：`append_audit_log()`（`tools/skills_hub.py:2660-2673`）把每次 `BLOCKED`/其他动作以时间戳+trust_level+verdict 格式追加写入 `skills/.hub/audit.log`（路径定义 `tools/skills_hub.py:48-51`）。两套系统在"可审计性"上完全不对等。

代价：危险命令审批这条主干路径在默认安装下是"批了就批了，事后查不到是谁在什么时间批的"——出问题排查时只能翻进程日志盲找，且撤销一条过宽规则需要手工编辑配置文件并重启进程，运维成本不低;而这恰恰是最需要审计的一层(命令执行权限)反而是两套系统里审计能力较弱的一套。

### 7 审批 UX

结论：
- **CLI**：`prompt_dangerous_approval()`（`tools/approval.py:575-687`）打印描述 + 完整命令原文，给出 `[o]nce | [s]ession | [a]lways | [d]eny` 四选项（`website/docs/user-guide/security.md:151`，与源码的分支逻辑一致：`tools/approval.py:664-678`），**默认选中项是 deny**——任何非 `o/once/s/session/a/always` 的输入（包括空输入、无法识别的字符）都落到 `else` 分支返回 `"deny"`（`tools/approval.py:676-678`）。超时（默认 60 秒，`_get_approval_timeout`, `tools/approval.py:722-727`）同样判定为 `deny`（`tools/approval.py:659-661`）——fail-closed。当同时存在 tirith 内容级发现时，`allow_permanent` 被置 False，`[a]lways` 选项被隐藏，用户选 `always` 也会被静默降级为 `session`（`tools/approval.py:670-674`），理由是"内容级安全发现不适合永久放行"。
- **网关/消息平台**：优先走按钮式 UI（如果适配器实现了 `send_exec_approval`，例如 Slack `gateway/platforms/slack.py:2202-2221` 提供 Approve Once / Approve Session / Always Approve / Deny 四个按钮，与 CLI 四选项一一对应）；否则降级为纯文本提示，展示命令预览（超过 200 字符截断，`gateway/run.py:14079`）+ 原因 + 回复关键词说明（`gateway/run.py:14080-14086`）。回复 `yes/y/approve/ok/go` 记为批准，`no/n/deny/cancel` 记为拒绝（`website/docs/user-guide/security.md:167-168`，辅助来源，源码层面的关键词映射未逐字核对，标注 `[未查]`）。超时默认 300 秒（`gateway_timeout` 配置项，`tools/approval.py:1110`），超时/未解析同样判定为拒绝（`tools/approval.py:1167-1174`）。
- **批量审批**：`/approve all` 会一次性 resolve 掉该 session 队列里**所有**未决的审批条目（`resolve_gateway_approval(..., resolve_all=True)`，`tools/approval.py:419-445`），批量呈现方式只是"全部按同一个选择处理"，没有逐条展示细节的批量视图。

代价：CLI 与网关两条 UX 路径的选项集合、语义高度一致，但网关文本降级路径依赖用户记住自由格式的回复关键词（而不是强约束的按钮），存在误操作或适配器不支持按钮时体验劣化的风险；`/approve all` 一次性放行整个队列，在并发多个 subagent/后台命令同时触发审批时，容易让用户在没有逐条看清楚每条命令的情况下一次性放行一批不同性质的危险操作。

### 8 无人值守降级

结论：这是本系统最反直觉的一处。`check_all_command_guards`（`tools/approval.py:948-971`）的判断顺序是：

```python
is_cli = os.getenv("HERMES_INTERACTIVE")
is_gateway = os.getenv("HERMES_GATEWAY_SESSION")
is_ask = os.getenv("HERMES_EXEC_ASK")

# Preserve the existing non-interactive behavior: outside CLI/gateway/ask
# flows, we do not block on approvals and we skip external guard work.
if not is_cli and not is_gateway and not is_ask:
    if os.getenv("HERMES_CRON_SESSION"):
        if _get_cron_approval_mode() == "deny":
            ... return 拒绝 ...
    return {"approved": True, "message": None}
```

即：只要进程既不是"交互式 CLI/ACP"（`HERMES_INTERACTIVE`）、也不是"网关会话"（`HERMES_GATEWAY_SESSION`）、也不是显式要求"询问"（`HERMES_EXEC_ASK`），也不是 cron 任务（`HERMES_CRON_SESSION`），就**直接放行**——连 tirith 内容扫描和 `DANGEROUS_PATTERNS` 正则检测本身都不会运行（这两步在函数体里位于这个判断之后，`tools/approval.py:973-985`）。源码注释自己承认这是"preserve the existing non-interactive behavior"——即以库/脚本方式调用 agent 时（既非四种已知模式），fail-safe 是**朝"放行"倒**，唯一仍然生效的是无条件的 `HARDLINE_PATTERNS`（在函数更早处检查，`tools/approval.py:937-940`，先于这个判断）。这个同样的分支逻辑在旧版 `check_dangerous_command()` 里重复了一遍（`tools/approval.py:831-848`），说明是有意为之的设计而非疏漏。

对于识别为 cron 的会话：`_get_cron_approval_mode()`（`tools/approval.py:730-741`）读取 `approvals.cron_mode` 配置，默认值是 `"deny"`（`tools/approval.py:735`，`default="deny"`），即 cron 任务默认 fail-closed，需要显式设置 `approvals.cron_mode: approve` 才会放行。这里 fail-safe 朝"拒绝"倒，与上面"既非四种模式"的默认放行方向恰好相反。

预授权机制：`command_allowlist`（`always` 级永久白名单）本身就是唯一的预授权手段——无人值守场景下，唯一能让危险命令免于每次询问的方式是提前手动把对应模式加进 `config.yaml`。

降级后用户事后如何知情：`[未查]`。cron 拒绝分支会把拒绝原因写进返回给 agent 的消息（`tools/approval.py:840-847`），但这条消息只进了 agent 的工具调用结果，不保证会被转发给人类用户；对于"既非四种模式因而被静默放行"的路径，没有找到任何通知/日志机制会告诉用户"这条命令跳过了审批直接执行了"——`[未查]`，缺口在于没有检索到覆盖这条分支的告警埋点，需要去 `logger` 调用点逐一确认是否有针对这个具体分支的日志（本次检索范围内该 `if` 分支内部除 cron-deny 外没有任何 `logger.*` 调用）。

代价：这个"既非 CLI/网关/ask/cron 即放行"的分支意味着——任何以库方式导入 `run_agent`/直接跑 `terminal_tool()`、或者新写的运行模式忘记设置这四个环境变量之一的调用方，会在不知情的情况下让危险命令检测整体失效（只剩 hardline 兜底），且没有日志明确提示"本次调用跳过了审批"。这是一个默认值方向不一致的设计（cron 默认拒绝，其它未分类场景默认放行），对于二次开发或将 Hermes 作为库嵌入的场景是一个容易被忽略的坑。

## 时序

以 CLI 交互式场景为例，一条命中 `DANGEROUS_PATTERNS` 的命令的典型时序：

```
用户 -> LLM: 自然语言请求
LLM -> run_agent.py: 决定调用 terminal 工具, command="rm -rf /tmp/build"
run_agent.py -> tools/terminal_tool.py: terminal_tool(command=..., force=False)
terminal_tool -> tools/approval.py: check_all_command_guards(command, env_type="local")
  approval.py: hardline 检测 -> 未命中, 继续
  approval.py: yolo/off 检测 -> 未开启, 继续
  approval.py: is_cli=True (HERMES_INTERACTIVE=1) -> 进入审批流程
  approval.py: tirith 扫描 -> action=allow
  approval.py: DANGEROUS_PATTERNS 匹配 -> 命中 "recursive delete"
  approval.py: is_approved(session_key="default", "recursive delete") -> False (首次)
  approval.py: approvals.mode=manual -> 走人工 prompt
  approval.py -> 终端: 打印命令+描述+四选项, input() 阻塞等待(超时60s)
  用户 -> approval.py: 输入 "s" (session)
  approval.py: approve_session("default", "recursive delete") 写入内存 _session_approved
  approval.py -> terminal_tool: {"approved": True}
terminal_tool -> 环境后端: 实际执行 rm -rf /tmp/build
terminal_tool -> run_agent.py: 返回 stdout/exit_code
```

同一进程内、同一 `session_key`("default")下，第二次出现"recursive delete"类命令：`is_approved` 直接命中内存里的 `_session_approved["default"]`，不再弹提示，直到进程退出。

## 明确不做什么

- 不对"这一次调用"做单独的、比"类别正则"更细的资源级或参数级授权——没有"只允许删除 `/tmp/` 下的文件"这种带条件的批准。
- 不对 `terminal` 之外的任何工具（`execute_code`、文件写入、MCP 工具、浏览器/网页工具等）套用同一套危险命令审批逻辑——各自独立设防，互不共享这套状态。
- 不做 shell 语法解析/复合命令拆分/变量展开后再匹配——纯字符串正则匹配，承认存在通过命令替换等方式构造出的检测盲区（`tools/approval.py:267-272` 注释自认）。
- 不提供撤销单条永久批准的专用命令——只能手工编辑 `config.yaml`。
- 不提供"查看我已批准了什么"的可视化列表命令。
- 危险命令审批路径不提供默认开启的持久化审计日志——`pre_approval_request`/`post_approval_response` 钩子存在但默认无订阅者。
- `trust_level` 体系不参与运行时工具调用审批，只参与 skill 安装这一个动作；agent 自建 skill 默认不经过 `trust_level` 扫描（`skills.guard_agent_created` 默认 `False`）。
- 不对"既非交互 CLI/网关/ask/cron"的调用模式做危险命令检测（只保留 hardline 兜底）——这是源码注释明确承认的既有行为，不是遗漏。

## 未确认项汇总

- `terminal_tool(force=True)` 在本次检索范围内没有找到任何调用点，其真实用途/是否在未检索到的路径（测试 harness、外部脚本）中被触发，`[未查]`。
- 网关文本降级路径的自由格式关键词（`yes/y/approve/ok/go` 等）与 `deny` 一侧的完整正则/关键词列表未在源码层面逐字核对，仅依据 `website/docs/user-guide/security.md:167-168` 转述，`[未查]`，需要去 `gateway/run.py` 中处理 `/approve`、`/deny` 文本回复的具体解析函数核实。
- "既非 CLI/网关/ask/cron 即放行"分支执行后，是否有任何面向用户的事后可见记录（日志埋点、通知），本次检索在该分支内部未发现 `logger.*` 调用，`[未查]`，需要确认是否在更上层调用栈（如 `run_agent.py` 的工具调用结果记录）有间接留痕。
- `tools/tirith_security.py` 的具体扫描逻辑（homograph URL、pipe-to-interpreter 检测规则细节）未展开阅读，只读取了它在 `check_all_command_guards` 中的调用方式和返回结构，`[未查]`。
- `acp_adapter/permissions.py` 的 `AllowedOutcome`/`PermissionOption` 与 ACP 协议本身的完整选项集合（是否支持 session 级批准的等价物）未核实——当前实现只映射了 `allow_once`/`allow_always`/`reject_once`/`reject_always` 四种，`allow_always` 直接映射到 hermes 的 `"always"`（永久写入 config.yaml），跳过了 `"session"` 这一档，`[读到]`（`acp_adapter/permissions.py:18-23`），但 ACP 客户端侧是否还有其它未在这里体现的选项种类未核实。

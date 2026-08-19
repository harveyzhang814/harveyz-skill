# Codex CLI 权限模块机制报告

## 元信息

- 分析对象：`openai/codex`（官方开源 Codex CLI，Rust workspace，`codex-rs/`）
- 路线：半黑盒。上游源码 **可达**，已 `git clone --depth 1` 到 scratchpad 目录。
  - commit hash：`3b45c29062ff0e76e71c91b6753290400e7fa8da`（clone 时刻，本地系统时间 2026-08-19，仓库对应提交时间戳同为 2026-08-19 18:01:14 +0000 —— 注意这是浅克隆得到的默认分支最新提交，非固定 release tag）
  - 本地 `codex` 可执行文件（`/opt/homebrew/bin/codex`，npm 包 `@openai/codex` 安装）在本机实测时报 `ENOENT`（vendor 二进制缺失），因此【实测】渠道仅限本地状态文件只读检查，无法跑 `codex --help`。这不影响源码/文档渠道的把握度。
  - 版本skew 提示：源码中读到的部分机制（`Granular` 审批策略、`Guardian`/`approvals_reviewer = AutoReview` 自动审阅、`PermissionProfile`）在官方公开文档（`developers.openai.com/codex/*`，实际渲染于 `learn.chatgpt.com/codex/*`）中要么未提及要么只提了名字未展开，说明源码 main 分支比公开稳定文档新，本报告以源码为准，官方文档仅作交叉印证。
- 依据来源清单：
  - 源码（`codex-rs/protocol`、`codex-rs/config`、`codex-rs/core`、`codex-rs/execpolicy`、`codex-rs/exec`、`codex-rs/cli`、`codex-rs/tui`）
  - 本地状态实证：`~/.codex/config.toml`、`~/.codex/rules/default.rules`、`~/.codex/history.jsonl`、`~/.codex/session_index.jsonl`、`~/.codex/.codex-global-state.json`（均只读）
  - 官方文档：`developers.openai.com/codex/security`（重定向至 `learn.chatgpt.com/docs/security`）、`learn.chatgpt.com/codex/agent-approvals-security`、`learn.chatgpt.com/codex/sandboxing`
  - 实测：仅 `~/.codex/` 目录结构与文件内容只读查看；`codex --help` 因二进制缺失失败，未执行任何会改变状态的 codex 子命令
- 分析日期：2026-08-19

## 定位

Codex CLI 是本地运行的 Rust coding agent。权限/审批模块分两条独立但互相嵌套的机制：

1. **信任域（trust_level）**：以“项目绝对路径”为 key，持久化在 `~/.codex/config.toml` 的 `[projects."<path>"]` 表里，只有两个取值 `trusted` / `untrusted`。它的作用范围很窄——只决定**该项目自己的 `.codex/` 目录（项目级 config.toml、hooks、exec policy 规则文件）要不要被加载**，不直接参与"这条命令要不要问用户"的判断。
2. **逐次审批（approval_policy + sandbox_policy + exec-policy 规则引擎 + 会话级缓存）**：每次工具调用（shell/apply_patch/MCP tool/network/request_permissions）在执行前统一走 `Session::request_approval`，由 hooks → Guardian（自动审阅）→ 用户交互 三级依次尝试给出裁决。

这两条线不是同一个"审批系统"的两级，而是**"能不能加载自定义规则"和"要不要问人"两个正交问题**，见下节。

## 架构

```
用户输入 / 模型产出的工具调用（shell, apply_patch, MCP tool, network, request_permissions）
        |
        v
+----------------------------------------------------------+
| 配置加载阶段（进程启动 / cwd 变化时）                        |
| - 按 cwd 解析 project_root / git repo_root                 |
| - 查 config.toml 里的 trust_level（projects.<path>）        |
| - trusted  -> 加载该项目 .codex/config.toml + hooks + rules |
| - untrusted / 未设置 -> 该项目层被 disabled，跳过上述三者     |
| - 全局 ~/.codex/rules/*.rules 始终加载（不受本项目信任影响）  |
+----------------------------------------------------------+
        |
        v  （每次工具调用）
+----------------------------------------------------------+
| Session::request_approval                                 |
| 1. Hooks（配置里定义的程序化 allow/deny）                    |
| 2. strict_auto_review 或                                    |
|    (approval_policy in {OnRequest, Granular}                |
|     且 approvals_reviewer == AutoReview)                     |
|      -> Guardian（自动审阅，本质是另一个 LLM 评审请求）        |
| 3. 否则 -> 交互式问用户                                      |
+----------------------------------------------------------+
        |
        v
  before-answer 阶段还会查:
  - 会话内 ApprovalStore（exact-match 缓存，进程内存，不落盘）
  - exec-policy 规则引擎（prefix_rule allow/reject/prompt）
  - sandbox 是否已经能兜底（工作区可写根、网络策略）
        |
        v
   AutoApprove / AskUser(Guardian或人) / Reject
        |
        v
   实际执行落在 sandbox 内（seatbelt/bwrap/Windows sandbox/ExternalSandbox/DangerFullAccess 之一）
```

信任域只出现在最上面的"配置加载阶段"；下面的"每次工具调用"阶段完全不读 trust_level（全仓库 grep `core/src` 排除 `config/` 子目录，无一处业务逻辑读取 `trust_level` 或 `active_project`，见未确认项/证据部分）。

## 信任域与逐次审批的关系

结论：**分层，且信任域只管"能不能有自定义规则"，逐次审批管"这次要不要问"，二者不替代。**

- `TrustLevel` 只有 `Trusted`/`Untrusted` 两个值（`codex-rs/protocol/src/config_types.rs:623-626`）。`[读到]`
- 信任域被读取的唯一业务含义：项目层 config 是否被 disable。`disabled_reason_for_decision`（`codex-rs/config/src/loader/mod.rs:1056-1074`）在非 Trusted 时返回一条禁用原因，字符串明确写死 `gated_features = "project-local config, hooks, and exec policies"`。`[读到]`
- exec-policy 规则加载函数 `load_exec_policy` 明确注释：“Disabled project layers already represent the trust decision, so hooks and exec-policy loading can reuse the normal trusted-layer view.”（`codex-rs/core/src/exec_policy.rs:650-671`）。即项目自己 `.codex/rules/*.rules` 只有在该项目 Trusted 时才会被解析进最终 Policy；用户级 `~/.codex/rules/*.rules` 不受这个门槛影响，始终加载。`[读到]`
- approval_policy 的判断逻辑（`AskForApproval` 枚举、`Session::request_approval`、`assess_patch_safety`）不读取 `trust_level`/`active_project` 任何字段——全仓库对 `core/src`（排除 `config/`）按 `trust_level|active_project` 搜索命中为零。`[读到]`（否定性证据：搜索范围内未见引用）
- 因此：把一个项目标 `trusted` 之后，**逐次审批（approval_policy 决定的“问不问用户”这条链路）仍然照常发生**——trusted 只是打开了"这个项目现在可以自己在 `.codex/config.toml` 里把 `approval_policy` 设成 `never`、往 `.codex/rules/` 里加 `prefix_rule` 白名单"的**能力**，真正减少打扰的是这些被解锁的项目级配置本身，而不是 `trusted` 这个标签直接生效。可以理解为：`trusted` 是"允许你自己决定要不要少问"的开关，不是"少问"本身。`[推断]`（由上面三条 `[读到]` 证据直接推导：trust 只影响 config 层加载，config 层里才装着 approval_policy/rules，approval 执行路径不读 trust）

代价：这个设计把"信任一个目录"和"这个目录以后不再打扰我"两件事在心智模型上强行拆开了。产品经理/用户很容易把"标 trusted"直接理解成"以后这个项目不再问我"，但实际上如果项目没有在 `.codex/config.toml` 里显式把 `approval_policy` 调宽，标 trusted 后该问还是问——这是一次典型的"用户预期 vs 实现"错位，容易被当作 bug 反馈（"我明明信任了这个项目为什么还一直问我"）。

## 八切面

### 1 拦截点

- 拦截发生在核心会话层的 `Session::request_approval`（`codex-rs/core/src/tools/approvals.rs:484-547`），在具体工具执行**之前**、由每个工具运行时（shell/exec_command/apply_patch/mcp_tool_call/network_access/request_permissions）统一调用。`[读到]`
- 拦的不是工具名，是工具名 + 完整参数：`ApprovalAction` 枚举每个变体都带着完整命令 argv / cwd / patch 内容与目标文件 / MCP server+tool+参数 / network host+port 等（`approvals.rs:66-150`）。`[读到]`
- 沙箱与审批的关系：以 `assess_patch_safety`（`codex-rs/core/src/safety.rs:26-98`）为例——如果写操作能被完全约束在沙箱可写根内，且平台沙箱确实可用（`get_platform_sandbox`），就直接 `AutoApprove`，不问用户，靠沙箱兜底；只有当沙箱不可用、或操作会突破可写根时，才升级为 `AskUser`/`Reject`。也就是说**沙箱内的操作默认不打扰用户，沙箱边界之外的操作才触发审批**。`[读到]`（注：这是 `apply_patch` 路径；shell/`unified_exec` 命令是否有对等的“沙箱内自动放行”函数未在本次源码阅读范围内定位到，见未确认项）
- 谁不信任谁：系统既不信任模型输出的命令本身安全，也不认为"跑在沙箱里"就足以豁免一切——沙箱负责兜底文件系统/网络边界，exec-policy 规则引擎负责对命令做前置分类（allow/reject/prompt），审批层负责处理沙箱不能兜底或规则未覆盖的情形，三层叠加。`[推断]`（由 assess_patch_safety 的分支结构 + execpolicy 规则引擎存在 + Guardian/User 审批链路共同存在推出）

代价：拦截点在“核心会话层”而不是“沙箱边界层”，意味着一旦某个工具运行时的判断逻辑写错（比如误判某个 patch 完全在可写根内），审批会被整个跳过而不会有沙箱兜底第二次拦截的假设——沙箱和审批共享同一份“可写根”判断输入，不是两套独立冗余的防线。

### 2 决策单元

- 会话级“记住”的最小单位不是工具、也不是宽泛的“一类操作”，而是**一次调用的精确签名**：`ApprovalCacheKey`（`approvals.rs:152-266`）。
  - Shell/ExecCommand：`(environment_id, 规范化后的命令 argv, cwd, sandbox_permissions, additional_permissions)`。
  - ApplyPatch：**按文件路径拆开**，一个 patch 涉及几个文件就生成几个 key，"批准一次"只精确覆盖这些文件路径，不覆盖整个项目或整个 patch 类别。
  - McpToolCall / NetworkAccess / RequestPermissions：`cache_keys()` 返回空——**这三类根本不进入这个精确匹配缓存**，它们各自有自己的持久化机制（见切面 5）。`[读到]`
- 命令的“规范化”（`canonicalize_command_for_approval`，`codex-rs/core/src/command_canonicalization.rs:14-38`）只做**外壳包装差异归一**（例如 `bash -lc` vs `/bin/bash -lc` 视为同一个），**不做前缀泛化**——参数不同就是不同的 key，命中缓存要求命令文本（规范化后）完全一致。`[读到]`
- 默认级别：单次调用（`AutoApprove` / `AskUser` 一次性决策）。用户在交互提示里可以主动升级到更宽的对象：
  - 会话内“不再问同一条命令”（`ApprovedForSession`，精确匹配缓存，见上）
  - 会话内“不再问这个 host”（`NetworkAccess` 场景的"allow this host for this conversation"）
  - 跨会话“以后不再问这一类前缀命令”（`ApprovedExecpolicyAmendment`，写入 `.rules` 文件的 `prefix_rule`）
  - 跨会话"以后不再问这个 MCP 工具"（`ApprovedMcpPolicyAmendment`）
  - 跨会话"以后允许/拒绝这个 host"（`NetworkPolicyAmendment`）
  这些选项都是 `ReviewDecision` 的具体枚举值（`codex-rs/protocol/src/protocol.rs:3871-3906`），由用户在提示界面里显式选择才会升级，系统不会自动升级级别。`[读到]`

代价：ApplyPatch 按“文件路径”而不是“这次改动”做缓存键，意味着模型对同一批文件反复小幅修改时，只要文件集合不变就不会重复问——这在“连续小步修改同一批文件”的工作流里体验很顺滑，但也意味着用户一次批准后，agent 对这些文件的后续任意内容改动（哪怕语义上和第一次批准的内容完全不同）都会被静默放行，直到会话结束或文件集合变化。

### 3 生命周期

- `AskForApproval` 四个取值把审批的“生命周期基调”定在四个不同档位（`codex-rs/protocol/src/protocol.rs:916-940`）：
  - `untrusted`（`UnlessTrusted`）：只有"已知安全的只读命令"自动放行，其余每次都问，不存在"记住"这一说（`assess_patch_safety` 里这个分支直接返回 `AskUser`，不进入缓存判断）。`[读到]`
  - `on-request`（`OnRequest`，默认值，且 `on-failure` 作为别名映射到它）：模型自己决定何时该问；问过之后用户可以选择只批一次，也可以选择升级为会话级/跨会话级记住。`[读到]`
  - `granular`（`Granular(GranularApprovalConfig)`）：五个布尔开关（`sandbox_approval`/`rules`/`skill_approval`/`request_permissions`/`mcp_elicitations`），每个开关 `true` 表示该类请求走正常审批流程，`false` 表示直接自动拒绝、不再打扰用户去问。这是"按请求类别整体开关"，不是按单个命令。`[读到]`
  - `never`：从不问用户，失败直接回传给模型自己处理，"从不升级到用户审批"（协议里明文写"never escalated to the user"）。`[读到]`
- 三种"记住"的持续时间分别对应：
  - `ApprovedForSession`（会话内精确匹配缓存）：活到进程/会话结束，存在内存 `HashMap`（`ApprovalStore`，`codex-rs/core/src/tools/sandboxing.rs`），未发现任何落盘代码路径。`[读到]`
  - `ApprovedExecpolicyAmendment` / `NetworkPolicyAmendment`（写入 `.rules` 文件的前缀规则/网络规则）：一旦写入即为**永久**，直到有人手动编辑规则文件删除该行；不因重启、换 session 而失效。`[读到]`
  - 项目 `trust_level`：写入 `config.toml`，同样永久，直到手动改配置。`[读到]`
- 升迁触发者：全部由**用户在交互提示里的显式选择**触发（切面 2 里列的几种 `ReviewDecision`），代码里没有发现系统自动把“批了很多次”累积升级为“记住这一类”的自动化逻辑。`[推断]`（未见到自动升级代码，按当前搜索范围判断为不存在，但不排除遗漏）
- 重启/换项目/换机分别丢什么：
  - 重启（同一项目、同一台机器）：会话级 `ApprovedForSession` 全部丢失；`trust_level`、`.rules` 前缀规则、网络规则全部保留（都在 `config.toml`/`rules/*.rules` 里）。`[读到]`
  - 换项目（同机器，不同 cwd）：`trust_level` 按项目路径索引，天然不跨项目共享；用户级 `~/.codex/rules/*.rules` 里的前缀规则**是全局的，跨项目共享**（因为它加载自 `codex_home`，不区分 project）；项目级 `.codex/rules/*.rules` 只在该项目内有效。`[读到]`
  - 换机：`~/.codex/` 整个不随代码仓库走，除非用户手动同步这个目录，否则信任域、规则文件、MCP/网络策略在新机器上全部从零开始。`[推断]`（基于存储位置是本地 `codex_home` 而非仓库内文件这一事实推出）

代价：`granular` 的“类别级开关”一旦设为 false 就是静默拒绝而不是静默放行——如果用户图省事把 `rules`（execpolicy prompt 类别）关掉，以为是“别再为规则问我了”，实际效果是所有原本该走 `prompt` 规则的动作会被自动拒绝而不是自动允许，容易被误用成“为什么 Codex 突然什么都做不了”。

### 4 持久化与作用域

- `trust_level` 存放路径：`~/.codex/config.toml`，`[projects."<绝对路径>"]` 表下的 `trust_level` 字段（本地实读确认，见下方原文）。`[读到]`

```
[projects."/Users/harveyzhang96"]
trust_level = "untrusted"

[projects."/Users/harveyzhang96/Projects/Product Insight"]
trust_level = "trusted"
```

- 索引 key 的构成：不是单纯的字符串路径匹配，而是一套多层回退查找（`ProjectTrustContext::decision_for_dir`，`codex-rs/config/src/loader/mod.rs:1010-1054`）：
  1. 先查 cwd 本身的规范化路径（原始路径字符串 + `canonicalize` 后的路径字符串两种 key 都会尝试，`normalized_project_trust_keys`，`loader/mod.rs:1205-1218`）
  2. 查不到，退到 project_root（按 `project_root_markers`，如 `.git`，向上找到的项目根目录）
  3. 再查不到，退到 git 仓库根（`resolve_root_git_project_for_trust`，专门处理 git worktree/checkout 场景，`worktree` 路径下没有单独记录时会去查主仓库根的信任状态）
  4. 全部查不到 -> `trust_level = None`（未决定，触发首次信任提示）
  Windows 上所有 key 会先转小写再比较，做大小写不敏感匹配（`normalize_project_trust_lookup_key`，`loader/mod.rs:1220-1226`）。`[读到]`
- 跨 session：共享（同一台机器上任意 session 只要 cwd 落在同一个 key 下就复用同一条 `trust_level`）。`[读到]`
- 跨项目：不共享（key 就是项目路径本身）。`[读到]`
- 跨设备：不共享，`~/.codex/config.toml` 是本地文件，没有发现任何云端同步机制（本次搜索范围内）。`[推断]`（未找到同步代码，但也未穷尽搜索 `cloud_config`/`workspace_identity` 等企业侧模块，见未确认项）
- 路径变化的行为：
  - 目录改名/移动：新路径没有对应 key，`trust_level` 为 `None`，会重新触发信任询问（对 TUI 交互式流程而言）或被 app-server 自动信任路径静默重新写入（见下方 UX 部分的"两条写入路径"）。`[推断]`（由 key = 路径字符串这一事实直接推出）
  - symlink：`normalized_project_trust_keys` 同时保留“字面路径”和“canonicalize 之后的路径”两个 key 去查找——如果历史记录写的是 canonical 路径而当前访问走的是 symlink 路径，仍然能匹配上（反之亦然）。`[读到]`
  - git worktree：有专门的 `repo_root_lookup_keys` 回退，worktree 路径本身查不到时会退到主仓库根，如果主仓库根是 trusted，worktree 默认也当作已决定（trusted），不会重新问。`[读到]`

代价：这套多层回退对“同一个仓库的不同 worktree 应该被同等信任”这个直觉友好，但也意味着**用户没法把某一个 worktree 单独标为“不信任”**而让同仓库其它 worktree 保持信任——回退链路里没有“worktree 级别单独覆盖”的中间层，一旦某仓库根被标 trusted，所有 worktree（除非各自在 `projects.<worktree路径>` 下有更高优先级的直接命中）都继承这个信任。

### 5 泛化与匹配

- 从“这一次”到“这一类”的转换只发生在用户显式选择“记住这一类”选项后（见切面2/3），产物落在两种持久文件：
  - `~/.codex/rules/default.rules`（execpolicy 规则文件，本地已实读，格式确认）：
    ```
    prefix_rule(pattern=["npx", "tsx", "src/cli.ts", "run", "--input"], decision="allow")
    ```
    语法上是前缀 token 数组匹配：只要命令 argv 的前 N 个 token 与 pattern 完全一致（区分大小写、逐 token 精确比较），后面任意参数都算命中。写入函数 `blocking_append_allow_prefix_rule`（`codex-rs/execpolicy/src/amend.rs`）直接把用户批准时勾选的“记住这个前缀”序列化后追加一行。`[读到]`
  - 网络规则（同一套 `.rules` 文件，`blocking_append_network_rule`）：按 host 记录 allow/deny，UX 文案是 “Yes, and allow this host in the future” / “No, and block this host in the future”。`[读到]`
- 规则文件加载范围：不止 `~/.codex/rules/`，`load_exec_policy`（`codex-rs/core/src/exec_policy.rs:650-699`）会遍历**每一个已启用的 config layer**（managed/requirements、user、project——project 层前提是该项目 trusted）各自的 `rules/*.rules` 子目录，全部解析进同一个 Policy，层级越高（越接近用户/项目）优先级越高，可以覆盖低优先级层的规则。存在一个 `ignore_user_and_project_exec_policy_rules` 开关，可以在跑受管控场景（如 `cyber`/安全扫描）时整体屏蔽 user+project 两层的规则，只保留 managed 层。`[读到]`
- 归一化处理：
  - 命令层面：`canonicalize_command_for_approval` 只处理 shell 包装差异（`bash -lc` vs `/bin/bash -lc`、区分出脚本文本本体），不做“复合命令拆分”这类语义级归一——复杂脚本会被整体当作一段脚本文本参与匹配，没有把 `a && b` 拆成 `a`、`b` 分别判断的证据。`[读到]`（未见拆分逻辑）
  - 路径层面：仅在 trust_level 查找环节做了 symlink/canonical 双 key 归一（见切面4），execpolicy 规则文件本身对路径参数没有看到专门的符号链接/相对路径归一逻辑。`[未查]`：execpolicy 规则匹配时如果 pattern 里包含路径 token（如例子里的 `examples/mvp-input.json`），相对路径 vs 绝对路径、`..` 展开等归一细节未在本次代码阅读范围内确认，需要读 `codex-rs/execpolicy/src/policy.rs` 的匹配实现细节才能下结论。
- 已知绕过/防护：源码里能看到的防护点——`WritableRoot::path_contains_protected_metadata_name`（`codex-rs/protocol/src/protocol.rs:1092-1104`）显式保护 `.git`、`.codex` 等目录名不被“可写根”覆盖，防止通过写沙箱把自己的信任/规则配置文件改掉来提权。`[读到]`。除此之外没有找到更具体的“已知绕过”文档或代码注释（比如复合命令注入、`eval` 类逃逸的专门处理），标记为未查。`[未查]`

代价：前缀匹配的泛化力度是“越具体越安全、越宽泛越省心”的直接权衡——用户批准时选的前缀越短（比如只到 `npx tsx`），未来免打扰的命令面越大，但也意味着后续任何以这个前缀开头的命令（包括模型后来生成的、语义完全不同的调用）都会被自动放行，规则文件里没有看到基于命令语义/风险等级的二次校验。

### 6 撤销与可审计

- 撤销信任：没有找到任何专门的 CLI 子命令（`codex-rs/cli/src/main.rs` 的 `Subcommand` 枚举里没有 `trust`/`untrust`/`projects` 之类的入口，完整枚举见源码 `codex-rs/cli/src/main.rs:132-230`），撤销只能靠**手动编辑 `~/.codex/config.toml`**，把对应 `[projects."<path>"]` 的 `trust_level` 改成 `"untrusted"` 或整段删除。`[读到]`（否定性证据：枚举里没有对应子命令）
- 撤销粒度 vs 批准粒度是否对称：不对称。批准这条线有“单次 / 会话 / 前缀类 / host / 整个项目”多档细粒度选项（切面2），撤销这条线只有“整项目 trust_level 改回 untrusted”这一个粗粒度操作；已经写进 `.rules` 文件的某一条 `prefix_rule` 或某一条 network rule，没有发现对应的“删除/收回”命令，只能手动打开文本文件删那一行。`[读到]`（同样是否定性证据：搜索范围内未发现移除类 API/子命令）
- 用户能否查看自己信任了哪些项目：没有发现专门的“列出所有 trusted 项目”命令或 UI（`codex doctor` 是环境/安全体检——比如检测端点防护软件——不是信任状态审计，`codex-rs/cli/src/doctor/security.rs` 通篇是关于本机 EDR/AV 产品检测，与项目信任无关）。唯一途径是打开 `~/.codex/config.toml` 手工读 `[projects.*]` 各个表。`[读到]`
- 误标 trusted 之后的恢复路径：手动改回 `untrusted`（同上），但要注意——已经因为“曾经 trusted”而被加载执行过的项目级 hooks/规则造成的副作用（比如已经写过的文件、已经执行过的命令）不会被这个改动撤销，`trust_level` 只影响**未来**的配置加载，不回滚已发生的动作。`[推断]`（由 trust_level 只是"加载开关"这一事实直接推出，配置系统本身没有"回滚已执行动作"的概念）
- 审计日志：`~/.codex/history.jsonl` 和 `~/.codex/session_index.jsonl` 本地实读确认内容是**提示词文本 / 会话标题**，不是审批决策记录（例如 `history.jsonl` 里的条目是 `{"session_id":...,"ts":...,"text":"npx tsx src/cli.ts run --input ..."}`，没有 approve/deny 字段）。`[读到]`。代码里确实存在审批决策的埋点（`record_resolution`/`session_telemetry.tool_decision`，`codex-rs/core/src/tools/approvals.rs:841-854`；`session_telemetry.counter("codex.approval.requested", ...)`，`codex-rs/core/src/tools/sandboxing.rs:99-106`），但这些是发给 OTel/analytics 管道的埋点，本次没有追踪到它们是否落到本地任何可查询文件（`state_5.sqlite`/`logs_1.sqlite` 未做结构性检查，只读了目录列表）。`[未查]`：这些埋点最终是否/如何在本地可查询，需要进一步读 `codex-rs/otel`、`codex-rs/state` 或直接 dump `logs_1.sqlite`/`state_5.sqlite` 的表结构才能确认。

代价：批准细、撤销粗——这是这套机制里最直接的“事后清理成本”问题：一旦用户在很多个项目里陆续按了“记住这个前缀”“信任这个项目”，想要系统性收紧权限时，除了逐条打开 `.rules` 文本文件手删、逐个项目改 `config.toml`，没有任何工具能一键列出“我到底信任了什么”，更没有一键撤销。

### 7 审批 UX

- 首次进入新目录（trust_level 为 None）的信任提示（TUI，`codex-rs/tui/src/onboarding/trust_directory.rs`）：
  - 文案：“Do you trust the contents of this directory? Working with untrusted contents comes with higher risk of prompt injection. Trusting the directory allows project-local config, hooks, and exec policies to load.”
  - 若 cwd 是某个 git 仓库的子目录，额外提示“Trusting will apply to the repository root: <root>”——即信任决策的落点是仓库根，不是当前子目录。
  - 选项只有两个：`Yes, continue`（默认高亮）/ `No, quit`。**`No, quit` 只是退出 CLI 进程，不写任何配置**（`handle_quit` 只置 `should_quit = true`，`trust_directory.rs`）；只有 `Yes, continue` 会把 `trust_level = "trusted"` 写进 `config.toml`（`persist_selected_trust`，`codex-rs/tui/src/onboarding/onboarding_screen.rs:641-706`）。也就是说，交互式首启流程里**从来不会主动写入 `"untrusted"`**——“未决定”和“主动拒绝”在这条路径上是同一个结果（退出）。`[读到]`
  - 另有一条完全不同的写入路径：app-server（IDE 扩展等非 TUI 客户端）在 `thread_start` 时，如果 `trust_level` 为 None 且当前生效的权限档位（`effective_permission_profile`）已经隐含“可以在 cwd 写”，会**自动、静默**把该路径写成 `trust_level = "trusted"`，不经过任何用户确认（`codex-rs/app-server/src/request_processors/thread_processor.rs:1270-1319`）。`[读到]`。本地 `config.toml` 里那条 `/Users/harveyzhang96` 的 `trust_level = "untrusted"` 具体是通过哪条路径写入的，本次未能在代码里定位到显式写 `"untrusted"` 的调用点（除测试代码外，只发现 `TrustLevel::Trusted` 被主动写入的路径），标记为未查。`[未查]`
- 命令执行审批提示的选项集合（`codex-rs/tui/src/bottom_pane/approval_overlay.rs`，字符串原文摘录）：
  - 一般命令：`Yes, just this once` / `Yes, and don't ask again for commands that start with '<prefix>'`（仅当系统主动提出一个前缀规则建议时出现）/ `No, continue without running it` / `No, and tell Codex what to do differently`
  - 网络访问：`Yes, just this once` / `Yes, and allow this host for this conversation` / `Yes, and allow this host in the future` / `No, and block this host in the future` / `No, and tell Codex what to do differently`
  - `request_permissions` 工具调用：`Yes, grant these permissions for this turn` / `Yes, grant for this turn with strict auto review` / `Yes, grant these permissions for this session` / `No, continue without permissions`
  - MCP elicitation（第三方 MCP server 主动要信息）：`Yes, provide the requested info` / `No, but continue without it`
  `[读到]`
- 默认选中项：信任提示默认高亮 `Yes, continue`（`onboarding_screen.rs:162`，`let highlighted = TrustDirectorySelection::Trust;`）。`[读到]`；命令审批提示默认高亮哪一项本次未确认。`[未查]`
- 超时行为：交互式“问用户”这条分支的代码（`request_user_approval`）没有看到任何超时/自动决策逻辑，推断为无限等待人操作；相反，Guardian（自动审阅）分支明确定义了 `ReviewDecision::TimedOut` 状态和 `guardian_timeout_message()`（`codex-rs/core/src/guardian/`），说明超时机制目前只覆盖“自动审阅”场景，不覆盖“人工审阅”场景。`[推断]`（由 `request_user_approval` 内未见超时相关代码、而 Guardian 路径显式存在超时类型这一对比推出）

代价：TUI 首启流程把“未决定”和“显式拒绝”合并成同一个结果（退出进程、不留记录），这意味着用户没法通过这条路径主动、明确地把一个目录标成"我看过了，我不信任它"，下次进这个目录还是会重新问一遍——想要"记住我不信任这个目录"，只能手动编辑 config.toml。而 app-server 的静默自动信任路径又是相反方向的问题：只要满足权限档位条件就会不经确认直接写 trusted，两条路径的用户可见性完全不对等。

### 8 无人值守降级

- `codex exec`（非交互子命令，CI/脚本场景）在构建配置时**默认强制** `approval_policy = AskForApproval::Never`（`codex-rs/exec/src/lib.rs:406-411`，注释原文：“Default to never ask for approvals in headless mode. Rebuild below if the fully resolved reviewer is AutoReview.”）。`[读到]`
- 但这不是无条件的：`build_exec_config`（`codex-rs/exec/src/lib.rs:582-611`）会先按“强制 Never”构建一次配置；如果解析出的 `approvals_reviewer == AutoReview`（即项目/用户配置里显式启用了 Guardian 自动审阅），就**放弃强制 Never，改用配置里原本的 approval_policy 重新构建**——也就是说无人值守场景下如果配置了 Guardian，Guardian 仍然会介入评审，不是纯粹“全部放行”。`[读到]`
- `AskForApproval::Never` 的护栏本身：协议注释明写“Failures are immediately returned to the model, and never escalated to the user for approval”（`codex-rs/protocol/src/protocol.rs:937-939`）——即某个动作被拒绝时，失败信息回传给模型让它自己想办法，绝不会等待人。`[读到]`
- 真正的兜底不是审批策略，是沙箱：headless 模式下 `sandbox_mode` 仍然按 CLI 参数/项目配置正常解析（`exec/src/lib.rs:294-298`），并没有被一并放宽——除非用户显式传 `--dangerously-bypass-approvals-and-sandbox`，这个 flag 会同时把 `approval_policy` 设为 `Never` 且 `sandbox_mode` 设为 `SandboxMode::DangerFullAccess`（`exec/src/lib.rs:294-298`，`cli/src/main.rs:2209-2217`），并且这个 flag 的命名本身带着"danger"字样，是一种命名层面的摩擦/警示设计。`[读到]`
- fail-safe 朝哪边倒：**朝“不打扰、但仍受沙箱约束”倒**，不是朝“全部拒绝”也不是朝“全部放行”。默认 headless 行为 = 从不等人 + 沙箱边界照常生效；只有显式加危险 flag 才是真正无边界的“全部放行”。`[推断]`（由上面三条 `[读到]` 证据的组合直接得出）

代价：这个默认设计对“CI 里跑 `codex exec` 却忘了配置合适的 sandbox_mode/writable_roots”这种情况没有额外保护——因为“不问人”是默认值而不是需要显式打开的选项，如果项目本身的 sandbox 配置定得比预期宽（比如某处配置了 `workspace-write` 但 `writable_roots` 覆盖了不该覆盖的路径），无人值守场景下不会有任何人工兜底去拦住它，全靠 sandbox 配置本身的正确性。

## 时序

以“全新目录首次用 TUI 打开、执行一条会写文件的命令”为例，用 ASCII 表示各方交互：

```
User                 Codex TUI                Config Loader          Session/Approval          Sandbox/FS
 |                        |                          |                       |                       |
 |-- codex (cwd=X) ------>|                           |                       |                       |
 |                        |-- 查 trust_level(X) ----->|                       |                       |
 |                        |<-- None（未设置）---------|                       |                       |
 |<-- 信任提示界面 --------|                           |                       |                       |
 |   "Yes, continue" /                                |                       |                       |
 |    "No, quit"                                      |                       |                       |
 |-- 选 Yes, continue --->|                           |                       |                       |
 |                        |-- 写 trust_level=trusted->|                       |                       |
 |                        |                          |-- 重新加载项目层        |                       |
 |                        |                          |   (config/hooks/rules)|                       |
 |                        |<-- 加载完成 --------------|                       |                       |
 |-- "写个文件" --------->|                           |                       |                       |
 |                        |-- 工具调用: apply_patch ------------------------->|                       |
 |                        |                          |                       |-- 检查 hooks --------->|
 |                        |                          |                       |<-- 无 hook 命中 -------|
 |                        |                          |                       |-- 判断: 目标路径是否   |
 |                        |                          |                       |   在可写根内?           |
 |                        |                          |                       |-- 是, 且沙箱可用 ------>|
 |                        |                          |                       |<-- AutoApprove --------|
 |                        |                          |                       |-- 在 sandbox 内执行 --->|
 |                        |                          |                       |<-- 完成 ----------------|
 |<-- 结果展示 -----------|                           |                       |                       |
```

若第二次执行的是一条会跑到工作区之外、且用户在提示里选了“记住这个前缀”：

```
 |-- 工具调用: shell(cmd) ------------------------------------------------->|
 |                                                                          |-- 判断: 超出可写根/需要审批
 |                                                                          |-- 走 Guardian 还是 User?
 |                                                                          |   (approval_policy=on-request
 |                                                                          |    且 approvals_reviewer!=AutoReview
 |                                                                          |    -> User)
 |<-- 审批提示: "Yes, just this once" / "Yes, and don't ask again          |
 |     for commands that start with '<prefix>'" / "No..." ----------------|
 |-- 选 "记住这个前缀" ----------------------------------------------------|
 |                                                                          |-- 写 <codex_home>/rules/default.rules
 |                                                                          |   追加 prefix_rule(pattern=[...], decision="allow")
 |                                                                          |-- 本次 AutoApprove 并执行
 |<-- 结果展示 -------------------------------------------------------------|
 (下次同前缀命令: exec_policy 规则命中 -> 不再进入审批提示，直接放行)
```

## 明确不做什么

- 不做 `trust_level` 决定"要不要问用户"这件事——它只决定项目自己的配置/hooks/规则文件加不加载（见"信任域与逐次审批的关系"一节）。
- 不做跨设备的信任/规则同步——`~/.codex/config.toml` 和 `~/.codex/rules/*.rules` 都是本地文件，没发现云同步机制。
- 不做"一键查看我信任了哪些项目"或"一键撤销"——没有对应 CLI 子命令，只能手工编辑文件。
- 不对已经因为曾经 trusted 而执行过的动作做任何回滚——撤销信任只影响未来的配置加载。
- 交互式信任提示不做"记住我拒绝"——`No, quit` 只是退出进程，不写任何持久状态。
- 人工审批这条分支不做超时——超时机制目前只在 Guardian（自动审阅）分支里存在。

## 未确认项汇总

1. `config.toml` 里显式写着 `trust_level = "untrusted"`（本地实例：`/Users/harveyzhang96` 这个项目条目）具体是通过哪条代码路径写入的——本次搜索范围内只找到 `TrustLevel::Trusted` 的显式写入调用点（TUI onboarding、app-server 自动信任、测试代码），没有找到任何非测试代码显式写 `TrustLevel::Untrusted` 的位置。可能是用户手动编辑，也可能是本次未覆盖到的某条代码路径（例如企业管理侧的 `requirements.toml`/managed config 写入，或早期版本的不同 UX）。去哪查：全仓库对 `TrustLevel::Untrusted` 的构造点做穷尽搜索，并确认是否存在 managed/org 配置下发信任决策的写入路径。
2. shell/`unified_exec` 命令是否存在与 `assess_patch_safety` 对等的"命令能否在沙箱内自动放行"的判定函数——本次只完整读了 `apply_patch` 的 `assess_patch_safety`，没有定位/读到 shell 命令对应的等价逻辑（大概率在 `codex-rs/core/src/tools/runtimes/shell.rs` 或 `unified_exec.rs`，未展开读）。去哪查：读 `codex-rs/core/src/tools/runtimes/shell.rs`、`unified_exec.rs` 及 `codex-rs/sandboxing` crate。
3. execpolicy 规则匹配对路径类 token 的归一化细节（相对路径、`..`、符号链接）——只确认了 trust_level 查找环节的路径归一，规则引擎本身的匹配实现（`codex-rs/execpolicy/src/policy.rs`）未展开读。
4. `ApprovedMcpPolicyAmendment`（MCP 工具跨会话免审批）具体持久化在哪个文件/哪种格式——只确认了协议里存在这个决策变体和它的语义描述，没有追踪到具体的存储实现。
5. 审批决策的遥测埋点（`session_telemetry.tool_decision`、`codex.approval.requested` 计数器）最终是否/如何落到本地可查询的文件（`logs_1.sqlite`/`state_5.sqlite`）——只做了目录级只读查看，没有做表结构检查。
6. 命令审批提示（`approval_overlay.rs`）的默认高亮选项是哪一个——只确认了信任提示默认高亮"Yes, continue"，命令审批提示的默认项未查。
7. `execpolicy` 的 `Decision` 枚举完整取值范围（本次只确认了 `"allow"`）——`prefix_rule`/网络规则是否还支持 `"reject"`/`"prompt"` 等其他取值及其语义，未在 `codex-rs/execpolicy/src/decision.rs` 里展开确认。
8. 是否存在已知的绕过手法（复合命令拆分注入、`eval`/间接执行逃逸审批等）及对应防护代码——只确认了针对可写根的 `.git`/`.codex` 元数据目录保护，没有找到更系统性的"已知绕过与防护"清单或注释。

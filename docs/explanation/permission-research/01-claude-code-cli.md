# Claude Code CLI 权限模块机制报告

## 元信息

- 分析对象：Claude Code CLI，本机安装版本 `2.1.224`（`claude --version` 实测）
- 路线：黑盒（官方文档 + 本地配置实测，无源码）
- 依据来源清单：
  - 文档（均为 2026-08-19 抓取，域名已从 docs.claude.com 301 跳转到 code.claude.com）：
    - https://code.claude.com/docs/en/permissions （核心：规则语法、模式、workspace trust）
    - https://code.claude.com/docs/en/permission-modes （模式详情、classifier、protected/critical paths）
    - https://code.claude.com/docs/en/settings （四层 settings 文件、优先级、schema）
    - https://code.claude.com/docs/en/security （已知风险声明、防护清单）
    - https://code.claude.com/docs/en/hooks （PreToolUse 位置与输出格式）
    - https://code.claude.com/docs/en/headless （`-p`/CI/SDK 下的权限降级）
    - https://code.claude.com/docs/en/iam （跳转目标同 permissions，未产出独立新信息）
  - 本地文件（只读）：
    - `~/.claude/settings.json`
    - `~/.claude/settings.local.json`（不存在）
    - `/Users/harveyzhang96/Projects/harveyz-skill/.claude/settings.json`
    - `/Users/harveyzhang96/Projects/harveyz-skill/.claude/settings.local.json`
    - `~/.claude.json`（顶层字段 + `projects["<path>"]` 子树）
  - 实测命令：`which claude`、`claude --version`、`claude --help`、`claude auto-mode --help`、`claude project --help`；未执行任何写操作
- 分析日期：2026-08-19

## 定位

权限模块是 Claude Code 在"模型决定调用某个工具"和"工具真正在本机执行"之间插入的一道判定层。它只回答一个问题：这次调用要不要问用户。判定依据三类输入：写在 settings 文件里的规则（allow/deny/ask）、当前会话的 permission mode、以及可选的 PreToolUse hook 和（auto 模式下）一个独立的 classifier 模型。判定结果落到三个动作之一：直接放行、直接拒绝、弹窗问用户。`[读到]` 文档明确写道"Permission rules are enforced by Claude Code, not by the model"——即这层判定在 CLI 宿主进程里，不是模型自律。

## 架构

```
模型产出一次工具调用意图 (tool_name, tool_input)
        |
        v
PreToolUse hook  (可返回 allow / deny / ask；exit code 2 强制 deny)
        |  hook 的 allow/ask 不能覆盖下面的 deny/ask 规则；hook 的 deny 优先于 allow 规则
        v
permissions 规则匹配： deny -> ask -> allow，命中即止，与规则精细度无关
        |
        v
按 permission mode 分流：
  default(manual)  : 只读免检，其余按上面结果问用户
  acceptEdits      : 读 + 文件编辑 + 一批文件系统命令免检
  plan             : 只读 + (若 auto 可用) classifier 审核命令，不许改源码
  auto             : 规则命中的直接放行/拒绝；其余交给 classifier 模型复核
  dontAsk          : 不在 allow 规则里的一律拒绝，从不弹窗
  bypassPermissions: 除"任何模式都不自动批准"的清单外全部放行
        |
        v
（可选）用户交互式弹窗：Yes / Yes and don't ask again / No
        |
        v
工具执行
```

谁不信任谁：`[读到]` 是 Claude Code（宿主进程）不信任模型的输出，模型的工具调用意图必须经过宿主的规则/模式/（可选）classifier/用户四层过滤才能落地。CLAUDE.md 或 prompt 里写的规则只影响模型"想不想做"，不改变宿主"让不让做"。

## 八切面

### 1 拦截点

- 拦截发生在 `PreToolUse` hook（如果配置了）→ 权限规则匹配 → 用户弹窗，三级串联，早于工具真正执行。`[读到]` https://code.claude.com/docs/en/hooks：管道位置为 `Tool call initiated → PreToolUse hook → Permission flow → Tool execution`。
- 拦的对象是"工具名 + 输入参数"的组合，不是单纯工具名。规则语法 `Tool(specifier)` 里 specifier 既可以是 Bash 命令串、文件路径，也可以是任意标量参数（`Tool(param:value)`）。但**不能**对工具的"主内容字段"做参数匹配——Bash 的 `command`、Read/Edit/Write 的 `file_path`、Grep/Glob 的 `path`、WebFetch 的 `url` 这些字段必须走各工具自己的专用 specifier 语法（如 `Bash(rm *)`、`Read(./path)`），写 `Bash(command:rm *)` 会被启动时警告并忽略。`[读到]` https://code.claude.com/docs/en/permissions#match-by-input-parameter：原文"A rule like `Bash(command:rm *)` would be bypassable by a compound command, so Claude Code ignores it and emits a startup warning."
- 谁不信任谁：宿主进程不信任模型的工具调用意图；hook 脚本本身则是用户/项目主动注入的额外不信任层，可以比默认规则更严格，但**不能**绕过既有的 deny/ask 规则去放宽权限——`[读到]` 原文："Hook decisions don't bypass permission rules... a matching deny rule blocks the call, and a matching ask rule still prompts even when the hook returned "allow" or "ask""。
- 本地实测：本仓库 `.claude/settings.json` 配置了一个 `PreToolUse` hook，`matcher: "Bash"`，调用 `check-similar-branch.sh`，且用户级 `~/.claude/settings.json` 里另有一个 matcher 为空字符串（等价于全工具）的 `PreToolUse` hook 调用 `notify.sh`。两者会并行触发，互不替代。`[本地实测]` 文件路径见"元信息"。

**代价**：`Bash(command:rm *)` 这类"看起来该管用却被静默忽略"的规则，如果产品经理设想的心智模型是"参数级匹配可以覆盖到工具的核心动作参数"，会在这里踩空——只有工具作者预先设计好的 specifier 语法（Bash 命令串、文件路径、domain）才被真正校验，任意参数匹配存在硬性白名单限制。`[读到]`

### 2 决策单元

- 一次"同意"的默认粒度因工具类型而不同，不是统一的"一次调用"或"一个工具"：

  | 工具类型 | 是否需要审批（Manual 模式） | "不再询问"的作用域 |
  |---|---|---|
  | 只读（文件读、Grep） | 否（工作目录及 additionalDirectories 内） | 不适用 |
  | Bash 命令 | 是（内置只读命令集除外） | 永久，按"仓库 + 具体命令"维度 |
  | 文件修改（Edit/Write） | 是 | 仅到会话结束，不落盘 |
  | WebFetch | 是（内置预批准文档域名除外） | 永久，按"仓库 + 域名"维度 |
  | WebSearch | 是 | 永久，按"仓库"维度 |

  `[读到]` https://code.claude.com/docs/en/permissions#permission-system 表格原文。
- 默认级别：Manual 模式（config 值 `default`）下，读操作默认放行，其余默认逐次询问；用户可以通过修改 `permissions.defaultMode`、`/permissions` 手动加规则、或按 `Shift+Tab` 切模式来升降级。`[读到]`
- 决策单元不是"资源前缀"或"信任域"这类抽象概念，而是具体的"规则字符串是否匹配"，规则本身可以窄到一条精确命令、也可以宽到 `Bash(*)`（等价裸工具名，会把整个工具从模型可见工具集里移除）。`[读到]` https://code.claude.com/docs/en/permissions#match-all-uses-of-a-tool

**代价**：文件修改类审批"不落盘、只活到会话结束"意味着每次新会话都要重新对同一批文件的编辑权限做出选择，产品侧如果预期"批准过的编辑权限会像 Bash 规则一样持久化"，会被这个不对称设计打破预期——这也解释了为什么 `acceptEdits` 模式存在（用模式而不是规则来解决编辑权限的重复询问问题）。`[读到]`

### 3 生命周期

- 批准的存活时间因类型而异（见切面 2 表格）：Bash/WebFetch/WebSearch 的"Yes, and don't ask again"是永久性的，写入磁盘规则；文件修改的批准只活到当前会话结束。`[读到]`
- 层级升迁（"这次" → "这个会话" → "这个仓库永久"）由用户在弹窗里主动选择触发，CLI 不会自动升级审批范围。当弹窗展示的内容不足以完整代表规则会覆盖的范围时（命令/编辑过大而无法完整展示），CLI 会**不提供**"don't ask again"选项，只给一次性批准。`[读到]` https://code.claude.com/docs/en/permissions#permission-system：原文"Claude Code offers those options only when the prompt can show you everything they would allow...Claude Code leaves the options out when the command or edit is too large to show in full"。
- Permission mode 本身也有生命周期：`Shift+Tab` 在 `default → acceptEdits → plan → default` 之间循环（`auto`/`bypassPermissions` 若被启用会插入循环中）；`dontAsk` 从不出现在循环里，只能用 `--permission-mode dontAsk` 显式指定。`[读到]` https://code.claude.com/docs/en/permission-modes#switch-permission-modes
- 会话 resume 时，permission mode 会被保留（除非显式传 `--permission-mode`）；`bypassPermissions` 模式必须在会话**启动时**就被启用，中途无法从未启用状态切入。`[读到]`
- 重启/resume/换机分别丢什么：
  - 重启终端新开会话：不丢已落盘的仓库级 Bash/WebFetch 规则（在 `.claude/settings.local.json`），但丢"文件修改会话内批准"和当次弹窗选的 permission mode（除非配置了 `defaultMode`）。`[读到]`
  - `--resume`/`--continue`：保留会话当时的 permission mode。`[读到]`
  - 换机：`.claude/settings.local.json` 若未提交到 git 且不同步，则该机器上积累的"don't ask again"规则全部丢失，需要在新机器上重新逐条批准。`[推断]`——文档未直接讨论跨设备场景，推理链条：`.claude/settings.local.json` 文档明确"Automatically gitignored"，而 `~/.claude.json` 的 `hasTrustDialogAccepted` 之类状态也是本机文件，未见任何云同步机制的文档描述。
- "don't ask again"具体写到哪个文件：`.claude/settings.local.json`（git 仓库根目录，经 worktree 解析后落到主 checkout）。`[读到]` 原文："Claude Code saves the rule to `.claude/settings.local.json` at the root of the git repository...Outside a git repository, and when the repository root is your home directory, Claude Code saves the rule in the directory you started it from."

**代价**：Bash 规则"永久"而 Edit 规则"仅到会话结束"这个不对称，会让用户对同一份工作在不同工具类型上产生完全不同的审批疲劳曲线——跑测试命令问一次以后再也不问，但改文件却每个新会话都要重新点头，如果产品设计者没读到这条差异，容易把两者的用户体验混为一谈来做预期管理。`[读到]`

### 4 持久化与作用域

- Settings 分四层：Managed（`/Library/Application Support/ClaudeCode/managed-settings.json` 等，企业级，机器/组织范围）、User（`~/.claude/settings.json`）、Project（`.claude/settings.json`，提交到 git，团队共享）、Local（`.claude/settings.local.json`，git 忽略，个人）。`[读到]` https://code.claude.com/docs/en/settings
- 优先级：**一般 settings** 按 Managed > 命令行参数 > Local > Project > User 排序，高层覆盖低层；但**权限规则是例外**——deny/ask/allow 规则是跨作用域**合并**而非按层级覆盖，"deny 在任意层级出现即生效，没有任何层级能覆盖它"。`[读到]` https://code.claude.com/docs/en/permissions#settings-precedence：原文"If a tool is denied at any level, no other level can allow it... a user-level deny blocks a project-level allow, because deny rules from any scope are evaluated before allow rules."
- Managed 设置有独立的"仅 managed 生效"锁：`allowManagedPermissionRulesOnly` 可让 user/project 层的 allow/ask/deny 规则完全失效，只认 managed 层。`[读到]`
- 索引 key：Bash/WebFetch/WebSearch 的"don't ask again"规则以"仓库根路径 + 具体命令/域名"为索引单元，落在该仓库的 `.claude/settings.local.json` 里；`workspace trust` 的索引 key 是绝对路径，存在 `~/.claude.json` 的 `projects["<绝对路径>"].hasTrustDialogAccepted` 字段里。`[本地实测]` 我读取 `~/.claude.json`，`projects` 下有 1341 个项目条目，`/Users/harveyzhang96/Projects/harveyz-skill` 和 `/Users/harveyzhang96/Projects/Video-Learner` 两个条目的 `hasTrustDialogAccepted` 均为 `true`、`allowedTools` 均为空数组——说明这两个仓库的"文件夹信任"已被接受，但**没有**通过弹窗"Yes, and don't ask again"生成过任何 Bash/命令类持久规则（本机 `~/.claude/settings.json` 把 `permissions.defaultMode` 设为 `bypassPermissions`，弹窗流程被整体跳过，所以 `allowedTools` 保持空是符合预期的）。
- 跨设备是否同步：`[未查]`——文档中未见任何"settings 跨设备同步"描述；`.claude/settings.local.json` 明确是 gitignore 的本机文件，`~/.claude.json` 也是本机文件。若团队要共享规则，唯一文档化路径是把规则写进会被提交的 `.claude/settings.json`（Project 层），此时会经过 workspace trust 弹窗二次确认（见切面 5）。

**代价**：权限规则"跨层级合并、deny 优先于一切"这条设计意味着任何一层（哪怕是某个人在自己 `~/.claude/settings.json` 里手滑加的一条 deny）都能静默拒绝掉项目组共享的 allow 规则，且没有任何层级能把它覆盖回来——排查"为什么这条命令突然被拒"时，需要检查全部四层文件，`/permissions` 弹窗虽然会列出规则来源文件，但需要用户主动打开去看。`[读到]`

### 5 泛化与匹配（本次调研重心）

**规则语法基本形态**：`Tool` 或 `Tool(specifier)`。裸工具名（如 `Bash`）匹配该工具全部调用；作为 deny 规则时会把该工具从模型可见工具集里整体移除（`EndConversation` 例外，只要还有别的工具在，deny/ask 规则都不能把它拿掉）。`[读到]` https://code.claude.com/docs/en/permissions#permission-rule-syntax

**Bash 规则**：
- `Bash(npm run build)` 精确匹配；`Bash(npm run test *)` 前缀匹配；`Bash(npm *)` 匹配任意以 `npm ` 开头的命令；`Bash(* install)` 匹配任意以 ` install` 结尾的命令；`Bash(git * main)` 中间通配，可跨多个参数（单个 `*` 能匹配含空格的任意字符序列）。`[读到]`
- 尾部空格很关键：`Bash(ls *)` 强制词边界（匹配 `ls -la` 不匹配 `lsof`），`Bash(ls*)` 无空格则不设词边界（两者都匹配）。`[读到]`
- `:*` 后缀等价于末尾 ` *`，但只在**末尾**生效——`Bash(git:* push)` 里的冒号会被当字面字符,不会当通配符解析。`[读到]`
- **复合命令拆分**：Claude Code 能识别 shell 操作符 `&&`、`||`、`;`、`|`、`|&`、`&`、换行，会把复合命令拆成子命令，规则必须对每个子命令独立匹配——`Bash(safe-cmd *)` 不会让 `safe-cmd && other-cmd` 整体放行。用户点"Yes, and don't ask again"批准一条复合命令时，CLI 会**为每个需要审批的子命令分别生成一条规则**（而不是给整条复合字符串生成一条规则），单次复合命令最多落盘 5 条规则。`[读到]` https://code.claude.com/docs/en/permissions#compound-commands
- **归一化/去壳层**：匹配前会剥离固定的一批"包装器"命令——`timeout`、`time`、`nice`、`nohup`、`stdbuf`，以及 shell 内建的 `command`、`builtin`、zsh 的 `noglob`；也会剥离一批"已知安全"的前置环境变量赋值（如 `Bash(npm test *)` 能匹配 `NODE_ENV=test npm test`）。这个剥离列表是**内置且不可配置**的，`direnv exec`、`devbox run`、`npx`、`docker exec` 等"环境运行器"不在剥离列表里，意味着 `Bash(devbox run *)` 这类规则会把 `devbox run rm -rf .` 也一并放行。`[读到]` https://code.claude.com/docs/en/permissions#process-wrappers：原文明确点名了这个陷阱。
- **只读命令白名单**：`ls`、`cat`、`echo`、`pwd`、`head`、`tail`、`grep`、`find`、`wc`、`which`、`diff`、`stat`、`du`、`cd`、只读形式的 `git` 等，在任意模式下都不问，且不可配置（想强制询问需要手写 ask/deny 规则覆盖）。`[读到]`
- **文档明确承认的绕过风险**：文档用整段 `<Warning>` 明说"Bash permission patterns that try to constrain command arguments are fragile"，举了具体反例——`Bash(curl http://github.com/ *)` 不会拦住 `curl -X GET http://github.com/...`（选项在前）、`curl https://github.com/...`（协议不同）、重定向到 GitHub 的短链接、`URL=http://github.com && curl $URL`（变量间接引用）、多余空格 `curl  http://github.com`。文档给出的正规做法是"用 deny 规则整体禁用 curl/wget，改用 WebFetch 工具 + `WebFetch(domain:...)` 做域名白名单"，并再次强调"Bash 若被允许，WebFetch 域名白名单挡不住 Claude 用 curl/wget 绕过网络限制"。`[读到]` https://code.claude.com/docs/en/permissions#redirections 上方 Warning 原文。

**路径规则（Read/Edit）**：与 Bash 语法**不是同一套**，用的是 gitignore 模式语法，四种锚点：
| 写法 | 含义 | 示例 |
|---|---|---|
| `//path` | 文件系统根的绝对路径 | `Read(//Users/alice/secrets/**)` |
| `~/path` | 用户主目录相对 | `Read(~/Documents/*.pdf)` |
| `/path` | 相对于规则所在 settings 文件的"锚点目录"（项目 settings 锚定项目根，local settings 锚定启动目录，user settings 锚定 `~/.claude`） | `Edit(/src/**/*.ts)` |
| `path` 或 `./path` | 相对当前目录 | `Read(*.env)` |

- 明确的反直觉陷阱：`/Users/alice/file` **不是**绝对路径，单斜杠是"相对于 settings 来源锚点"，要用 `//Users/alice/file` 才是真正的文件系统绝对路径。`[读到]` 原文用单独 Warning 强调这一点。
- Windows 上路径会先归一化成 POSIX 形式再匹配（`C:\Users\alice` → `/c/Users/alice`）。`[读到]`
- 单段目录名（如 `src/**`）在 allow 规则和 deny/ask 规则下**匹配深度不同**：allow 规则只匹配当前目录下的 `src/`；deny/ask 规则会匹配任意深度下名为 `src` 的目录（包括嵌套的 `vendor/pkg/src/`）。这是文档明确列出的一张对照表，`[读到]`。
- 符号链接：allow 规则要求"链接路径和目标路径都匹配"才放行（否则退回询问）；deny 规则只要"链接路径或目标路径"任一匹配就拦截——即 deny 对符号链接更保守。`[读到]`
- 用户在弹窗里选"Yes, and don't ask again"批准路径时，CLI 会对路径中的 gitignore 特殊字符（`[`、`]`、`*`）做转义，确保生成的规则只匹配这个具体路径（2.1.202 之前有转义 bug）；但用户**自己手写**的规则不会被转义。`[读到]`

**Deny 与 Ask 相对 Allow 的优先级**：文档给出确定性顺序——"Rules are evaluated in order: deny, then ask, then allow. The first match in that order determines the outcome, and rule specificity doesn't change the order." 也就是说更精细的 allow 规则（如 `Bash(aws s3 ls)`）**不能**在更宽泛的 deny 规则（如 `Bash(aws *)`）面前开洞——deny 不允许有白名单式的例外。`[读到]` https://code.claude.com/docs/en/permissions#manage-permissions

**参数级匹配**（`Tool(param:value)`）只能匹配工具输入的顶层标量字段（如 `Agent(model:opus)`、`Bash(run_in_background:true)`），不能匹配嵌套字段，也不能匹配前述的"主内容字段"（会被启动警告忽略）。比较是对模型发送的**原始字面值**做比较，不做归一化——`Agent(model:opus)` 匹配别名 `opus` 但不匹配完整 model ID。`[读到]`

**代价**：路径规则和 Bash 规则用两套完全不同的通配语法（gitignore vs 自定义 glob），且路径规则里"单段目录名在 allow/deny 下匹配深度不同"这种非对称设计，极容易被写规则的人凭直觉搞反——以为 `Edit(src/**)` 作为 deny 规则也只挡当前目录下的 src，结果它其实挡住了项目里所有名为 src 的目录（包括 vendor 里嵌套的）。这类"看起来对称、实际不对称"的规则是本次调研里最反直觉的发现之一。`[读到]`

### 6 撤销与可审计

- 查看已授权清单的入口是 `/permissions` 斜杠命令：弹出的对话框会列出**全部**权限规则，并标注每条规则来自哪个 `settings.json` 文件。`[读到]` https://code.claude.com/docs/en/permissions#manage-permissions：原文"The dialog lists all permission rules and the `settings.json` file each rule comes from."
- 在 `/permissions` 里可以直接增删规则，且改动会在**同一轮对话内、Claude 下一次工具调用前**立即生效（2.1.234 之前是排队到本轮对话结束才生效）。`[读到]`
- 撤销路径：`/permissions` 里删除对应的 allow 规则，或者直接编辑/删除 `.claude/settings.local.json` 里的那一行——这是纯文本 JSON 文件，没有版本历史或审计日志机制的文档描述。`[读到]`（是否有版本历史：`[未查]`，文档未提及规则变更的审计留痕机制）
- 误批一条过宽规则（比如手滑批了 `Bash(*)`）后的恢复路径：文档只给出"用 `/permissions` 删除或收窄该规则"这一条路径，没有"回滚到上一次已知安全状态"的机制。`[读到]` + `[未查]`（撤销后是否有效追溯"这条宽规则曾经批准放行过哪些具体调用"——文档未描述任何调用历史审计功能，只提到 `ConfigChange` hook 可以在**settings 变更时**触发脚本用于审计/拦截。）
- auto 模式下的"Recently denied"标签页：被 classifier 拦截的动作会出现在 `/permissions` 的 **Recently denied** tab 里，可以按 `r` 重试并转成人工审批。这是一个"事后可见"的记录，但只覆盖 auto 模式下被 classifier 拒绝的动作,不是通用的调用审计日志。`[读到]` https://code.claude.com/docs/en/permission-modes#when-auto-mode-falls-back

**代价**：撤销机制只到"删掉这条规则"为止,没有文档化的"这条过宽规则生效期间到底放行了哪些调用"的审计能力——如果一条 `Bash(npm *)` 被写宽成实际放行了危险命令，事后排查只能靠会话 transcript（`.jsonl` 文件）人工翻，而不是权限模块自带的审计视图。`[读到]`+`[未查]`

### 7 审批 UX

- 展示信息：Bash/PowerShell 弹窗支持按 `Ctrl+E` 展开"命令做什么、Claude 为什么要跑它、可能出什么问题"的解释，并标注 **Low risk / Med risk / High risk**；这个解释是按需生成的（按一次才发一次请求给模型），不是每次弹窗都自动附带。`[读到]` https://code.claude.com/docs/en/permissions#permission-system：原文"Claude Code sends the command and Claude's own description of the call to the model to generate the explanation only when you press `Ctrl+E`, not on every prompt."
- 选项集合：文档没有给出一张统一的"选项 1/2/3"表，而是按场景描述具体文案，已确认存在的具体选项文案包括：
  - `.claude/` 写入弹窗："Yes, and allow Claude to edit its own settings for this session"（会话内后续 `.claude/` 写入不再问）
  - Plan 模式审批计划时三选一：**Yes, and use auto mode**（若 auto 不可用则文案变为 **Yes, auto-accept edits**；若会话启用了 bypass permissions 则变为 **Yes, and switch to BYPASS PERMISSIONS (no further prompts) for this session**）/ **Yes, manually approve edits** / **No, keep planning**
  - 常规 Bash/路径弹窗的"don't ask again"选项：文档统一称为"Yes, and don't ask again"，但**并非每次都提供**——命令或编辑内容太大、无法在选项文案里完整展示时，CLI 会砍掉这个选项，只留一次性批准。`[读到]`
  - 一次性批准的具体文案（如"Yes"/"No"）：文档未给出逐字符串，`[未查]`——需要在真实交互终端里截图确认精确措辞。
- 默认选中项：`[未查]`——文档未说明弹窗默认高亮哪个选项。
- 超时行为：`[未查]`——文档未描述人工弹窗本身的超时机制；能查到的相关但不同的机制是 auto 模式下 classifier 请求失败/重试的行为（`system/api_retry` 事件），这属于模型请求超时，不是权限弹窗超时。
- 批量审批呈现：没有文档化的"批量勾选多条待审批规则"UI；批量效果是通过复合命令的"每个子命令生成一条落盘规则（最多 5 条）"这种事后拆分实现的，而不是一次弹窗里勾选多条。`[读到]`

**代价**：选项集合会因内容大小而**动态变化**（有时给三选项，有时降级成一次性批准），如果产品经理把"用户总能一键永久放行"当作稳定交互假设去设计上层引导文案，会在大 diff/长命令场景下失真。`[读到]`+`[未查]`

### 8 无人值守降级

- 默认起始模式：`claude -p`（非交互）和 Agent SDK 会话的**内置默认**都是 Manual（`default`），即使交互式会话在 Pro/Max/Team 计划下默认是 `auto`，`-p` 也不继承这个 auto 默认。`[读到]` https://code.claude.com/docs/en/permission-modes#which-mode-a-session-starts-in 表格："`claude -p` or the Agent SDK → Built-in starting permission mode: `default`"
- 由于 Manual 模式下大多数操作都要问用户，而 `-p` 模式**不会**弹出交互式确认（也不会弹 workspace trust 对话框），所以非交互模式下"该问却问不出口"的操作默认结果是**跑不动/报错**，除非显式传：
  - `--allowedTools "Bash,Read,Edit"`（对具体工具做白名单）
  - `--permission-mode auto`（classifier 复核代替人工）
  - `--permission-mode dontAsk`（未落地 allow 规则的一律拒绝，适合"精确白名单跑 CI"）
  - `--permission-mode acceptEdits`
  - `--dangerously-skip-permissions` / `--permission-mode bypassPermissions`（完全跳过权限检查，等价旗标）
  `[读到]` https://code.claude.com/docs/en/headless#auto-approve-tools
- bypass 类开关的护栏：
  - 交互式会话第一次启用 `bypassPermissions` 时会弹一次性警告对话框要求用户"接受责任"，接受后写入 user settings，之后不再弹；**非交互模式下这个对话框根本不显示**，`--bg` 后台会话如果之前从未在交互式会话里接受过这个对话框，会被直接拒绝启动。`[读到]` https://code.claude.com/docs/en/permission-modes#skip-all-checks-with-bypasspermissions-mode：原文"In non-interactive mode no dialog is shown, and a background session started with `--bg` is refused until you've accepted the dialog in an interactive session."
  - Linux/macOS 上以 root/sudo 运行会被硬拒绝启动 bypass 模式（"cannot be used with root/sudo privileges for security reasons"），在被识别的沙箱环境里这条检查会自动跳过。`[读到]`
  - 管理员可以用 managed settings 里的 `permissions.disableBypassPermissionsMode` / `permissions.disableAutoMode` 硬关闭这两种模式，且这两个 key 处于"managed 设置任何一层设了就不能被覆盖"的例外名单里。`[读到]`
  - `bypassPermissions` 模式下仍有两条"任何模式都不自动批准"的硬底线不能被跳过：`rm`/`rmdir` 命中 critical path（如 `rm -rf /`、`rm -rf ~`）依然会弹窗；跨会话消息（cross-session messaging）的 `isolatePeerMachines` 审批和"未声明策略时的入站消息拦截"也依然生效。`[读到]`
- fail-safe 朝哪边倒：**不是简单的"倒向拒绝"**，而是分层的：Manual 模式默认拒绝未授权操作（fail-closed）；但一旦用户显式选择了 `bypassPermissions`/`dangerously-skip-permissions`，系统整体转向 fail-open（除极少数硬编码底线外全部放行），且文档明确用大写 Warning 强调"`bypassPermissions` offers no protection against prompt injection or unintended actions"、"Only use this mode in isolated environments like containers, VMs, or dev containers without internet access, where Claude Code cannot damage your host system."。`[读到]`
- 本地实测发现：本机 `~/.claude/settings.json` 里 `"permissions": {"defaultMode": "bypassPermissions"}` 且额外设置了 `"skipDangerousModePermissionPrompt": true`、`"skipAutoPermissionPrompt": true`。结合文档"首次启用 bypass 会弹一次性警告，接受后写入 user settings 不再弹"的描述，`skipDangerousModePermissionPrompt` 极可能就是那次"已接受责任声明"的落盘标记；`skipAutoPermissionPrompt` 结构上类似，推测对应"是否切到 auto 模式"的一次性询问被跳过的标记。`[推断]`——文档没有直接点名这两个具体 key 是做什么用的，是基于命名和行为描述的合理推断，不排除是其他内部用途。

**代价**：`-p`/CI/SDK 场景下"默认起始模式是 Manual 但又没有交互式弹窗"这个组合，意味着一个没读文档、直接把交互式脚本原样搬进 CI 的团队，大概率会遇到"权限卡住、进程挂起或直接报错"，而不是优雅降级；反过来如果为了让 CI 跑通就图省事全局加 `--dangerously-skip-permissions`，又会把 fail-safe 方向从"拒绝"整体扳到"放行"，代价是失去 prompt injection 防护——这是文档自己承认的，不是我的推断。`[读到]`

## 时序

以"交互式会话里，用户第一次要求 Claude 运行 `npm run test:xyz`，随后选择永久放行"为例：

```
1. 用户输入自然语言指令
2. 模型规划出 Bash 工具调用: command = "npm run test:xyz"
3. PreToolUse hook(s) 依次触发 (若配置了 matcher 命中 Bash 的 hook)
   - hook 可以在这一步就 deny (exit 2 或 permissionDecision: deny)
   - 若 hook 未拦截, 进入下一步
4. 权限规则匹配: 依次检查 deny -> ask -> allow 规则列表
   - 若命中已有 allow 规则(如之前批准过的 Bash(npm run test *)), 直接放行, 跳到第7步
   - 若无匹配规则, 进入第5步
5. 按当前 permission mode 分流:
   - default: 触发用户弹窗
   - acceptEdits: 若不属于文件编辑/白名单文件系统命令, 仍触发弹窗
   - auto: 交给 classifier 模型复核, 复核通过则放行, 拒绝则回退给 Claude 换策略
   - dontAsk: 直接拒绝(不弹窗)
   - bypassPermissions: 直接放行(硬底线命令除外)
6. 用户弹窗 (若走到这一步):
   展示命令原文 + 风险等级(按 Ctrl+E 才展开原因)
   用户选择 "Yes" / "Yes, and don't ask again" / "No"
   若选 "don't ask again": 复合命令按子命令拆分, 各自生成一条规则,
     写入 <git 仓库根>/.claude/settings.local.json
7. 工具执行, 结果返回给模型
8. 下一次同一仓库里再调用匹配的 npm run test:* 命令:
   直接命中第4步落盘的 allow 规则, 全程不再触发弹窗
```

## 明确不做什么

- 权限规则不做语义理解，只做字符串/AST 级别的模式匹配；对"这条命令实际会不会造成危害"的判断，Manual/acceptEdits/dontAsk/bypassPermissions 四种模式完全不做，只有 `auto` 模式引入的 classifier 才做语义层面的复核，且该 classifier 只读消息、工具调用记录和 CLAUDE.md，**不读工具执行结果**（避免被文件/网页里的恶意内容直接操纵）。`[读到]`
- 权限系统不提供跨设备/跨机器的规则同步；`.claude/settings.local.json` 和 `~/.claude.json` 都是纯本机文件。`[推断]`（文档未直接否定同步存在，但通篇未提及任何同步机制，且明确描述这些文件是 gitignore/本机专属）
- Read/Edit 的 deny 规则不能拦截"间接读写文件"的任意子进程（比如 Python/Node 脚本自己 open() 文件）——只拦 Claude 内置文件工具和它识别出的 Bash 文件命令（`cat`/`head`/`tail`/`sed` 等）。要做进程级强制隔离，文档明确指向另一个独立机制（sandboxing），不是权限模块的职责。`[读到]` https://code.claude.com/docs/en/permissions#read-and-edit
- 权限模块不提供"调用历史审计日志"这种一等公民功能；`/permissions` 只展示**当前生效的规则清单**和 auto 模式下**最近被 classifier 拒绝**的动作，不提供"某条 allow 规则历史上放行过哪些具体调用"的回溯视图。`[读到]`+`[未查]`

## 未确认项汇总

- 常规审批弹窗（非 plan 模式、非 `.claude/` 写入这类特殊场景）里"一次性批准"选项的确切文案（如是否叫"Yes"）、以及弹窗默认高亮哪个选项。去向：需要在真实交互终端里手动触发一次弹窗截图确认（本次任务被要求"实测限于只读命令"，未做交互式触发）。
- 人工审批弹窗本身是否存在超时机制（无人响应多久后自动拒绝/终止）。去向：文档未见描述，需查阅是否有相关 issue/changelog，或实测挂起观察。
- 跨设备/跨机器权限规则是否有任何同步机制（比如通过 Anthropic 账号云端同步 user settings）。去向：文档通篇未提及，可能需要直接询问 Anthropic 支持或翻查 `claude update`/账号设置相关文档页面。
- `~/.claude/settings.json` 里 `skipDangerousModePermissionPrompt`、`skipAutoPermissionPrompt` 两个 key 的确切语义，本报告基于命名和文档描述的"一次性警告接受后落盘"机制做了推断，未在官方 settings 参考页面里找到这两个 key 的逐字定义。去向：`https://code.claude.com/docs/en/settings` 的 "Available settings" 完整表格（本次因输出过大只读到 WebFetch 生成的摘要，未逐字核对该表格的原始逐条定义）。
- `/permissions` 弹窗是否支持"批量勾选多条待审批规则一次性处理"，文档只描述了单条规则的增删和 auto 模式下 Recently denied 的单条重试，未见批量操作的描述。去向：需要实机在 `/permissions` 界面里操作确认。
- 误批过宽规则后，是否存在任何"该规则历史上放行了哪些具体调用"的回溯能力。去向：文档未提及，可能需要翻会话 transcript（`~/.claude/projects/<project>/*.jsonl`）人工核对，或确认是否有 OpenTelemetry 监控（`/docs/en/monitoring-usage`，本次未展开调研）能起到审计作用。

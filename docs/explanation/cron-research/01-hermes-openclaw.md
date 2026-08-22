# Hermes Agent / OpenClaw 定时任务机制调研报告

## 元信息

- **调研对象**：Hermes Agent、OpenClaw 两个 agent 系统的 cron（定时任务）子系统
- **调研日期**：2026-08-22
- **路线**：白盒，全部结论来自本地源码通读
- **代码基线**：
  - Hermes Agent：`~/repositories/hermes-agent` @ `81928f03a`（2026-05-08）
  - OpenClaw：`~/repositories/openclaw` @ `09e471f32e`（2026-05-08）
- **主要依据文件**：
  - Hermes：`cron/scheduler.py`（1740 行）、`cron/jobs.py`（1050 行）、`cron/__init__.py`、`tools/cronjob_tools.py`（662 行）、`tools/approval.py`、`gateway/run.py`
  - OpenClaw：`src/cron/`（约 90 个文件）、`src/agents/tools/cron-tool.ts`（944 行）、`src/agents/pi-tools.ts`、`src/agents/openclaw-tools.ts`、`src/gateway/server-methods/cron.ts`、`docs/automation/cron-jobs.md`
- **本报告范围**：只写这两家的实现机制。不含选型建议，不含对第三方系统的移植建议。

---

## 0. 主线

> **两家的 cron 都不是"定时器 + 调用 agent"。它们是把"无人在场"实现成了一种独立的运行模式。** 计算下次运行时间加上到点触发这件事，在两家各自的 cron 模块里都占不到六分之一的代码；剩下的全部用来回答四个问题——这一轮由谁发起、带什么上下文进去、权限比人在场时窄多少、跑完的话说给谁听。

这句可证伪：只要任一家的 cron 模块里，"调度 + 触发"以外的代码不足一半，主线即被推翻。实际情况是 Hermes 的 `cron/` 共 2832 行，其中调度语义（`parse_schedule` / `compute_next_run` / `get_due_jobs` / `tick` 的锁与推进部分）约 400 行；OpenClaw 的 `src/cron/` 里 `schedule.ts` + `stagger.ts` + `armTimer` 合计约 350 行，而 `isolated-agent/` 一个子目录就有 60 多个文件。

由此得到本报告的组织方式：每一家都按「调度 → 执行 → 权限 → 投递 → 失败」五段展开，因为这正是两家代码量的实际分布。

---

# 第一部分：Hermes Agent

## 1.1 定位与部署形态

Hermes 的 cron 是一个**内置的、基于 JSON 文件的调度器**，由 gateway 守护进程驱动。模块自己的 docstring 说明了它存在的理由：让 agent 能跑自动化任务、能自己排期提醒与后续任务、能在隔离会话（无历史上下文）里执行。

部署形态只有一种：gateway 起一个后台线程，每 60 秒调用一次 `tick()`。没有独立的 cron 进程，也不依赖系统 crontab——工具的可用性检查函数里明确写了"cron 系统是内部的 JSON 文件调度器，不需要外部 crontab 可执行文件"。

```
  gateway 进程
  +-------------------------------------------+
  |  主循环（聊天平台适配器、HTTP 等）        |
  |                                           |
  |  后台线程: 每 60s -> cron.scheduler.tick() |
  |                        |                  |
  |                        v                  |
  |            ~/.hermes/cron/.tick.lock      |
  |            ~/.hermes/cron/jobs.json       |
  |            ~/.hermes/cron/output/<id>/    |
  +-------------------------------------------+
```

文件锁的存在是因为 tick 有三个可能的调用方：gateway 的进程内定时线程、独立守护进程、以及人工触发。锁保证同一时刻只有一个 tick 在跑，拿不到锁的直接返回 0，不排队。

**代价**：60 秒的固定 tick 意味着调度精度上限就是分钟级，且每次 tick 都要读一次 `jobs.json` 全量。任务多了之后这是纯线性开销，但换来的是没有任何常驻内存状态——进程随时可以重启。

## 1.2 数据模型

**存储位置**：

| 路径 | 内容 |
|---|---|
| `~/.hermes/cron/jobs.json` | 全部 job 的定义 **和** 运行态，单文件 |
| `~/.hermes/cron/output/<job_id>/<时间戳>.md` | 每次运行的完整产出文档 |
| `~/.hermes/cron/.tick.lock` | tick 互斥锁 |
| `~/.hermes/scripts/` | job 可引用的脚本目录（唯一允许的脚本位置） |

注意 Hermes **没有把定义和运行态分开**——`last_run_at`、`last_status`、`next_run_at`、`repeat.completed` 全都写在同一个 `jobs.json` 里。写入走 `tempfile` + `fsync` + 原子替换，目录和文件都会被设权限（`_secure_dir` / `_secure_file`）。

**一条 job 的字段**（从创建路径和消费点归纳）：

- 身份：`id`（12 位十六进制）、`name`、`enabled`、`state`（scheduled / paused / completed / error）
- 调度：`schedule`（结构化，见下节）、`schedule_display`（给人看的字符串）、`next_run_at`、`repeat.{times, completed}`
- 内容：`prompt`、`skills`（有序列表）、`script`、`context_from`、`no_agent`
- 运行环境：`model`、`provider`、`base_url`、`enabled_toolsets`、`workdir`
- 投递：`deliver`（字符串，支持逗号分隔多目标）、`origin`（创建时捕获的平台/会话）
- 运行态：`last_run_at`、`last_status`、`last_error`、`last_delivery_error`

`last_delivery_error` 和 `last_error` 分开存，注释写明了原因：一个 job 可以 agent 成功（产出了内容）但投递失败（平台挂了），这是两种不同的故障，混在一起用户无法判断该修哪个。

## 1.3 调度语义

**输入形态**。`parse_schedule` 接受一个字符串，按顺序尝试四种解析：

1. `every ` 前缀 → 间隔型。后面跟时长（`30m` / `2h` / `1d`，正则严格匹配单位）
2. 5 个及以上空格分隔字段且前 5 段只含 `数字 * - , /` → cron 表达式，交给 `croniter` 校验
3. 含 `T` 或形如 `YYYY-MM-DD` → ISO 时间戳，一次性
4. 纯时长（`30m`）→ 从现在起算的一次性

解析结果归一成三种 kind：`once`（带 `run_at`）、`interval`（带 `minutes`）、`cron`（带 `expr`）。

**时区处理**。ISO 时间戳如果不带时区，在**解析时**就用 `astimezone()` 转成本地时区并存下来——注释说明这是为了让存下来的值不依赖"检查时系统时区是否还一样"。历史遗留的 naive 时间戳按"创建时的系统本地墙上时间"解释，再转到 Hermes 配置时区。cron 表达式本身没有独立时区字段，跟随进程时区。

**下次运行的计算**（`compute_next_run`）：

- `once`：只有在还没跑过（`last_run_at` 为空）且预定时间不早于「现在 - 120 秒宽限」时才返回时间，否则返回 None（永久失效）
- `interval`：有上次运行就是 `上次 + 间隔`，没有就是 `现在 + 间隔`
- `cron`：**以上次运行时间为基准**推进，没有上次运行才用现在。注释写明这是为了让崩溃重启后锚定在真实的上次执行，而不是任意的重启时刻

**错过窗口的处理**（`_compute_grace_seconds` + `get_due_jobs`）。这是 Hermes 最有设计感的一块：宽限期不是固定值，而是**调度周期的一半，钳制在 120 秒到 2 小时之间**。

```
  daily job (86400s)  -> 周期一半 43200s -> 钳到 7200s (2 小时)
  hourly job (3600s)  -> 周期一半 1800s  -> 1800s (30 分钟)
  every 10m (600s)    -> 周期一半 300s   -> 钳到 120s (最小值)
```

超过宽限期的到期任务被判定为"陈旧的错过运行"，直接快进到下一个未来时刻，**这一轮不跑**。设计意图写在注释里：防止 gateway 重启时爆发一堆积压任务。

**至多一次的保证点**（`advance_next_run`）。tick 拿到锁后，**先把所有到期的循环任务的 `next_run_at` 全部推进，再开始执行**。函数 docstring 直说：这把调度器从至少一次转成了至多一次，理由是"漏掉一次远好于崩溃循环里触发几十次"。一次性任务不推进，所以它们在重启后还能重试。

**恢复路径**。如果一条循环任务的 `next_run_at` 是空的（典型场景：有人手改了 `jobs.json` 绕过了创建路径），`get_due_jobs` 会从 schedule 重新算一个并回写。没有这个分支，这类任务会被永久静默跳过。

## 1.4 tick 主循环

```
  tick()
   |
   +- 拿文件锁（拿不到 -> 直接 return 0，不排队）
   |
   +- get_due_jobs()          # 含快进陈旧任务、恢复丢失的 next_run_at
   |
   +- 对所有到期任务 advance_next_run()   # 至多一次的保证点
   |
   +- 按 workdir 划分:
   |    有 workdir -> 顺序执行（因为要改进程全局的 TERMINAL_CWD）
   |    无 workdir -> 线程池并行（上限来自环境变量 > config.yaml > 无上限）
   |
   +- 每个任务: run_job -> 存产出 -> 投递 -> mark_job_run
   |
   +- 全部结束后: 清理孤儿 MCP 子进程
   |
   +- 释放锁
```

并发的划分依据非常具体：带 `workdir` 的任务在 `run_job` 里会改 `os.environ["TERMINAL_CWD"]`，这是进程全局的，所以**必须串行**；不带 `workdir` 的任务不碰环境变量，可以并行。每个任务都在 `contextvars.copy_context()` 里跑，这样 ContextVar 形式的会话/投递状态不会互相污染。

并发上限的默认值是**无上限**——设成 1 可以恢复旧的串行行为。

MCP 孤儿进程的清理放在**所有任务跑完之后**，注释说明理由：只有这样才能保证不误杀仍然活跃的会话（包括真人的聊天会话），被清理的只有明确标记为孤儿的 PID。

## 1.5 执行路径 A：纯脚本模式（no_agent）

这条路径在 `run_job` 的最前面短路，**在导入 agent 机器之前**。注释写明这是刻意的：一次纯脚本 tick 不应该为它用不到的 `AIAgent` / `SessionDB` 构造付代价。

语义是经典 watchdog：

| 脚本结果 | 行为 |
|---|---|
| stdout 非空 | 原样作为消息投递 |
| stdout 为空 | 静默——什么都不发，用户看不到发生过任何事 |
| 最后一行是 `{"wakeAgent": false}` | 同上，静默 |
| 非零退出 / 超时 | 投递一条错误告警（"watchdog 自己坏了"必须让人知道） |

工具描述里对这个设计有一段很直白的说明：空 stdout 意味着静默，所以"把你的脚本设计成没事的时候不出声"。

`workdir` 在这条路径上只是子进程的 cwd，不涉及 agent 的工具桥接。

## 1.6 执行路径 B：LLM 模式

这是主路径，顺序如下。

**第 1 步：唤醒门（wake gate）**。如果 job 配了 `script`，脚本**先于 prompt 组装**执行。脚本 stdout 的最后一个非空行如果能解析成 `{"wakeAgent": false}`，整个 agent 运行被跳过，返回静默。脚本结果会传给下一步复用，不会执行两次。

脚本执行本身有几层约束：
- 路径必须落在 `~/.hermes/scripts/` 内。相对路径、绝对路径、`~` 开头一律 resolve 后用 `relative_to` 校验，防路径穿越和符号链接逃逸
- 解释器**按扩展名决定**，`.sh`/`.bash` 走 bash，其余走当前 Python 解释器。注释明确说：**故意不遵循文件自己的 shebang**，为的是让允许的执行面小且可审计
- stdout 和 stderr 在任何返回路径之前都过一遍密钥脱敏
- 超时可配（模块变量 > 环境变量 > config.yaml > 默认值）

**第 2 步：prompt 组装**（`_build_job_prompt`）。按以下顺序层层前置：

```
  [注入扫描] <- 最终组装结果
      ^
      |
  cron 执行须知（固定文案，总是最前）
      +
  skill 内容（按 skills 列表顺序，每个前面加一句"用户调用了这个 skill"）
      +
  上游 job 产出（context_from，每个截断到 8000 字符）
      +
  脚本输出（成功则作为"Script Output"上下文；失败则作为"Script Error"并要求上报）
      +
  用户 prompt
```

固定的执行须知文案包含三条硬指令：（a）你的最终回复会被自动投递，不要自己调用发消息工具；（b）真的没什么可报的就回复恰好 `[SILENT]`；（c）**绝不允许把 `[SILENT]` 和内容混在一起**。第三条的存在说明模型确实会这么干。

`context_from` 的 job id 有独立校验：必须是纯十六进制字符（这就是防路径穿越，因为 id 会被拼进目录路径）；上游没有产出就静默跳过，不往 prompt 里塞错误信息。

skill 加载失败不会让整个 job 失败——被跳过的 skill 名会被收集起来，在 prompt 最前面插一条要求 agent 在回复开头告知用户。

**第 3 步：组装后的注入扫描**（`_scan_assembled_cron_prompt`）。这是全报告里最值得单独记住的一处设计。

扫描器本身（`_scan_cron_prompt`）是 10 条正则加一组不可见 Unicode 字符检测，覆盖：指令覆盖类（"忽略之前的指令"、"系统提示词覆盖"、"无视你的规则"）、欺骗类（"不要告诉用户"）、外泄类（`curl`/`wget` 拼接含 KEY/TOKEN/SECRET 的变量、`cat` 读 `.env`/`.netrc`/`.pgpass`）、后门类（`authorized_keys`、`/etc/sudoers`）、破坏类（`rm -rf /`）。

关键在于**扫两次**。第一次在创建/更新时扫用户填的 prompt；第二次在每次执行前扫**完全组装好的**结果。第二次的存在理由写在异常类的 docstring 里：创建时的扫描只覆盖用户提供的 prompt 字段，而 skill 内容是运行时从磁盘加载的，从来没被扫过——一个恶意 skill 可以携带注入载荷，直达这个非交互（自动批准）的 cron agent。

命中后不是静默跳过，而是抛出专用异常，`run_job` 捕获后生成一份带 `Status: BLOCKED` 的运行报告，里面写明扫描结果、要求操作者审计挂在这个 job 上的 skill、以及误报时该怎么改。

**第 4 步：会话与上下文变量**。

- 会话 id 形如 `cron_<job_id>_<YYYYmmdd_HHMMSS>`，写进 SQLite 会话库，这样 cron 产生的消息可以被 `session_search` 检索到
- 设置进程级环境变量标记这是 cron 会话（供审批系统识别）
- 会话来源（平台/会话 id/会话名）和投递目标用 **ContextVar** 存，不用环境变量。注释写明理由：并行 job 会互相覆盖 `os.environ`
- `workdir` 是唯一的例外——它必须走 `os.environ["TERMINAL_CWD"]`，因为下游的上下文文件加载和终端/文件/代码执行工具都读这个。这就是 tick 必须把带 workdir 的任务串行化的原因，`finally` 块负责还原原值

**第 5 步：运行时配置重读**。每次运行都重新 `load_dotenv(override=True)` 和读 `config.yaml`，注释说明目的：改了 provider 或 key 不用重启 gateway 就能生效。

**第 6 步：模型与 provider 解析**。优先级是 job 上的 `model`/`provider` → `HERMES_MODEL` 环境变量 → config.yaml 的 `model.default`。provider 解析失败（认证错误）时会遍历 `fallback_providers` 逐个尝试。这里有一条注释值得注意：**不注入 `HERMES_INFERENCE_PROVIDER` 环境变量**，因为那会短路"持久化配置优先于陈旧 shell 环境变量"的既定优先级，把老 provider 复活。

**第 7 步：工具集解析**（`_resolve_cron_enabled_toolsets`）。三级优先级：job 上的 `enabled_toolsets` → `cron` 这个"平台"的全局工具配置 → None（加载全量默认集）。注释里记了一个真实事故：默认关闭集里包含 `moa`，是因为有用户因为它产生了一次意外的 $4.63 账单。

**第 8 步：agent 构造**。关键参数：

- `disabled_toolsets=["cronjob", "messaging", "clarify"]` —— **硬关掉三类工具**：不能递归排期、不能自己发消息（投递由框架负责）、不能提问（没人可答）
- `skip_context_files=not bool(workdir)` —— 没有 workdir 就不做当前目录的上下文发现
- `load_soul_identity=True` —— cron 任务仍然继承用户的身份设定
- `skip_memory=True` —— 注释：cron 的系统提示词会污染用户画像
- `quiet_mode=True`、`platform="cron"`

**第 9 步：超时**。用的是**不活动超时**而非总时长。实现方式是把 `run_conversation` 提交到一个单线程池，主线程每 5 秒轮询一次 agent 的活动追踪器（每次工具调用、API 调用、流式增量都会刷新）。空闲超过阈值（默认 600 秒，环境变量可覆盖，0 表示不限）则调用 agent 的中断方法并抛 `TimeoutError`。超时日志里带完整诊断：最后一次活动描述、空闲秒数、当前迭代数/上限、当前工具名。

提交任务时用 `contextvars.copy_context()`，注释说明是为了让 skill 声明的环境变量透传注册能跟着跳进工作线程。

**第 10 步：结果判定**。三道关：

1. 返回值不是 dict → 直接抛错
2. 返回值里 `failed=True` 或 `completed=False` → 抛错。注释记了这个补丁的来由：agent 在重试耗尽、模型中止、运行中断这些路径上会把错误文本放进 `final_response`，不拦的话会被当成正常回复投递出去，而且 job 状态会被记成 ok
3. `final_response` 恰好等于 `"(No response generated)"` → 清空（上游注入的占位符）

回到 tick 层还有第四道：`success=True` 但 `final_response` 为空，被降级为软失败，状态不记 ok，错误信息是"agent 完成但产出为空（模型错误、超时或配置问题）"。

**第 11 步：资源清理**（`finally`）。还原 `TERMINAL_CWD`、清 ContextVar、结束并关闭 SQLite 会话、调用 `agent.close()`、清理陈旧的异步 HTTP 客户端。`agent.close()` 那一段注释记了一个真实事故：不关的话，每 N 分钟 tick 一次的 gateway 会每个 job 泄漏一批文件描述符，直到 EMFILE（"too many open files"）。最后一段清理的是那些缓存在已死事件循环下的异步 httpx 客户端。

## 1.7 权限与注入防护

Hermes 的 cron 权限有两层，方向相反：

**软层——prompt 里的指令**。执行须知里写了"不要自己投递"，工具描述里写了"cron 会话不应该递归创建更多 cron 任务"。

**硬层——直接关工具、直接拒执行**。`disabled_toolsets` 把 cronjob/messaging/clarify 三类工具从注册表里摘掉，模型看不见就调不了。审批系统层面，`approvals.cron_mode` 的**默认值是 `deny`**：cron 会话撞到危险命令直接拒绝，错误信息里会告诉用户可以在 config.yaml 里改成 approve。测试文件里有一条专门断言：`cron_mode=approve` **不能**绕过 hardline 黑名单——也就是说这个开关只能放宽到"自动批准可批准的操作"，不能放宽到"什么都能干"。

**投递目标的枚举防护**。用户提供的平台名会先对一个已知平台白名单校验，注释写明目的：防止通过构造平台名枚举环境变量（因为平台名会被拼成 `<PLATFORM>_HOME_CHANNEL` 去读环境变量）。

## 1.8 投递

`deliver` 字段是一个字符串，支持这些形态：

| 值 | 含义 |
|---|---|
| 省略 / `origin` | 回创建时捕获的那个会话（含话题/线程 id） |
| `local` | 不投递，只落盘 |
| `telegram` | 该平台配置的 home 频道 |
| `telegram:-1001234:17585` | 显式平台 + 会话 + 线程 |
| `a,b,c` | 逗号分隔多目标，去重后逐个投递 |

`origin` 解析不出来时（典型场景：job 由脚本或 API 创建，没有会话上下文）会遍历各平台的 home 频道兜底，而不是静默丢弃。

工具描述里对 `deliver` 有一句加粗的警告：`platform:chat_id` 不带 `:thread_id` 会丢掉话题定位——这说明"提醒发到了群里但不在原来那个话题下"是个真实痛点。

历史兼容：`deliver` 曾经被某些调用方（MCP 客户端传数组、手改 jobs.json）存成列表，`str(["telegram"])` 会变成字面量 `"['telegram']"` 从而静默解析失败，所以现在有一个归一化函数把列表拍平成逗号分隔字符串。

**静默协议**：agent 返回的内容里出现 `[SILENT]`（大写比较）就跳过投递，但**产出仍然落盘**。失败的任务总是投递（错误告警不受静默影响）。

## 1.9 agent 可见的工具面

单个工具 `cronjob`，七个 action（create / list / update / pause / resume / remove / run）。设计注释直说目的：压缩成一个动作型工具，避免 schema 和上下文膨胀。

工具描述里的行为指令值得逐条记：

- "要停掉用户不想要的任务：先 list 找到 job_id，再用那个 id remove。**绝不要猜 job ID——永远先 list**"
- "任务跑在没有当前聊天上下文的新会话里，所以 prompt 必须自包含"
- "agent 的最终回复会被自动投递到目标。把主要的、面向用户的内容放进最终回复"
- "cron 任务自主运行，没有用户在场——它们无法提问或请求澄清"
- "重要安全规则：cron 运行的会话不应该递归创建更多 cron 任务"

`no_agent` 参数的描述是全部字段里最长的，专门用了"什么时候用 True / 什么时候用 False"两段对照：脚本本身就能产出确切消息文本的（内存/磁盘/GPU 看门狗、阈值告警、心跳、CI 通知、输出形状固定的 API 轮询）用 True；需要推理的（总结信息流、起草简报、挑有意思的条目、把数据改写成人话、按内容做条件判断）用 False。

创建时的校验：`no_agent=True` 必须有 script；否则必须有 prompt 或至少一个 skill；prompt 过注入扫描；script 路径过目录校验；`context_from` 引用的 job 必须存在。

## 1.10 Hermes 失败态汇总

| 触发 | 结果状态 | 是否投递 | 备注 |
|---|---|---|---|
| 拿不到 tick 锁 | 无（返回 0） | 否 | 不排队，等下一个 60 秒 |
| 超过宽限期的陈旧到期 | 快进到下次 | 否 | 这一轮完全跳过 |
| 唤醒门返回 false | 成功 + 静默 | 否 | 产出文档记为 "Script gate returned wakeAgent=false" |
| 脚本产出为空（LLM 模式） | 成功 + 静默 | 否 | 直接不调 LLM |
| 组装后 prompt 命中扫描器 | 失败 | 是（错误告警） | 产出文档标 BLOCKED，含审计指引 |
| agent 不活动超时 | 失败 | 是（错误告警） | 中断 agent，日志含完整诊断 |
| agent 自报失败 | 失败 | 是（错误告警） | 防止错误文本被当回复投递 |
| agent 成功但回复为空 | 降级为失败 | 是（错误告警） | tick 层的兜底判定 |
| agent 回复含 `[SILENT]` | 成功 | 否 | 仍然落盘 |
| 投递本身失败 | 保持原状态 | — | 单独记 `last_delivery_error` |
| 循环任务算不出下次运行 | state=error 但**保持 enabled** | — | 注释：绝不能让缺依赖变成"任务完成" |
| 一次性任务算不出下次运行 | enabled=false, state=completed | — | 正常终态 |
| 达到 repeat 次数上限 | 从存储中删除 | — | — |

## 1.11 Hermes 的代价

| 决策 | 代价 |
|---|---|
| 单文件存定义+运行态 | 简单，但定义无法安全地进版本控制（每次运行都改这个文件） |
| 60 秒固定 tick | 无常驻状态、随时可重启，但精度只到分钟且每次全量读 |
| 先推进再执行 | 至多一次，但执行中崩溃这一轮就丢，无补偿 |
| 宽限期按周期一半自适应 | 日级任务能容忍 2 小时延迟、分钟级任务快速快进；代价是同一套代码里两类任务的行为差异很大，用户不看文档预测不出来 |
| workdir 走进程全局变量 | 复用了全部下游工具的既有路径，代价是这类任务只能串行 |
| 并发默认无上限 | 吞吐好，代价是一次 tick 里 20 个到期任务会同时开 20 个 LLM 会话 |
| 不活动超时而非总时长 | 长任务不被误杀，代价是真正的死循环（一直在调工具但不收敛）永远不会超时，只能靠 `max_turns` 兜 |
| 组装后二次扫描 | 堵住 skill 注入，代价是每次执行多一次全文正则扫描，且误报会让任务直接不跑 |
| 正则式威胁模式 | 实现简单、无外部依赖，代价是绕过成本极低（换个说法就过了），只能拦住直白的载荷 |
| `cron_mode` 默认 deny | 无人值守不误伤，代价是需要提权的任务静默失败，用户必须去看运行历史才知道原因 |

---

# 第二部分：OpenClaw

## 2.1 定位与部署形态

OpenClaw 的 cron 跑在 **Gateway 进程内**（文档第一句就强调"不在模型里"）。它不是 tick 轮询，而是**自我重新武装的定时器链**：算出最近的一个下次运行时刻，`setTimeout` 到那个点，触发后再重新武装。

```
  Gateway 进程
  +--------------------------------------------------------+
  |  cron service state { store, timer, running }           |
  |        |                                                |
  |     armTimer() -- 算 nextWakeAtMs --> setTimeout        |
  |        ^                                   |            |
  |        |                                   v            |
  |        +----------------------------- onTimer()         |
  |                                            |            |
  |                                            +- 主会话路径 |
  |                                            +- 隔离路径   |
  |                                                         |
  |  ~/.openclaw/cron/jobs.json        (定义)               |
  |  ~/.openclaw/cron/jobs-state.json  (运行态)             |
  |  run log (每 job 一份，JSONL，可裁剪)                    |
  +--------------------------------------------------------+
```

关闭方式：`cron.enabled: false` 或环境变量 `OPENCLAW_SKIP_CRON=1`。

## 2.2 数据模型：定义与运行态分离

这是 OpenClaw 和 Hermes 最直观的结构差异。

| 文件 | 内容 | 是否建议进 git |
|---|---|---|
| `~/.openclaw/cron/jobs.json` | job 定义 | 是 |
| `~/.openclaw/cron/jobs-state.json` | 待运行槽位、活跃标记、上次运行元数据、调度身份 | 否 |

state 文件路径是从 store 路径派生的：`.json` 结尾的替换成 `-state.json`，否则直接追加 `-state.json`。

**调度身份（schedule identity）**。这是分离方案的关键配套。它把 job 的调度相关字段（kind、at、everyMs、anchorMs、expr、tz、staggerMs）归一化成一个身份串存进 state 文件。当 `jobs.json` 被外部编辑后，系统比对新的调度身份和 state 里记的那个：

- 不一致 → 清掉陈旧的 `nextRunAtMs`，重新排期
- 一致（纯格式化、只改了键顺序）→ 保留待运行槽位

归一化函数对字段做了大量兼容：`expr` 和 `cron` 两个键名都认，`at` 和 `atMs` 都认，kind 缺失时从其他字段反推。

**代价（文档明说）**：拆分之后，旧版本 OpenClaw 能读 `jobs.json`，但因为运行态字段搬走了，会把所有 job 当成全新的。

## 2.3 调度语义

**三种 kind**：`at`（一次性，ISO 时间戳或 `20m` 这类相对量）、`every`（固定间隔毫秒，可带锚点）、`cron`（5 段或 6 段表达式 + 可选 IANA 时区）。

**时区**。不带时区的时间戳按 UTC 处理；cron 表达式不带 `tz` 时按 **Gateway 宿主机本地时区**。工具描述里对这一点反复强调了三次，措辞是"用所选时区的本地墙上时间写表达式，**不要先把请求的本地时间转成 UTC**"，还给了例子："每天上海时间下午 6 点" → `0 18 * * *` + `tz: Asia/Shanghai`。

**日/周字段是 OR 逻辑**。文档专门开了一节讲这个坑：表达式交给 croner 解析，当日期字段和星期字段都不是通配符时，croner 匹配的是**任一满足**，这是标准 Vixie cron 行为。`0 9 15 * 1` 的意图是"每月 15 号且是周一的早上 9 点"，实际是"每月 15 号早上 9 点 **加上** 每个周一早上 9 点"，一个月触发 5-6 次而不是 0-1 次。OpenClaw 选择保留 croner 的默认 OR 行为，给出的绕法是用 croner 的 `+` 修饰符或者在 prompt/命令里自己加条件判断。

**抖动（stagger）**。识别"整点循环"表达式（5 段时首字段为 0 且小时段含 `*`；6 段时秒和分都是 0 且小时段含 `*`），自动加最多 5 分钟的抖动。抖动量不是随机的，而是**对 job id 做 SHA-256 取前 4 字节模抖动窗口**——同一个 job 每次算出的偏移都一样，重启后不会漂移。算法上还做了一件事：把调度游标往回退一个偏移量，这样如果当前窗口的抖动槽位还没过去，仍然能命中当前窗口而不是跳到下一个。`--exact` 等价于把抖动设成 0。

**croner 年份回退的绕法**。`computeNextRunAtMs` 里有一段专门的补丁：某些时区/日期组合（注释点名 `Asia/Shanghai`）会让 croner 返回一个**过去年份**的时间戳。处理方式是三级重试——先从"下一秒"重算，再从"明天 UTC 零点"重算，都不行才返回 undefined。

**`every` 的计算**是纯算术：从锚点起算已过去多少个完整周期，向上取整加一步。这意味着长时间停机后重启，`every` 类型会直接跳到下一个未来槽位，不会补跑历史。

## 2.4 定时器主循环

**armTimer**。算出最近的唤醒时刻，转成延迟，然后做两次钳制：

- **下限**：延迟为 0 时强制一个最小间隔。注释里记了完整的事故链——某个 job 有卡住的 `runningAtMs` 标记加上已过期的 `nextRunAtMs` 时，找到期任务的函数会跳过它（被 running 标记挡住），而维护式重算又故意不推进已过期的时刻，于是 onTimer 的 finally 用 0 延迟重新武装，形成热循环，把事件循环打满并把日志写到大小上限
- **上限**：最多 60 秒。注释说明目的是避免调度漂移，并在进程被挂起或系统时钟跳变后快速恢复

还有一条分支：如果没有任何 job 带有效的下次运行时刻，但**存在启用的 job**，仍然武装一个 60 秒的"维护重查"定时器，而不是彻底停摆。

定时器回调**故意不写成 async**，注释说明是因为 Vitest 的假定时器会 await 异步回调，那会阻塞模拟长任务的测试。

**onTimer**。进来先看 `state.running`：

- 已经在跑 → 重新武装一个 60 秒重查定时器然后返回。注释记了这个补丁的事故：没有这一句的话，一个超过 60 秒的长任务会让定时器在 running 为 true 时触发，早返回之后**没有任何定时器留下**，调度器静默死掉直到 gateway 重启
- 没在跑 → 置 running，**同时武装一个看门狗定时器**（防止执行过程本身挂在 provider 调用里）

主体流程：

```
  locked(加锁) {
     强制重载 store
     collectRunnableJobs(now)
     若为空 -> recomputeNextRunsForMaintenance(允许重算过期) -> 持久化 -> 返回空
     否则 -> 给每个到期 job 打 runningAtMs 标记、清 lastError -> 持久化
  }
  |
  v
  并发执行（worker 池，并发度 = min(配置并发, 到期数)，游标分配）
  |    每个 job: 打活跃标记 -> 建后台任务记录 -> executeJobCoreWithTimeout
  v
  locked(加锁) {
     强制重载 store
     对每个结果 applyOutcomeToStoredJob
     recomputeNextRunsForMaintenance()   <- 只做维护式重算
     持久化
  }
  |
  finally: 会话回收器（自限流，每 5 分钟一次）
```

两处"维护式重算"都带注释解释为什么不用全量重算：全量重算会**在不执行的情况下推进已过期的 `nextRunAtMs`**，导致日级 cron 从跳 24 小时变成跳 48 小时。

会话回收器放在 `finally` 里，注释说明理由：如果一个长任务让 `running` 跨了多个定时器周期，onTimer 顶部的早返回会永久跳过回收器。

## 2.5 重启补跑

重启时的补跑（`runMissedJobs`）分三步：规划、执行、应用。

**规划阶段**的策略：

- 收集错过的任务，按下次运行时刻排序
- 可选地把 `agentTurn` 类型的任务**全部推迟**（延迟一个可配的时长）。文档解释了原因：过期的隔离 agent 任务如果立刻重放，会挤占 Discord/Telegram 的启动连接窗口和原生命令注册，导致重启后聊天平台长时间无响应
- 剩下的（非 agentTurn）取前 N 条立刻跑，**溢出的部分也推迟**

**执行阶段**是**严格串行**的（`for` 循环里逐个 await），与 onTimer 的并发执行形成对比。

## 2.6 执行路径 A：主会话任务

`sessionTarget: "main"` 的任务要求 payload 必须是 `systemEvent`。流程：

1. 取出文本，空的话直接记 `skipped`（错误信息区分"要求非空文本"和"要求 kind=systemEvent"两种）
2. 把文本作为系统事件入队，带上 `contextKey: cron:<jobId>`
3. 如果 `wakeMode` 是 `now`，立即跑一次心跳；否则等下一次自然心跳

`wake now` 的重试逻辑有三个分支：

- 心跳因为"cron 正在进行中"被跳过 → 不死等，改成**请求**一次心跳然后直接返回 ok
- 心跳因为其他可重试的忙碌原因被跳过 → 每 250 毫秒重试，最多等 2 分钟
- 超过最大等待 → 同样降级为"请求心跳"然后返回 ok

文档还补了一条语义：主会话任务入队的系统事件**不会延长目标会话的日更新/空闲重置的新鲜度**——也就是说 cron 唤醒不会阻止 `/new` 风格的会话滚动。

## 2.7 执行路径 B：隔离 agent 任务

这是 OpenClaw 代码量最大的部分（`src/cron/isolated-agent/` 一个目录 60+ 文件）。主流程是 `准备上下文 -> 执行 -> 收尾` 三段。

**会话身份**。隔离运行的会话键形如 `...:cron:<jobId>:run:<uuid>`，基础会话是 `...:cron:<jobId>`。解析时会做一次主会话别名的规范化（把 `agent:<id>:main` 转成配置里真正的 mainKey），注释记了不做这件事的后果：读路径用配置别名时，cron 会话会变成孤儿。

文档对"全新会话"给了精确定义：每次运行新的 transcript 和会话 id；**可以**继承的是安全偏好（thinking/fast/verbose 设置、标签、用户显式选择的模型与认证覆盖）；**不继承**的是频道/群组路由、发送或排队策略、提权、来源、ACP 运行时绑定。

**skill 快照**。每次运行解析一次工作区 skill 快照，带版本号和过滤器比对——版本没变且过滤器匹配就复用现有快照，否则重建。

**模型选择**的优先级链（文档明列四级）：

1. Gmail hook 的模型覆盖（当运行来自 Gmail 且该覆盖被允许）
2. 每 job 的 payload 模型
3. 用户存下的 cron 会话模型覆盖
4. agent/默认模型选择

关键语义：cron 的 `--model` 是**任务主模型**，不是聊天会话的 `/model` 覆盖——配置的回退链仍然生效。想要严格只试一个模型，要在 payload 里显式给 `fallbacks: []`。如果给了 `--model` 但既没有 payload 回退也没有配置回退，系统会传一个显式的空回退覆盖，防止 agent 的主模型被当成隐藏的额外重试目标。

Fast 模式跟随解析出来的实时选择；如果运行中发生实时模型切换握手，cron 会用切换后的 provider/模型重试并**持久化这次实时选择**（带认证配置的话一并持久化），重试上限是初始尝试 + 2 次。

**本地 provider 预检**。进入 agent 运行前，对配置为 `ollama` 或 `openai-completions` 且 baseUrl 是回环地址、私有网段或 `.local` 的 provider 做可达性探测。探测失败的运行记为 `skipped` 并带明确的 provider/模型错误，**不启动模型调用**。探测结果缓存 5 分钟，这样多个用同一个死掉的本地服务的到期任务共享一次探测而不是形成请求风暴。跳过的运行**不计入执行错误退避**，除非显式开启 `failureAlert.includeSkipped`。

**工具策略由投递模式推导**：

```
  deliveryMode = webhook  -> 关掉 message 工具
  deliveryMode = announce -> 强制开 message 工具
  deliveryMode = none     -> 强制开 message 工具（但若无显式目标则视为不请求投递）
```

**prompt 追加**。根据 message 工具是否可用，在任务正文后面追加不同的指令：

- 可用：「需要直接通知用户时使用 message 工具（面向当前聊天／需带显式目标）。如果你不直接发送，你的最终纯文本回复会被自动投递。」
- 不可用：「以纯文本返回你的回复，它会被自动投递。如果任务明确要求给某个外部收件人发消息，请写明该发给谁/发到哪，而不要自己发送。」

**收尾**（`finalizeCronRun`）做的事：

- 把系统提示词报告、模型/provider、上下文窗口大小写回会话条目
- 计算并**快照**用量与成本。注释记了一个事故：成本原本是每次持久化时累加的，导致数值被放大 1 到 72 倍；改成直接赋值（因为传入的用量本身就是累计值）
- 解析产出结果：区分摘要、输出文本、合成文本、投递负载、是否有致命错误负载、内嵌运行错误
- 频道输出策略：某些频道偏好"最终助手可见文本"而不是流式片段

**几条在文档里单独列出的收尾行为**：

- **中间态回复的再提问**：如果第一次结果只是一句中间状态更新（"on it"、"pulling everything together" 这类），且没有后代 subagent 还在负责最终答案，OpenClaw 会**重新提问一次**要真正的结果再投递
- **执行拒绝的识别**：优先用嵌入运行给出的结构化拒绝元数据，其次退回到已知的终态标记（`SYSTEM_RUN_DENIED`、`INVALID_REQUEST`），确保被拦截的命令不被报成绿色运行
- **运行级 agent 失败**即使没有产生回复负载也算 job 错误，这样模型/provider 故障会累加错误计数并触发失败通知，而不是被当成成功清账
- **浏览器与 MCP 清理**：隔离运行结束时尽力关闭该 cron 会话跟踪的浏览器标签/进程，并通过共享的运行时清理路径释放为该任务创建的 MCP 实例（否则隔离任务会跨运行泄漏 stdio 子进程和长连接）

**超时**。安全上限分两档：普通任务 10 分钟，agentTurn 60 分钟；job 上的 `timeoutSeconds` 覆盖之，设成 0 表示不限。超时后 cron 中止底层 agent 运行并给一个短清理窗口；如果运行没有排空，**Gateway 侧的清理会强制清除该运行的会话所有权**，这样排队的聊天工作不会卡在一个僵死的处理中会话后面。

## 2.8 投递

三种模式：`announce`（agent 没自己发的话，把最终文本兜底投递给目标）、`webhook`（把完成事件 POST 到 URL）、`none`（运行器不做兜底投递）。

**目标解析的层次**：

- 显式 `channel` + `to`
- `channel: "last"` 或省略 channel 时，带 provider 前缀的目标（如 `telegram:123`）可以选定频道，然后才轮到会话历史或唯一已配置频道
- 只有插件声明过的前缀才算 provider 选择器；`channel:<id>`、`user:<id>`、`imessage:<handle>`、`sms:<number>` 这些是频道自有的目标语法，不是 provider 选择器
- 如果 `delivery.channel` 是显式的，目标前缀必须指向同一个 provider——`channel: whatsapp` 配 `to: telegram:123` 会被拒绝，而不是让 WhatsApp 把 Telegram id 当电话号码解释

**从会话键反推目标**。当 agent 在聊天中创建一个隔离任务而没指定投递目标时，工具层会从当前会话键反解出 channel/peer/thread。会话键的编码形态有五种（`direct:<peer>`、`<channel>:direct:<peer>`、`<channel>:<account>:direct:<peer>`、`<channel>:group:<peer>`、`<channel>:channel:<peer>`），历史键还可能用 `dm` 代替 `direct`；带 `:thread:<id>` 后缀的会被剥掉以便投递给父级会话，但 **Telegram 论坛话题编码成 `<chatId>:topic:<topicId>`，这个要保留**。

**隔离任务的聊天投递是共享的**：只要有可用的聊天路由，agent 就可以用 message 工具，即便任务设了不投递。如果 agent 发到了配置/当前目标，兜底 announce 就跳过；否则三种模式只控制运行器拿最终回复做什么。

**静默**：如果隔离运行只返回静默令牌（`NO_REPLY` / `no_reply`），直接投递被抑制，**兜底的排队摘要路径也一并抑制**，什么都不发回聊天。

**subagent 与 Discord 的特例**：隔离运行编排 subagent 时，投递优先取最终后代的输出而不是陈旧的父级中间文本；后代还在跑就抑制那次部分更新。对纯文本 Discord 播报目标，只发一次规范的最终助手文本，而不是把流式/中间文本和最终答案都重放一遍；媒体和结构化 Discord 负载仍然作为独立负载投递。

**失败通知走独立路径**：全局 `cron.failureDestination` → job 级 `delivery.failureDestination` 覆盖 → 都没有且任务本身用 announce 投递时，回退到那个主投递目标。`failureDestination` 只在 `sessionTarget=isolated` 的任务上支持，除非主投递模式是 webhook。

## 2.9 重试、退避与失败告警

**错误退避表**（循环任务）：30 秒 → 60 秒 → 5 分钟 → 15 分钟 → 60 分钟，按连续错误数取，到顶后保持 60 分钟。下次运行时刻取"自然的下次运行"和"退避时刻"里**较晚的那个**。成功一次后连续错误计数清零。

**一次性任务的重试**（区别于循环任务）：区分瞬时错误和永久错误。瞬时错误类别可配（默认 `rate_limit`、`overloaded`、`network`、`server_error`），瞬时且未超过最大尝试次数（默认 3）则按退避表排重试；否则**禁用**任务。注释特意说明：`deleteAfterRun: true` 只在成功时触发，所以重试耗尽的任务是被禁用而非删除，**故意保留在存储里以便查看错误状态**。

**跳过（skipped）单独计数**。`consecutiveSkipped` 和 `consecutiveErrors` 是两个计数器，跳过不影响执行错误退避。只有开了 `failureAlert.includeSkipped` 才会对连续跳过告警。

**调度计算异常**有专门处理：如果表达式或时区把 croner 打炸了，记录调度错误（反复失败后自动禁用）并退化到"只用退避"的排期，保证状态更新不丢。

## 2.10 权限收窄：cron 自限权

OpenClaw 的做法是给隔离运行的 cron 工具实例**降级**。触发条件很具体：运行触发源是 cron、有 jobId、且 owner-only 工具白名单里包含 cron。满足时，工具实例被绑上"只能删这一个 job"的作用域。

降级后的行为：

| action | 行为 |
|---|---|
| `status` | 只返回一个字段：调度器启没启用 |
| `list` | 结果被过滤成只剩自己那一条；为了找到自己，会按 200 一页翻页直到命中或翻完 |
| `remove` | 只有 id 等于自己的 job 才放行 |
| 其他所有 action | 直接抛错 |

文档对这个设计的表述是：受限的隔离运行仍然可以读调度器状态和自过滤的自身任务列表，这样状态/心跳检查能查看自己的排期，而不获得更广的 cron 变更权限。

## 2.11 运行日志、任务账本与会话回收

**运行日志**：每个 job 一份，可分页读取，默认上限 2 MB / 2000 行，超出自动裁剪。

**任务账本**：所有 cron 执行都创建后台任务记录，出现在 `openclaw tasks` 里。对账规则文档写得很细：**运行时所有权优先，持久化历史其次**——只要 cron 运行时还把这个 job 记作运行中，活跃任务就保持存活，即使存在旧的子会话行。运行时不再拥有该任务且 5 分钟宽限期过后，维护流程去查持久化的运行日志和任务状态里对应 `cron:<jobId>:<startedAt>` 的那条记录：有终态就据此结账，否则 Gateway 侧维护可以把任务标记为 `lost`。离线 CLI 审计可以从持久化历史恢复，但**不会**把自己进程内空的活跃任务集合当作"Gateway 侧的 cron 运行已经消失"的证据。

**会话回收**：清理形如 `...:cron:<jobId>:run:<uuid>` 的临时运行会话，基础会话保留。默认保留 24 小时，可设为 false 关闭。回收自限流，最少 5 分钟一次，挂在定时器周期上。

## 2.12 agent 可见的工具面与 RPC

**工具**：单个 `cron` 工具，八个 action（status / list / add / update / remove / run / runs / wake）。

Schema 的设计原则写在文件顶部的注释里：**把 job/patch 的属性一条条摊开写，好让 LLM 知道该发什么字段；避免嵌套 union；运行时校验放在归一化函数里**。

几处针对模型行为的具体补偿：

- **扁平参数恢复**：非前沿模型（注释点名 Grok）有时会把 job 的属性平铺到顶层而不是嵌进 `job` 对象。当 `job` 缺失或为空对象时，从顶层已知字段重建一个合成对象；只有当至少出现一个"意图创建"的信号（schedule / payload / message / text 之一）时才采用。同一套逻辑也用在 patch 上，且带一条额外保护：从扁平参数恢复出来的 patch 如果是空的，报错而不是发一个空补丁
- **`failureAlert` 的类型妥协**：这个字段既接受对象也接受布尔 `false`。为了兼容只支持 OpenAPI 3.0 子集的 provider（注释点名经 GitHub Copilot 的 Gemini），schema 声明成 `type: "object"`，然后**在描述里告诉模型 `false` 也是可以的**
- **`jobId` 与 `id` 双认**：以 `jobId` 为正式标识，`id` 为兼容保留
- **`agentId` 自动填充**：list 时从会话解析出 agentId 自动过滤；add 时若 job 没带 agentId，从会话补上

**工具描述**（约 150 行）里的行为指令：

- 「用这个来处理提醒、"稍后回来看"的请求、延后跟进和循环任务。**不要用 exec sleep 或进程轮询来模拟调度**」
- 时区那三条（前面已引）
- 约束矩阵：`sessionTarget=main` **要求** `payload.kind=systemEvent`；`isolated`/`current`/`session:xxx` **要求** `agentTurn`
- 「如果任务需要发给特定的聊天/收件人，设置 announce 的 channel/to；**不要在运行内部调用消息工具**」
- 「默认优先用隔离的 agentTurn 任务，除非用户明确要求绑定当前会话」
- 受限运行的说明也写进了描述，让模型知道自己可能处在自限权模式

**上下文搬运**：`contextMessages`（0-10）会去拉当前会话的最近几条消息，格式化成 `- User: ...` / `- Assistant: ...` 追加到系统事件文本后面，每条截断 220 字符、总量上限 700 字符。重复创建时会先剥掉已有的上下文段落再重新追加。

**RPC 面**：Gateway 暴露 `cron.status` / `cron.list` / `cron.add` / `cron.update` / `cron.remove` / `cron.run` / `cron.runs` / `wake`，每个都有独立的参数校验器。工具层实际上是 RPC 的客户端——它不直接操作存储，全部经由 `callGatewayTool` 转发。

**Webhook 与 Gmail 触发**（同一子系统的外部入口）：`POST /hooks/wake` 给主会话入队系统事件；`POST /hooks/agent` 跑一次隔离 agent 回合；自定义 hook 名经配置映射解析，可以用模板或代码转换把任意负载转成 wake/agent 动作。认证只接受请求头（`Authorization: Bearer` 或专用头），**查询串里的 token 被拒绝**。文档的安全清单要求：用专用 hook token、不要复用 gateway 认证 token、hooks 路径不能是 `/`、用 `allowedAgentIds` 限制显式 agent 路由、默认不允许调用方指定会话键。

## 2.13 OpenClaw 失败态汇总

| 触发 | 结果状态 | 备注 |
|---|---|---|
| 主会话任务文本为空 | skipped | 错误信息区分两种成因 |
| 本地 provider 端点不可达 | skipped | 不计入错误退避；探测结果缓存 5 分钟 |
| 一次性任务瞬时错误、未超上限 | error + 排重试 | 按退避表 |
| 一次性任务永久错误或重试耗尽 | error + 禁用 | 故意保留在存储里 |
| 一次性任务成功且 deleteAfterRun | 删除 | 默认行为 |
| 一次性任务成功但不删 | 禁用 + 清空下次运行 | 防止紧循环 |
| 循环任务错误 | error + 退避 | 下次 = max(自然下次, 退避时刻) |
| 调度表达式抛异常 | 记调度错误 | 反复失败后自动禁用，退化为只用退避 |
| 任务超时 | error | 中止 agent，强制清会话所有权 |
| 运行级 agent 失败但无回复负载 | error | 明确不算成功 |
| 结果只是中间态确认 | 重新提问一次 | 无后代 subagent 在跑时 |
| 结果是 `NO_REPLY` | ok | 直接投递与兜底摘要都抑制 |
| 运行时不再拥有 + 5 分钟宽限 + 历史无终态 | 任务标 lost | 只有 Gateway 侧维护能标 |

## 2.14 OpenClaw 的代价

| 决策 | 代价 |
|---|---|
| 定义/运行态拆两文件 | 定义可入 git、可手改，代价是要维护"调度身份"这套比对逻辑，且旧版本读新文件会把 job 当全新的 |
| 自重新武装定时器（非固定 tick） | 精度高、空闲时零开销，代价是状态机复杂——报告里出现的热循环、静默死亡、48 小时跳跃三个真实事故都出在这块 |
| 60 秒延迟上限 | 抗时钟跳变和进程挂起，代价是即便下次运行在 6 小时后也每分钟醒一次 |
| 抖动用 job id 哈希而非随机 | 重启后偏移稳定，代价是同一个 job 永远落在同一个偏移量上——如果那个点正好和别的负载撞车，它每次都撞 |
| 保留 croner 的 OR 语义 | 与标准 cron 行为一致，代价是最直觉的写法会多触发 5-6 倍，只能靠文档提醒 |
| 模型选择四级优先级 + 实时切换重试 | 覆盖面全，代价是用户无法预测某次运行到底用了哪个模型，只能查运行日志 |
| 工具描述当行为规范 | 改行为不改代码，代价是每次调用付这段描述的 token，且约束是软的 |
| 为弱模型做扁平参数恢复 | 兼容性好，代价是 schema 不再是唯一契约，运行时多一层猜测逻辑 |
| 隔离运行的 cron 工具降级而非关闭 | 允许自我清理和自查排期，代价是 list 为了找到自己可能翻很多页 |
| 重启补跑推迟 agentTurn 任务 | 保住聊天平台启动窗口，代价是重启后隔离任务的实际执行时间不可预测 |
| 任务账本"运行时优先、历史其次" | 长任务不会被误判为丢失，代价是对账逻辑复杂到需要一整段文档解释，且离线 CLI 的判断能力被刻意削弱 |

---

# 第三部分：事实对照

只列可以直接从代码读出来的差异，不做优劣判断。

| 维度 | Hermes Agent | OpenClaw |
|---|---|---|
| 驱动方式 | gateway 后台线程，固定 60 秒 tick | Gateway 进程内自重新武装定时器，延迟钳在下限与 60 秒之间 |
| 互斥 | 文件锁，拿不到直接放弃 | 进程内 `running` 标志 + 加锁段 |
| 存储 | 单文件（定义+运行态） | 双文件（定义 / 运行态），带调度身份比对 |
| 调度类型 | once / interval / cron | at / every / cron |
| 时区 | 解析时转本地时区存下来；cron 跟随进程时区 | 时间戳无时区按 UTC；cron 无 tz 按宿主机本地时区 |
| 抖动 | 无 | 整点循环自动抖动至多 5 分钟，偏移量 = job id 哈希 |
| 至多一次 | 执行前统一推进 `next_run_at` | 执行前打 `runningAtMs` 标记，结果回写时算下次 |
| 错过处理 | 宽限期 = 周期一半（钳 120s–2h），超出则快进跳过 | 重启补跑，取前 N 条串行执行，agentTurn 类型整体推迟 |
| 并发 | 无 workdir 的并行（默认无上限），有 workdir 的串行 | worker 池，并发度可配，隔离 agent 走专用执行通道 |
| 执行形态 | 纯脚本模式 / LLM 模式（同进程线程） | 主会话（系统事件 + 心跳）/ 隔离 agent 回合 |
| 会话绑定 | 只有隔离（每次新会话 id） | main / isolated / current / session:\<id\> 四种 |
| 上下文搬运 | `context_from` 引用上游 job 产出（截断 8000 字符） | `contextMessages` 拉最近 0–10 条消息（每条 220 字符，总 700 字符） |
| 预处理脚本 | 有（唤醒门 + 数据采集，限定目录，按扩展名选解释器） | 无（外部触发走 webhook / Gmail PubSub） |
| 工具收窄 | `enabled_toolsets` 白名单 + 硬关 cronjob/messaging/clarify | payload 的 `toolsAllow` + 由投递模式推导的 message 工具策略 |
| 自排期防护 | 直接关掉 cronjob 工具 | 工具实例降级为"只能查/删自己" |
| 注入防护 | 创建时扫用户 prompt + 执行前扫组装结果（10 条正则 + 不可见字符） | 无对应机制（依赖工具策略与 owner-only 白名单） |
| 危险操作 | `approvals.cron_mode`，默认 deny | 依赖既有审批体系与 owner-only 工具白名单 |
| 静默令牌 | `[SILENT]`（禁止半沉默） | `NO_REPLY` / `no_reply`（同时抑制兜底摘要） |
| 超时 | 不活动超时，默认 600 秒 | 墙钟超时，普通 10 分钟 / agentTurn 60 分钟，job 可覆盖 |
| 重试 | 无自动重试 | 一次性任务分瞬时/永久，瞬时按表重试；循环任务错误退避 30s→60m |
| 失败告警 | 失败即投递错误消息 | 连续 N 次触发告警，独立目的地，带冷却，跳过单独计数 |
| 运行历史 | 每次运行一份 markdown 落盘 | 每 job 一份可分页运行日志 + 全局后台任务账本 |
| 产出留存 | `output/<job_id>/<时间戳>.md` 永久保留 | 运行日志按字节/行数裁剪；隔离运行会话默认留 24 小时 |
| 模型覆盖 | job 级 model/provider/base_url，认证失败走 fallback 列表 | job 级 model + fallbacks，四级优先级，实时切换重试上限 2 次 |
| 外部触发 | 无（只有内部调度） | webhook 端点 + Gmail PubSub + 自定义 hook 映射 |
| agent 工具面 | 单工具 `cronjob`，7 个 action | 单工具 `cron`，8 个 action，经 Gateway RPC 转发 |

---

# 第四部分：判断

## 技术判断

**1. 两家在同一个问题上给出了相反的答案：cron 跑起来之后还能不能碰 cron。** Hermes 直接把工具从注册表里摘掉（`disabled_toolsets`），OpenClaw 保留工具但降级成只能查/删自己。差异的代价方向不同：Hermes 的做法让任务无法自我清理（一次性提醒跑完只能靠 `repeat` 计数或外部删除），OpenClaw 的做法保留了自清理能力但引入了一条需要翻页的读路径和一套额外的作用域校验。这不是谁对谁错，是"任务能否自治"这个产品问题的两个答案。

**2. 调度器的复杂度和事故数量成正比，而事故几乎全在时间推进上。** 报告里能追溯到具体 issue 编号的补丁，OpenClaw 一侧集中在：定时器热循环、running 状态下静默死亡、维护式重算导致的 48 小时跳跃、croner 年份回退、抖动窗口错过当前槽位；Hermes 一侧集中在：循环任务算不出下次运行被误判为完成、手改文件后 `next_run_at` 丢失、成功但空回复被记成 ok。**没有一条事故出在"prompt 写得不好"上。** 这说明调度语义看着简单但状态机很脏，是真正吃工程时间的地方。

**3. 两家对"无人在场"的补偿手段完全不同，且各自只做了一半。** Hermes 做了注入扫描和默认拒绝，但没有重试、没有失败告警的独立目的地、没有运行日志裁剪。OpenClaw 做了完整的重试/退避/告警/账本/回收，但**没有任何 prompt 注入防护**——它的 cron 路径依赖既有的 owner-only 工具白名单和审批体系。如果把两家的能力做并集，才是一个完整的无人值守执行环境；单独任何一家都有明显缺口。

**4. 工具描述的体量说明了一件事：这类系统的行为约束主要不在代码里。** OpenClaw 的 cron 工具描述约 150 行，Hermes 的 `no_agent` 一个参数的描述就有 20 行。这些文字每次调用都要付 token，且约束是软的（模型可以不听）。两家都在描述里写了"不要用 sleep 模拟定时"、"不要自己投递"这类指令，同时又在代码里做了硬拦截——**说明它们都不信任描述本身**。描述的真实作用是降低模型犯错的概率，不是保证。

## 产品判断

*依据只到代码和文档，未考虑定价、用户分层、竞品。*

**1. 两家产品形态的分岔点，是"定时任务的结果给谁看"。** Hermes 的默认投递目标是"创建这个任务时你在的那个聊天"，产出同时永久落盘成 markdown；它的 `no_agent` 模式、唤醒门、`context_from` 链接，全都是在服务"运维式的持续监控"。OpenClaw 的投递体系（多频道前缀、线程/话题、失败目的地、announce 兜底、subagent 输出优先）明显更重，服务的是"多人多频道的团队通知"。这不是功能多寡的差别，是场景差别。

**2. `no_agent` 是 Hermes 里最被低估的一个决策。** 它承认了一件事：**很多"定时任务"根本不需要 LLM**。内存看门狗、阈值告警、CI 通知这些，脚本自己就能产出确切的消息文本，过一遍模型只是增加成本和不确定性。工具描述里那段"什么时候用 True / 什么时候用 False"的对照，实际上是在教用户识别自己的需求要不要推理。OpenClaw 没有对应的东西——它的每一个 `agentTurn` 任务都要过模型。

**3. 静默协议是这类产品的存亡开关，两家都做了，但只有 Hermes 把它写成了硬约束。** Hermes 的执行须知里明确禁止"半沉默"（标记后面不许跟内容），说明模型确实会输出"[SILENT] 另外我还发现……"。一个每小时运行的任务如果每次都说话，用户三天内就会关掉它。这条约束的产品价值远超它的实现成本。

**4. 从产品交付的角度看，OpenClaw 的复杂度已经外溢到用户侧了。** 它的文档里需要专门解释"为什么 `cron --model` 不等于会话的 `/model`"、"为什么日/周字段是 OR"、"为什么改了 jobs.json 排期会重置"。这些都是实现细节被迫暴露成用户必须理解的概念。Hermes 的对应位置要简单得多，代价是能力上限低（没有重试、没有多会话模式、没有外部触发）。

---

# 第五部分：未确认项汇总

行文中已就地标注的推测，在此汇总。以下均为**没有实际验证**的部分：

1. **代码量的比例估算**（主线里的"不到六分之一"）是我按文件和函数粗略归类的结果，没有做精确的行数统计。结论方向可靠，具体比例不可引用。
2. **Hermes 的 `_deliver_result` 内部实现**只读了目标解析和媒体路由的入口，没有通读各平台适配器的发送路径。所以"投递失败如何分类"这一层我只知道它被记进 `last_delivery_error`，不知道错误粒度。
3. **OpenClaw 的 `executeCronRun` 运行时**（`run-executor.runtime.ts` 等 `.runtime.ts` 文件）没有读。所以"隔离 agent 回合内部到底怎么调 agent runner"这一层是空白，报告里关于该部分的描述全部来自调用点的参数和官方文档。
4. **OpenClaw 的 `collectRunnableJobs`** 具体的到期判定条件（尤其 `allowCronMissedRunByLastRun` 这个开关的语义）我只从调用点推断，没有读实现。
5. **两家的测试覆盖**没有评估。OpenClaw 的 `src/cron/` 下有大量以 issue 编号命名的回归测试文件，我把这当作"每个线上事故都固化成回归测试"的证据，但**没有逐个打开确认**它们是否真的对应线上事故。
6. **Hermes 的 gateway 侧 cron 线程**只看了启动位置和 60 秒间隔，没有读它的异常处理和退出路径。
7. **性能数据**两家都没有。报告里所有关于开销的描述都是结构性推断，不是实测。

---

# 第六部分：源码锚点索引

## Hermes Agent

| 主题 | 位置 |
|---|---|
| 模块定位与部署说明 | `cron/__init__.py:1` |
| 调度字符串解析 | `cron/jobs.py:124` (`parse_schedule`)、`:103` (`parse_duration`) |
| 一次性任务宽限恢复 | `cron/jobs.py:232` |
| 自适应宽限期 | `cron/jobs.py:259` |
| 下次运行计算 | `cron/jobs.py:291` |
| 运行结果落库 | `cron/jobs.py:703` (`mark_job_run`) |
| 至多一次的推进 | `cron/jobs.py:776` (`advance_next_run`) |
| 到期判定与快进 | `cron/jobs.py:805`、`:817` |
| 产出落盘 | `cron/jobs.py:907` |
| 注入拦截异常 | `cron/scheduler.py:44` |
| 工具集三级优先级 | `cron/scheduler.py:57` |
| 已知投递平台白名单 | `cron/scheduler.py:~168` |
| 投递目标解析 | `cron/scheduler.py:257`、`:343`、`:363` |
| 脚本执行与路径校验 | `cron/scheduler.py:655` |
| 唤醒门解析 | `cron/scheduler.py:756` |
| prompt 组装 | `cron/scheduler.py:782` |
| 组装后注入扫描 | `cron/scheduler.py:930` |
| 单任务执行 | `cron/scheduler.py:955` (`run_job`)，纯脚本短路在 `:983` 起 |
| agent 构造参数 | `cron/scheduler.py:~1345` |
| 不活动超时 | `cron/scheduler.py:~1380`–`1465` |
| 结果判定三道关 | `cron/scheduler.py:~1467`–`1490` |
| 资源清理 | `cron/scheduler.py:~1535`–`1576` |
| tick 主循环 | `cron/scheduler.py:1578` |
| 威胁模式表 | `tools/cronjob_tools.py:40` |
| prompt 扫描 | `tools/cronjob_tools.py:60` |
| 来源捕获 | `tools/cronjob_tools.py:71` |
| 工具主体 | `tools/cronjob_tools.py:257` |
| 工具 schema 与描述 | `tools/cronjob_tools.py:496` |
| cron 审批模式 | `tools/approval.py:735`、`:835`、`:955` |
| 默认值 deny | `hermes_cli/config.py:1192` |
| gateway 定时线程 | `gateway/run.py:15059`、`:15449` |

## OpenClaw

| 主题 | 位置 |
|---|---|
| 用户文档 | `docs/automation/cron-jobs.md` |
| 下次运行计算（含 croner 绕法） | `src/cron/schedule.ts:68` |
| 抖动识别与解析 | `src/cron/stagger.ts` |
| 稳定抖动偏移（job id 哈希） | `src/cron/service/jobs.ts:65`、`:86` |
| 错误退避表 | `src/cron/service/jobs.ts:41`、`:57` |
| 调度身份归一化 | `src/cron/schedule-identity.ts` |
| 存储与状态 sidecar 路径 | `src/cron/store.ts:36` |
| 超时策略 | `src/cron/service/timeout-policy.ts` |
| 结果落库与重试判定 | `src/cron/service/timer.ts:520` (`applyJobResult`) |
| 定时器武装（含热循环下限） | `src/cron/service/timer.ts:781` |
| 主循环 | `src/cron/service/timer.ts:850` (`onTimer`) |
| 重启补跑规划 | `src/cron/service/timer.ts:1130` |
| 执行分派（主会话 / 隔离） | `src/cron/service/timer.ts:1333` |
| 主会话执行与心跳重试 | `src/cron/service/timer.ts:1383` |
| 心跳投递抑制策略 | `src/cron/heartbeat-policy.ts` |
| 会话回收 | `src/cron/session-reaper.ts` |
| 运行日志与裁剪 | `src/cron/run-log.ts:82`、`:100` |
| 隔离运行会话键 | `src/cron/isolated-agent/session-key.ts` |
| skill 快照 | `src/cron/isolated-agent/skills-snapshot.ts` |
| 工具策略由投递模式推导 | `src/cron/isolated-agent/run.ts:305` |
| 投递上下文解析 | `src/cron/isolated-agent/run.ts:330` |
| prompt 追加投递指令 | `src/cron/isolated-agent/run.ts:391` |
| 收尾与用量快照 | `src/cron/isolated-agent/run.ts:796` |
| 隔离回合入口 | `src/cron/isolated-agent/run.ts:1055` |
| 工具 schema 设计注释 | `src/agents/tools/cron-tool.ts:29` |
| 扁平参数恢复 | `src/agents/tools/cron-tool.ts:90`、`:117` |
| failureAlert 类型妥协 | `src/agents/tools/cron-tool.ts:~224` |
| 自限权作用域校验 | `src/agents/tools/cron-tool.ts:352`–`382` |
| 上下文消息搬运 | `src/agents/tools/cron-tool.ts:439` |
| 从会话键反推投递目标 | `src/agents/tools/cron-tool.ts:~524` |
| 工具描述（行为规范） | `src/agents/tools/cron-tool.ts:~552`–`702` |
| 工具执行分派 | `src/agents/tools/cron-tool.ts:703` |
| 自限权授予条件 | `src/agents/pi-tools.ts:379` |
| 工具注册与投递上下文注入 | `src/agents/openclaw-tools.ts:340` |
| Gateway RPC 方法 | `src/gateway/server-methods/cron.ts` |

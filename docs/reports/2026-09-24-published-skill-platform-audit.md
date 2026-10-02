# 已发布 Skill 平台适配评估（第二轮）

评估基线：本地 `staging` 的 `6812670b12f3f262799119d1fbc2c66d6dae14df`；发布日期清单取自 `skills-index.json` 的 52 个 `skills[].path`。判据见 [Skill 平台适配标准](../reference/skill-platform-adaptation.md)。本次为源文件静态审查，未在七个 hskill target 上逐一执行，不把“可安装”当成“已运行通过”。

## 结论与处理顺序

发现 13 个需要处理或验证的发布条目，其中 6 个在特定宿主或安装条件下缺少核心流程的可执行路径，7 个主要是共享入口、引用文件与适配证据问题。其余 39 个属于本轮静态通过、有意限定范围，或已有回退但仍需实测；“通过静态审查”不代表端到端实测。

| 批次 | 条目 | 建议及验证 |
|---|---|---|
| A：先修执行断点 | `research/learn-video`、`research/extract-vision`、`design/scout-brand`、`mint/scout-philosophy`、`meta/sync-hotfix`、`agent-canvas/close-node` | 保留任务语义，解除专有工具/固定目录的必经条件；分别做受限宿主或隔离路径实测 |
| B：修共享表述和引用 | 三个 `feed/sync-*`、`coding/question-me`、`coding/rephrase`、`coding/init-project`、`mint/runby-opencode` | 把宿主命令移至明确适配点，校准引用文件；用静态检查及定向流程验证 |
| C：按使用频率补证据 | `research/clip-url`、`coding/init-goal`、三个 `feed/sync-*` 的非 Claude 适配器，以及使用 `SKILL_DIR` 字面量示例的 skill | 建立目标宿主实测矩阵，记录未验证、通过或失败，不预设全部兼容 |

### A 批次证据

| Skill | 证据与影响 | 处理建议 |
|---|---|---|
| [learn-video](../../skills/research/learn-video/SKILL.md#L60) | 模式选择强制 `AskUserQuestion`；[31](../../skills/research/learn-video/SKILL.md#L31) 和 [256](../../skills/research/learn-video/SKILL.md#L256) 将当前 skill 目录指向个人仓库；vdl 命令多处假设 `$HOME/Projects/Video-Learner`。Claude `Monitor` 在 [123](../../skills/research/learn-video/SKILL.md#L123) 有其他平台的泛化说法，属于示例而非单独断点。 | 提问用宿主能力或对话；skill 资产从实际目录定位；vdl 根目录由 CLI/配置查找并在缺失时报错。保留用户对下游配置漂移的决定权。 |
| [extract-vision](../../skills/research/extract-vision/SKILL.md#L44) | OCR 后强制子智能体过滤；OCR 为空、图片模糊时还要求“视觉子智能体”。没有委派或视觉子智能体的会话缺回退。 | 文本过滤允许当前 agent 顺序完成；原图需视觉能力时先检测，缺失则停下说明。OCR 识别脚本可独立实测。 |
| [scout-brand](../../skills/design/scout-brand/SKILL.md#L23) | `/browse` 初始化和 `$B` 浏览器 CLI 是核心前提，但 `browse` 不在发布清单内；[截图读取](../../skills/design/scout-brand/SKILL.md#L41) 又指定 `Read` 工具。宿主是否提供等价浏览能力没有声明。 | 明确浏览能力契约与可用入口；无法获取 DOM/截图时停止，不能捏造数据。实测至少一个非 Claude 浏览入口。 |
| [scout-philosophy](../../skills/mint/scout-philosophy/SKILL.md#L60) | 三个外部研究对象以 `~/.claude/skills`、Claude 插件缓存和 `~/Repositories` 固定路径定位；在其他装机方式下无法选对象。 | 每个生态先发现已安装路径或接受用户显式路径；缺失时报告覆盖范围，不虚构样本。 |
| [sync-hotfix](../../skills/meta/sync-hotfix/SKILL.md#L20) | 声称按当前平台自动推断安装目录，但只列 Claude、Codex、Hermes；hskill 实际支持七个 target 和项目级安装。对 Cursor、OpenCode、Pi、OpenClaw及自定义目录无法可靠定位。 | 显式安装目录优先，默认目录从 hskill target 解析；确认目录和 `SKILL.md` 后再扫描。保持源/装机方向和用户确认门禁。 |
| [close-node](../../skills/agent-canvas/close-node/SKILL.md#L58) | 接手方“离开”直接要求 `ExitWorktree(action: "keep")`。在 Codex 或没有该工具的 Agent Canvas 节点会卡住；该命令不是生命周期语义本身。 | 按宿主选择离开/解除绑定方式；没有该能力时保留 worktree、停止在安全位置并报告。不要扩大为自动清理。 |

### B 批次证据

| Skill | 证据与影响 | 处理建议 |
|---|---|---|
| [sync-xtimeline](../../skills/feed/sync-xtimeline/SKILL.md#L4) | 描述和 [run 标题](../../skills/feed/sync-xtimeline/SKILL.md#L48) 直接写 `/loop`；一次性运行步骤本身可执行，Codex 适配器标“未实测”。 | 共享入口改为“手动运行或经当前宿主调度”；平台命令置于适配说明；对调度与单次运行分别验证。 |
| [sync-ytchannel](../../skills/feed/sync-ytchannel/SKILL.md#L4) | 与上一项相同，[run 标题](../../skills/feed/sync-ytchannel/SKILL.md#L48) 含 `/loop`。 | 同上。 |
| [sync-website](../../skills/feed/sync-website/SKILL.md#L4) | 与上一项相同，[run 标题](../../skills/feed/sync-website/SKILL.md#L112) 含 `/loop`。 | 同上；同时保留标定失败不落盘的边界。 |
| [question-me](../../skills/coding/question-me/SKILL.md#L3) | description 把主动触发写成“Claude auto-triggers”；[30](../../skills/coding/question-me/SKILL.md#L30)、[115](../../skills/coding/question-me/SKILL.md#L115) 和 [186](../../skills/coding/question-me/SKILL.md#L186) 用 Claude 指代执行 agent。问答流程本身不依赖 Claude API。 | 用“当前宿主/当前 agent”描述手动触发与建议触发，避免承诺任何宿主一定自动调用。 |
| [rephrase](../../skills/coding/rephrase/SKILL.md#L3) | description 和 [正文](../../skills/coding/rephrase/SKILL.md#L10) 把可靠性判断归给 Claude，实际是当前执行 agent 的判断。 | 改主体表述；保留“仅手动调用”的边界。 |
| [init-project](../../skills/coding/init-project/references/template-schema.md#L4) | 主入口已使用当前 target 和 `SKILL_DIR`，但模板 schema 仍称安装路径固定为 `~/.claude/skills/...`；同文件的骨架示例仍称 `CLAUDE.md`。 | 校准引用文件与已发布的 `AGENTS.md`、目标安装目录；运行模板路径静态检查。 |
| [runby-opencode](../../skills/mint/runby-opencode/SKILL.md#L29) | `verify` 已允许用户提供路径或用仓库源，但默认候选仍偏向 Claude 安装目录；[35–50](../../skills/mint/runby-opencode/SKILL.md#L35) 用挂载 Claude 目录的配置示例。`compare` [81–98](../../skills/mint/runby-opencode/SKILL.md#L81) 本来就是 Claude 与 opencode 对比，不应算通用宿主缺陷。 | `verify` 以显式源目录与目标安装结果为先；`compare` 明确前置条件及缺一端时的结果。不得静默改用户 opencode 配置。 |

## 52 项逐条结果

标签：`A`＝A 批次；`B`＝B 批次；`静态通过`＝本轮未见宿主专有必经条件；`有意限定`＝特定平台/产品就是任务对象；`需实测`＝适配文字或抽象路径存在，运行能力尚未得到本轮验证。每行的“静态通过”仅限本轮对宿主机制的审查。

| 发布条目 | 结论 | 依据摘要 |
|---|---|---|
| [mint/learn-skill](../../skills/mint/learn-skill/SKILL.md) | 静态通过 | 共享配置路径，未见宿主专有入口。 |
| [research/extract-vision](../../skills/research/extract-vision/SKILL.md#L44) | A | 强制委派和视觉子智能体，缺能力回退。 |
| [research/learn-video](../../skills/research/learn-video/SKILL.md#L60) | A | 强制 Claude 提问工具及固定仓库路径。 |
| [research/survey-skillrepo](../../skills/research/survey-skillrepo/SKILL.md#L144) | 有意限定 | `WebSearch` 等出现在被调查 skill 的工具矩阵，不是执行调用。 |
| [research/learn-paper](../../skills/research/learn-paper/SKILL.md) | 静态通过 | Bash 是文本写入示例；未见 Claude 专属命令成为必要条件。 |
| [research/fetch-paper](../../skills/research/fetch-paper/SKILL.md) | 静态通过 | 已用搜索、请求、下载能力表述及 shell 回退。 |
| [research/extract-cognition](../../skills/research/extract-cognition/SKILL.md) | 静态通过 | shell/文件流程，无宿主专有调用。 |
| [research/probe-session](../../skills/research/probe-session/SKILL.md#L19) | 需实测 | 使用抽象 `SKILL_DIR`；示例执行前需绑定真实路径。 |
| [research/pdf-math-translate](../../skills/research/pdf-math-translate/SKILL.md) | 静态通过 | Hermes 作者元数据不限制其他宿主。 |
| [research/clip-url](../../skills/research/clip-url/SKILL.md#L16) | 需实测 | 明确适配与顺序回退；非 Claude 宿主未做本轮端到端测试。 |
| [feed/sync-xtimeline](../../skills/feed/sync-xtimeline/SKILL.md#L48) | B | 共享入口含 `/loop`，非 Claude 补丁仍标未实测。 |
| [feed/sync-ytchannel](../../skills/feed/sync-ytchannel/SKILL.md#L48) | B | 同上。 |
| [feed/sync-website](../../skills/feed/sync-website/SKILL.md#L112) | B | 同上。 |
| [creative/capture-todo](../../skills/creative/capture-todo/SKILL.md#L35) | 静态通过 | `Read` 可换成宿主的文件读取能力；未要求 Claude 特有 API。 |
| [creative/capture-insight](../../skills/creative/capture-insight/SKILL.md) | 静态通过 | 流程使用 Git 与文本处理，无宿主专有必经条件。 |
| [coding/init-workflow](../../skills/coding/init-workflow/SKILL.md#L33) | 有意限定 | `.claude/workflow-config.yml` 明确用于旧配置兼容；同时支持中性配置。 |
| [coding/setup-debug](../../skills/coding/setup-debug/SKILL.md) | 静态通过 | 多进程日志方案未绑定 agent 宿主。 |
| [coding/init-goal](../../skills/coding/init-goal/SKILL.md#L147) | 需实测 | `/loop` 已放入 Claude 适配器；共享正文有顺序回退。 |
| [coding/question-me](../../skills/coding/question-me/SKILL.md#L3) | B | 自动触发与执行主体仍写为 Claude。 |
| [coding/capture-vocab](../../skills/coding/capture-vocab/SKILL.md#L12) | 需实测 | 共享路径已抽象为 `SKILL_DIR`；示例执行前需绑定真实路径。 |
| [coding/rephrase](../../skills/coding/rephrase/SKILL.md#L3) | B | 当前 agent 的判断被写成 Claude 判断。 |
| [coding/explain-pm](../../skills/coding/explain-pm/SKILL.md) | 静态通过 | 无宿主特有调用。 |
| [coding/init-project](../../skills/coding/init-project/references/template-schema.md#L4) | B | 主入口已中性；schema 引用文件仍指固定 Claude 安装目录。 |
| [writing/forge-doc](../../skills/writing/forge-doc/SKILL.md#L8) | 需实测 | 路径已抽象；`SKILL_DIR` 示例执行前需绑定真实路径。 |
| [writing/draw-diagram](../../skills/writing/draw-diagram/SKILL.md) | 静态通过 | 图表生成语义与宿主无关。 |
| [writing/manage-dir](../../skills/writing/manage-dir/SKILL.md) | 静态通过 | 文件整理流程未绑定宿主工具名。 |
| [writing/migrate-spec](../../skills/writing/migrate-spec/SKILL.md) | 静态通过 | 规格迁移流程未绑定宿主工具名。 |
| [design/scout-brand](../../skills/design/scout-brand/SKILL.md#L23) | A | 必经 `/browse` 与 `$B`，发布包未提供该依赖。 |
| [design/build-style](../../skills/design/build-style/SKILL.md#L52) | 静态通过 | `Read` 是文件读取能力；另有独立的过期路径问题，见下文。 |
| [design/sync-design](../../skills/design/sync-design/SKILL.md) | 静态通过 | 文件与 HTML 预览操作未见宿主专有必经机制。 |
| [mint/init-skill](../../skills/mint/init-skill/SKILL.md#L56) | 静态通过 | `Read` 是文件读取能力；Claude 用语仅为示例主体。 |
| [mint/publish-skill](../../skills/mint/publish-skill/SKILL.md#L291) | 静态通过 | `Read`/`Edit` 可以由宿主文件能力实现；发布规则不依赖该工具品牌。 |
| [mint/archive-skill](../../skills/mint/archive-skill/SKILL.md) | 静态通过 | 归档流程无宿主特有必经调用。 |
| [mint/dedup-skill](../../skills/mint/dedup-skill/SKILL.md) | 静态通过 | 去重流程无宿主特有必经调用。 |
| [mint/contribute-skill](../../skills/mint/contribute-skill/SKILL.md#L20) | 静态通过 | 源目录已明确验证，不以 Claude 装机目录为默认真相。 |
| [mint/fix-skill](../../skills/mint/fix-skill/SKILL.md#L19) | 静态通过 | `claude` 是平台字段示例值。 |
| [mint/runby-opencode](../../skills/mint/runby-opencode/SKILL.md#L29) | B | 比较目标有意限定；验证入口的默认候选路径偏向 Claude，但已有显式路径/仓库源替代。 |
| [mint/scout-philosophy](../../skills/mint/scout-philosophy/SKILL.md#L60) | A | 研究对象固定在 Claude/本机路径。 |
| [meta/clean-git](../../skills/meta/clean-git/SKILL.md) | 静态通过 | Git 清理流程未见 agent 宿主调用。 |
| [meta/release-project](../../skills/meta/release-project/SKILL.md#L39) | 有意限定 | `CLAUDE.md` 是被扫描的项目配置候选之一。 |
| [meta/sync-hotfix](../../skills/meta/sync-hotfix/SKILL.md#L20) | A | 安装目录推断仅覆盖三宿主和用户级路径。 |
| [meta/sync-agent](../../skills/meta/sync-agent/SKILL.md) | 静态通过 | Syncthing CLI/API 为外部工具依赖，不是 agent 宿主接口。 |
| [coding/handoff](../../skills/coding/handoff/SKILL.md#L255) | 需实测 | 共享语义保留，文末明列 Claude/Codex 的进出方式。 |
| [feed/manage-creators](../../skills/feed/manage-creators/SKILL.md) | 静态通过 | roster 操作未见宿主专有调用。 |
| [feed/capture-opinion](../../skills/feed/capture-opinion/SKILL.md) | 静态通过 | 名册数据写入流程未见宿主专有调用。 |
| [agent-canvas/agent-canvas-control](../../skills/agent-canvas/agent-canvas-control/SKILL.md#L43) | 有意限定 | `claude-code` 等是 Canvas `node-type` 参数值。 |
| [agent-canvas/describe-node](../../skills/agent-canvas/describe-node/SKILL.md#L34) | 有意限定 | Claude 是 Canvas 默认节点标题的例子。 |
| [agent-canvas/relate-node](../../skills/agent-canvas/relate-node/SKILL.md) | 静态通过 | Canvas CLI 统一处理节点关系。 |
| [agent-canvas/capture-requirement](../../skills/agent-canvas/capture-requirement/SKILL.md) | 静态通过 | Canvas CLI 统一处理需求登记。 |
| [agent-canvas/relation-review](../../skills/agent-canvas/relation-review/SKILL.md) | 静态通过 | 本来仅限 Global Pilot；没有 Claude 专用调用。 |
| [agent-canvas/close-node](../../skills/agent-canvas/close-node/SKILL.md#L58) | A | 接手方分支直接调用 `ExitWorktree`。 |
| [coding/analyze-claudemd](../../skills/coding/analyze-claudemd/SKILL.md#L3) | 有意限定 | 审查对象就是 `CLAUDE.md`；源文件优先，装机副本仅最后兜底。 |

另见两个与平台适配相邻、但需要单独立项的源路径问题：[build-style](../../skills/design/build-style/SKILL.md#L52) 将自己的引用文件写成 `skills/writing/build-style/...`，而实际位于 `skills/design/build-style/...`；[scout-brand](../../skills/design/scout-brand/SKILL.md#L17) 的模板路径同样写成 `skills/writing/scout-brand/...`，实际位于 `skills/design/scout-brand/...`。本轮只记录，不改源文件。

## 方法与限制

审查了全部 52 个已索引 `SKILL.md`；对命中的适配文件、引用文档和执行示例追查到具体行。`rg` 命中只是候选，结论按是否进入核心执行路径判断。未运行真实 Claude、Codex、Hermes、Pi、OpenCode、Cursor、OpenClaw 会话；未安装或改写用户宿主配置；未启动浏览器、视频任务和 Canvas 节点。后续 A/B 批次应各自建立独立修复分支、同步版本/索引元数据，再做与主张匹配的验证。

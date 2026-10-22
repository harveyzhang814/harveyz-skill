# research bundle 精简扫描（simplify-skill「拟定建议」阶段）

扫描日期：2026-10-22 ｜ 基线：`staging` @ 9af95ab ｜ 标准：`.claude/skills/simplify-skill/SKILL.md` v0.1.2「拟定建议」7 条
范围：`skills-index.json` 中 `bundle: research` 的 10 个 skill，读了每个的 `SKILL.md`、`references/`、`platforms/`，以及与 SKILL.md 文本有约束关系的测试（`tests/skill-portability.test.mjs`、`extract-cognition/evals/evals.json`）。未读脚本实现，只核对了 SKILL.md 引用到的输出字符串和路径。

**主线：** 这个 bundle 可减的量集中在三处：extract-cognition 的同一规则在 3–4 处重复出现，以及只有模式 B 才用到却默认加载的归因层；learn-video / clip-url / fetch-paper 里写给维护者的背景说明；pdf-math-translate 抄进来的整张 CLI 参数表。其余 skill 已经接近下限。

**把握度标记：** [读到] = 直接出自文件原文；[推出] = 由多处原文推断；[未查] = 没有核实，需要去查。

**全局约束（所有建议都受它约束）：**
- `tests/skill-portability.test.mjs` 对 3 个 skill 的 SKILL.md 做文本断言（fetch-paper、learn-video、extract-vision），另对 `clip-url/platforms/SKILL.codex.md` 做断言。改写时这些字符串必须原样留在原文件里，而且正则要求同一行的，不能拆行。各节分别列出。[读到]
- 改动后 `skills-index.json` 的 `contentHash` / `contentVersion` 要跟着变，frontmatter `version` 也要 bump；frontmatter 的 `name` 必须等于目录名（`tests/skills.bats:185`）。[读到]
- 每个 skill 的 description 都是触发条件，本报告不建议改 description，只在发现它和正文对不上时标出来。

---

## 1. bundle 总览

规模 = SKILL.md + references/ + platforms/（agent 运行时会读的文本）；scripts、tests、evals、CHANGELOG 不计。

| skill | 当前规模（行） | 优化潜力 | 预估可减比例 | 主要问题（一句话） |
|---|---|---|---|---|
| extract-cognition | 1270（SKILL 541 + ref 729） | 高 | SKILL.md 约 30%；把模式 B 的内容移出去后，默认加载再少约 20% | 同一规则（F6/F7、置信度、模式判定、产物映射）写了 3–4 遍，runbook 又把全流程复述一遍；只有模式 B 才用到的归因层常驻 SKILL.md；参考文件是 729 行的通用教程，却被整份读入 |
| learn-video | 285 | 中 | 约 25%；失败处理移到 references 后默认加载再少约 25% | 维护者背景说明（`work/` 布局来历、索引凭据、配置为何会漂移）混在指令里；"必须后台启动"讲了 4 次；rerun、改模式、换 focus 这些只在失败或追问时才用的段落常驻 |
| clip-url | 610（SKILL 192 + ref 318 + platforms 100） | 中 | 约 15–20% | 初始化 ② 与步骤 2.5 做的是同一项检查；占位符替换规则在 SKILL.md 和 reference 头部各写一遍；4 个平台补丁里 ② 节是同一段文字，而且与 SKILL.md 对固定词表路径的说法不一致 |
| pdf-math-translate | 209 | 中 | 约 30% | 25 行的完整参数表和 24 个服务的列表就是 `pdf2zh --help` 的内容；Init 的 6 个探测步骤各占一个标题加一个代码块；「语言对说明」和示例命令对不上 |
| fetch-paper | 245 | 中 | 约 20% | 平台中立的措辞（"宿主的 X 能力""若使用 shell，这是一种示例写法"）逐句重复；PMC 和出版商两条渠道各是一大段实测记录；渠道顺序有两套说法 |
| survey-skillrepo | 364（SKILL 200 + ref 164） | 中 | 约 20–25% | 版本号头和尾都是旧的，正文示例还在用旧命令名 `/analyze-skill`；`prohibitions.md` 8 条有 6 条和必检清单重复；输出模板里"幽灵文件"出现两次 |
| learn-paper | 310 | 中 | 约 15% | 5C 维度、批判任务、诚实性标注各在"分析任务"和"产出模板"里写两遍；读结论页的 3 次 Read 被逐条写出；标题写的是 `read-paper`，与 name 不一致 |
| probe-session | 93 | 低 | 约 15% | 两段 Python `subprocess` 样板代码其实就是一条命令 |
| extract-vision | 71 | 低 | 约 5–10% | "常见问题"后两条重复了上面的分支规则 |
| explain-design | 190（SKILL 138 + ref 52） | 无 | <3% | 已经按条件和动作写好；只有第 12 行一句空泛要求可以删 |

---

## 2. 高 / 中潜力 skill 详述

### 2.1 extract-cognition（高）

**问题，按 7 条标准归类：**

- **②/⑤ 重复**
  - F6 鸡汤锁、F7 不可迁移锁的定义出现在 3 处：`SKILL.md:271-272`（阶段 5 标准）、`SKILL.md:419-421`（§5 失败模式）、`SKILL.md:385-386`（§8 自审）。[读到]
  - 置信度规则写了两遍：描述层门槛在 `SKILL.md:246`，在 `SKILL.md:371` 又重复一次；归因层规则在 `SKILL.md:372-376`。[读到]
  - 模式判定写了 3 遍：`SKILL.md:102-110`、`SKILL.md:463`、`SKILL.md:520`。[读到]
  - §9 runbook（`SKILL.md:517-541`，25 行）把 §4 的阶段 0–8 整体复述了一遍。[读到]
  - 管线 mermaid 图（`SKILL.md:116-141`）与「产出文件映射」表（`SKILL.md:171-178`）、`--pass` 表（`SKILL.md:70-76`）讲的是同一件事：阶段对应哪个文件、谁依赖谁。[读到]
  - 阶段 7 的闸门 mermaid 图（`SKILL.md:320-338`）与紧随其后的文字（`SKILL.md:340-364`）逐闸门重复。[读到]
- **⑥ 解释混在指令里**
  - `SKILL.md:10` 后半句"所有'判断'都被替换为可勾选的标准"是在说框架本身，不是在下指令。[读到]
  - `SKILL.md:207` 那段"读全文是对的……"引用框，讲的是阶段 5 为什么要隔离。[读到]
  - `SKILL.md:353` 与 `SKILL.md:358` 两段"为何要独立上下文 / 为什么必须用子任务"，各自 2–3 句，压成一句理由就够。[读到]
  - `SKILL.md:299` 的"为什么先学它"一句属于产出模板的内容，是要写进产物的，**保留**。[读到]
- **④ 渐进式披露**
  - 阶段 7（`SKILL.md:314-378`）、§6 签名卡模板中的归因层字段（`SKILL.md:439-448`）、归因层上限声明（`SKILL.md:453-454`）、§8 示例的阶段 7 部分（`SKILL.md:507-513`），合计约 100 行，只在模式 B 或 `--pass 4` 时才用到。可以移到 `references/attribution-gate.md`，在 SKILL.md 里只留"模式 B 时读该文件"和那条红线"无基线不出 4-attribution"。[推出]
  - `references/article-analysis-methods.md` 共 729 行，大部分是 19 种方法的通用教程，例如金字塔原理、Toulmin 的出处和定义。阶段 2 实际只需要它的第三部分：四问决策树和对照总表（`references/article-analysis-methods.md:669-729`）。建议把 `SKILL.md:215` 的读取指令改为"先读第三部分；选定方法后只读第一部分中那一节"。文件本身不删。[推出]
- **⑦ 对照原文发现的不一致**
  - runbook 写"交付前自审12项"（`SKILL.md:538`），而清单实际有 13 项（`SKILL.md:385-399`）。[读到]
  - 元信息块写"**模式**: A 仅描述 / B 描述+归因"（`SKILL.md:184`），与模式表"模式 A:学习层（evidence → signature → playbook）"（`SKILL.md:106`）对不上。现在的模式 A 也产出手册，不再是"仅描述"。[读到]
  - Step 0 询问文案写"认知签名分析保存到哪个目录"（`SKILL.md:32`），说的是 v0.1 的产物名。这是用户能看到的提问，改不改由用户决定。[读到]

**代表性修改：**

1. `SKILL.md:405-421`（§5 失败模式 F1–F7）
   - 修改前：7 条，每条都是"触发信号 / 为何危险 / 纠正"三段。其中 F6、F7 与阶段 5 的标准逐字重复；F2、F3、F4 的"纠正"分别是"走对抗 pass""过 Agenticity 门""套置信度公式"，也就是阶段 7 的步骤本身。
   - 修改后：只留 F1（清单扫描）和 F5（残余过读），这两条在阶段里没有对应的标准。F6、F7 在 §5 中各改成一行"见阶段 5 标准"；F2、F3、F4 随归因层一起移进 `references/attribution-gate.md`。
   - 理由：标准 ②⑤。F6、F7 同时还被 `evals.json` 用作断言名，所以编号和名称必须保留，只去掉重复的定义。
2. `SKILL.md:517-541`（§9 runbook）
   - 修改前：25 行，把阶段 0–8 全部复述，夹着"--pass N 终点"标注和一条红线。
   - 修改后：删掉整节。阶段与 `--pass` 终点的对应已经在 `SKILL.md:70-76` 的表里；"红线：无基线不出4-attribution，动作卡无锚不出，不可迁移则改写"这一行并到 `SKILL.md:12-15` 的操作信条里。
   - 理由：标准 ②。顺带消除了"12项 / 13项"的矛盾。
3. `SKILL.md:184`
   - 修改前：`**模式**: A 仅描述 / B 描述+归因`
   - 修改后：`**模式**: A 学习层 / B 学习层+归因层`
   - 理由：标准 ⑦，与 `SKILL.md:106-108` 对齐。这一行是写进 4 个产物文件头的字段值，属于输出契约的一部分，改之前需要用户确认。

**必须保留、不能动：**
- 配置路径 `~/.hskill/extract-cognition/config.json` 与字段名 `output_dir`。[读到]
- 产物文件名 `1-evidence.md` / `2-signature.md` / `3-playbook.md` / `4-attribution.md`，`--pass 1..4` 参数及其依赖关系。[读到]
- `evals/evals.json` 断言里用到的结构与名称，例如 `3-playbook.md` 的"一、这套思维的发生器"节标题、动作卡 7 栏的栏名（"回指证据""从哪条根性长出""迁移练习""怎么自己跑"）、"别处也这么使"、F6/F7 的编号、"归因层不得出现「高置信」"、片段拒绝（约 300 字）且零产物。[读到]
- 两段上限声明（`SKILL.md:453-457`），它们是产物里的固定措辞。[读到]
- 根性 ≤2 条、描述层 ≥1 实例 / 高置信 ≥3、Patternicity ≥2、留出约 20–30%、"无子任务环境"的降级标注文案。[读到]
- §8 最小示例中阶段 1–6 的部分：它用来锚定动作卡的写法，不建议删，只把阶段 7 部分随归因层一起移走。[推出]

**未确认：**
- 未确认：硬停机检查（`SKILL.md:97-100`）排在 Step 1 的 `mkdir -p`（`SKILL.md:65`）之后，所以片段输入会留下一个空目录。eval `no_files_produced` 只检查文件，目前能过；要不要把停机检查提到 mkdir 之前，属于行为改动，不在本次精简范围内。[推出]
- 未确认：把归因层移进 references 以后，eval 1（模式 B）的通过率是否不变，需要用户按这份 eval 重跑一次。[未查]

---

### 2.2 learn-video（中）

**问题，按 7 条标准归类：**

- **② 重复**
  - "必须后台启动 / 禁止前台阻塞"在 `SKILL.md:96`、`SKILL.md:160`、`SKILL.md:191`、`SKILL.md:197` 出现了 4 次。[读到]
  - 产物路径先在 `SKILL.md:134` 写一次（从终态 JSON 取路径），又在 `SKILL.md:221` 写一次（"首次运行成功时……不需要再跑"）。[读到]
- **⑥ 解释混在指令里**
  - `SKILL.md:42`（"这几个值分居不同文件……"）、`SKILL.md:245`（`work/` 这一层来自 vdl 的 `core/paths.js`）、`SKILL.md:265`（`meta.json` 是唯一凭据、`creators.json` 不含 registry），都是给维护者看的背景，不影响 agent 的下一步动作。[读到]
  - `SKILL.md:259` 的"顺手……（零额外成本——流程本来就在跑脚本）"是一句修饰。[读到]
  - `SKILL.md:96` 第二句讲为什么前台调用会超时，留半句理由就够。[推出]
- **④ 渐进式披露**
  - 「步骤名对照表」「处理步骤失败」「更改任务模式」「重新生成摘要」（`SKILL.md:139-215`，约 77 行）只在失败或用户追问时才用到，可以移到 `references/rerun.md`。**但**测试正则 `/package\.json.*npm run agent:serve.*存在/` 匹配的正是 `SKILL.md:180` 这一行，所以要么把这一行留在 SKILL.md，要么同步改测试。后者超出精简范围，需要用户决定。[读到]
- **⑤ 含糊的表述**
  - `SKILL.md:122` 中"定期查看"的周期没有写；不过 `SKILL.md:124-126` 已经把轮询节奏明确交给宿主机制，所以不算含糊，不改。[读到]

**代表性修改：**

1. `SKILL.md:96`
   - 修改前："**必须后台启动，禁止前台阻塞调用。** 视频处理可能长达数小时（见「超长视频检测」），前台 Bash 调用会被运行环境的超时机制打断——任务本身在后端仍会继续跑，但 agent 拿到的是超时错误而不是真实结果，也就无法感知进度或在完成后向用户报告。"
   - 修改后："**本文所有 `vdl` 主命令与 `vdl rerun` 一律后台启动**（前台调用会被宿主超时打断，拿不到终态）。"后文 `SKILL.md:160`、`SKILL.md:191` 中的"同样必须后台启动"删掉。
   - 理由：标准 ②⑤。一条规则写一次，覆盖范围说清楚。
2. `SKILL.md:245` 与 `SKILL.md:265`
   - 修改前：两段维护者背景说明，合计 2 段长句。
   - 修改后：删掉 `SKILL.md:245`；`SKILL.md:265` 删掉。
   - 理由：标准 ⑥。`archive.py` 报错时 `SKILL.md:257` 已经给出了动作，这两段不改变判断。
3. `SKILL.md:42`
   - 修改前："这几个值分居不同文件，没有任何机制保证自动同步；漂了的话归档步骤会当场报错，不会静默写出孤儿 `meta.json`。"
   - 修改后：删掉。
   - 理由：标准 ⑥。`SKILL.md:40` 已经规定了 `DRIFT:` 时的动作。

**必须保留、不能动：**
- 测试断言（`tests/skill-portability.test.mjs:32-41`）要求 SKILL.md 中存在：`当前宿主可用的提问方式`、`$SKILL_DIR/scripts/store_config.py`、`$SKILL_DIR/scripts/archive.py`、`$SKILL_DIR/scripts/build_creator_index.py`；同一行内依次出现"不能可靠启动并追踪长期任务…启动前…停止"（当前在 `SKILL.md:98`）、同一行内"package.json…npm run agent:serve…存在"（当前在 `SKILL.md:180`）；不得出现 `$HOME/Projects/harveyz-skill` 或 `$HOME/Projects/Video-Learner`。[读到]
- 跨 skill 共享契约：`~/.hskill/config.json` 的 `knowledgeRoot` 字段及"只增改、不覆盖其他字段"；`store_config.py check` / `check-downstream` 的输出前缀 `MISSING:` / `DRIFT:` / `SKIP:` / `fix:`；"不得擅自改 `knowledgeRoot` 或 vdl `WORK_ROOT`"。clip-url 与 3 个 feed skill 共用这套契约（`SKILL.md:283` 写"四个入范围 skill"）。[读到]
- 与 vdl 的接口：`Task: <task_id>` 首行、`[<step>] done/failed` 日志格式、终态 JSON 以 `{"task_id"` 开头、`Error: Step … failed`、`Done in <n>s`、显示名到 DAG 名的对照表、`BAD_ANCHOR_MODE`、`ECONNREFUSED 127.0.0.1:3000`、`/tmp/vl-agent-token` 与 `/api/tasks/<id>/steps/summary/run`。[读到]
- `archive.py` 的输出 `VIDEO_DIR:` / `META_PATH:`，以及必填字段 `source_url` / `title` / `fetched_at`。[读到]
- 默认值 `~/knowledge` 与"不选 Documents/Desktop/Downloads"的 TCC 理由：后者决定了默认值的取舍，保留一句。[推出]

**未确认：**
- 未确认：`SKILL.md:207-215` 的 HTTP API 换 focus 与 `SKILL.md:204` 的 `rerun summary` 是两步配合还是二选一，原文没有说清。精简时不动语义，但建议请用户澄清。[推出]

---

### 2.3 clip-url（中）

**问题，按 7 条标准归类：**

- **② 重复**
  - 初始化 ②（`SKILL.md:27-38`）已经在 `MISSING:` 时问用户并写入配置、创建空的 `fixed_tags.txt`；步骤 2.5（`SKILL.md:87-98`）又跑一次 `store_config.py check`，`MISSING:` 时让用户"回去做初始化 ②"，并检查 `fixed_tags.txt` 是否存在。初始化之后这两个分支只有在写入失败时才会命中。[推出]
  - 占位符替换规则写了两遍：SKILL.md 步骤 3、4.5、5（`SKILL.md:102`、`SKILL.md:114`、`SKILL.md:121`）各写一遍，三个 reference 的头部（`references/subagent1-fetch-prompt.md:3`、`references/subagent-self-optimize-prompt.md:3-8`、`references/subagent2-tag-translate-prompt.md:3`）又各写一遍。[读到]
  - 4 个平台补丁的「② 变量来源」前 4 行逐字相同（`platforms/SKILL.claude.md:19-22` 等），各文件之间只有 `SKILL_DIR` 一项不同。[读到]
  - 写入失败时禁止改 `knowledgeRoot` 的段落（`SKILL.md:42`）与 learn-video 那段逐字近似。这是跨 skill 的重复，每个 skill 都必须自包含，**不建议合并**。[读到]
- **⑥ 解释混在指令里**
  - `SKILL.md:36-38` 中关于 url-extract 的历史说明（"这份历史目录现在只承载……不再读取其中的 `VAULT_PATH` 字段"），`SKILL.md:172` 的边界段，以及 `SKILL.md:189-190` 两处"`mcp_` 前缀为历史遗留"。[读到]
  - 参考文件表（`SKILL.md:176-192`）共 16 行；其中 `browser_fetch_cli.py`、`vault_config.py`、`article_meta.py` 并不由主流程直接调用，属于维护信息。[推出]
- **⑤ 含糊的表述**
  - 步骤 4（`SKILL.md:109-110`）用两段长句表达一个由 3 个字段组合决定的判定，适合改成一张 3 行的表。[读到]
- **⑦ 不一致**
  - 4 个平台补丁写"固定词表仍从 `~/.hskill/url-extract/config.json` 读取"（`platforms/SKILL.claude.md:20`），SKILL.md 与 subagent2 都写的是 `~/.hskill/url-extract/fixed_tags.txt`（`SKILL.md:172`、`references/subagent2-tag-translate-prompt.md:39`）。[读到]

**代表性修改：**

1. `SKILL.md:87-98`（步骤 2.5）
   - 修改前：整节约 12 行，重新跑一次 `store_config.py check` 并检查 `fixed_tags.txt` 是否存在。
   - 修改后：删掉整节，流程概览中的 2.5 一并删除。把初始化 ② 的结尾改为"写入后再跑一次 `check`；仍为 `MISSING:` 则报告并终止"。
   - 理由：标准 ②⑤。终止条件仍然在，只是移到了初始化 ② 里。另外，`fixed_tags.txt` 不存在时的提示文案在初始化后不会被触发；精简时要不要保留这句提示，需要用户决定，见未确认项。
2. 4 个 `platforms/*.md` 的「② 变量来源」
   - 修改前：每个文件 4 行相同的说明，加各自的 `SKILL_DIR`。
   - 修改后：每个补丁的 ② 节只留 `SKILL_DIR` 一项；"文章路径由 `store_config.py` 计算、固定词表读 `~/.hskill/url-extract/fixed_tags.txt`、Chrome profile 由 browser-fetch 持久化，均不需 agent 传参"这句写一次，放在 SKILL.md 的初始化 ① 中。
   - 理由：标准 ②⑦。同时修正 `config.json` 与 `fixed_tags.txt` 的路径矛盾。
3. `SKILL.md:102`、`SKILL.md:114`、`SKILL.md:121`
   - 修改前：每步都完整写出占位符怎么替换，例如步骤 4.5 用一整段写了 7 个占位符在 OK 和 FAILED 下各取什么值。
   - 修改后：每步一句"读取 `references/<file>`，按其头部的占位符规则替换后，按**补丁①**派发"。替换规则只保留在 reference 头部。
   - 理由：标准 ②。保留 reference 头部这一份，是因为它和 prompt 正文在同一个文件里，主 session 替换时就在读这个文件。[推出]

**必须保留、不能动：**
- 测试断言：`platforms/SKILL.codex.md` 必须含"顺序执行"，且不得含"未验证""待补"（`tests/skill-portability.test.mjs:25-30`）。Hermes 补丁里的"未验证 / 待补"是给 agent 的停止信号，也要保留。[读到]
- 与 browser-fetch 的接口：`tools/browser-fetch/`、`hskill install --tool browser-fetch`、`browser_fetch_locate.py` 的 `FOUND:` / `NOT_FOUND:`、`chrome_profile_config.py` 的 `get` / `set` / `prompted` / `mark-prompted` 与 `CONFIGURED:` / `NOT_CONFIGURED` / `YES` / `NO`。[读到]
- 3 个 subagent 的报告字段，全部是主流程的解析依据：`RESULT: OK|FAILED|SKIPPED|SOLIDIFIED|GAVE_UP`、`ORIGIN_PATH` / `TITLE` / `SITE` / `BLOCK_COUNT` / `CHAR_COUNT` / `CODE_BLOCK_COUNT` / `IMAGE_COUNT` / `CONTENT_THIN` / `THIN_RETRY_USED` / `META_PATH` / `TRANSLATION_PATH` / `BRANCH` / `ATTEMPTS` / `DIAGNOSIS` / `ERROR`。[读到]
- Translation frontmatter 的字段与顺序（`references/subagent2-tag-translate-prompt.md:60-74`），双链格式 `[[{hash8}/Origin/{文件名}]]`，`Origin` / `Translation` 同名规则，`fetch_type` 默认 `manual`。[读到]
- 存储布局 `<knowledgeRoot>/articles/<hash8>/`；去重只看 `meta.json` 的 `source_url`；`scripts/migrate-store.sh --apply`（已确认存在）。[读到]
- 自优化 subagent 的 git 约束：`fix/<site-slug>-extraction`、不建 worktree、不 merge / 不 push、测试全绿才能提交；最多 5 次 `call_evaluate_js`；每个 URL 只自优化一次。[读到]
- 4 张卡片的格式与字段（`SKILL.md:129-166`），以及 SOLIDIFIED 之后的附加一行。[读到]

**未确认：**
- 未确认：`platforms/SKILL.claude.md:9-15` 的派发语法是 `sessions_spawn --runtime subagent`。仓库内只有已归档的 `extract-url`、`article-fetcher` 用过这个命令。Claude Code 里的派发应该是 Agent 工具，这一段可能是迁移时带过来的旧语法。这是行为问题，不在精简范围内，建议单独核实。[推出]
- 未确认：`SKILL.md:109` 中"`CONTENT_THIN: True` 且 `THIN_RETRY_USED: False` 不算需要自优化——没有更多现有手段可以尝试"，后半句的理由读起来和字段名的含义是反的：没用过 thin-retry，按字面应该是"还有手段没用"。规则本身不动，理由要请用户确认。[推出]
- 未确认：步骤 2.5 中"`fixed_tags.txt` 不存在时提示一句"的分支，在初始化 ② 之后是否还能被触发，取决于用户会不会手动删掉这个文件。[推出]

---

### 2.4 pdf-math-translate（中）

**问题，按 7 条标准归类：**

- **② 通用教程 / CLI 帮助**
  - 「完整参数表」（`SKILL.md:170-193`，21 个参数）和「支持的翻译服务」（`SKILL.md:195-197`）就是 `pdf2zh --help` 的内容。流程真正用到的只有 `-o`、`--lang-in` / `--lang-out`、`--service`、`--mode`、`--markdown`、`--word`、`--no-pdf`、`--pages`。[推出]
- **③ 压缩为术语**
  - Init 的步骤 1–6（`SKILL.md:33-80`）每步都有一个三级标题、一个代码块和判定说明，可以合并成一张"探测项 | 命令 | 判定 → 写入 config 的值"表。[读到]
- **⑤ 含糊的表述**
  - 「语言对说明」（`SKILL.md:199-202`）写的是 `ZH-EN` / `EN-ZH`，但示例命令用的是 `--lang-in en --lang-out ZH`（`SKILL.md:139`），没有说明这两种写法分别用在哪里。[读到]
- **⑦ 可疑内容**
  - `SKILL.md:206` 写"自动下载 ONNX 模型（约 300MB），缓存在 `~/.paddlex/`"，与 extract-vision 的 `SKILL.md:69` 措辞几乎一样（PaddleOCR 的缓存目录），有可能是从那里复制过来的。[推出]

**代表性修改：**

1. `SKILL.md:170-197`
   - 修改前：25 行参数表加服务列表。
   - 修改后："常用参数：`-o` 输出目录、`--lang-in/--lang-out`、`--service`（默认 `google`）、`--mode fast|precise`、`--pages`、`--markdown` 与 `--word` 互斥、`--no-pdf` 仅配合 `--word`。其他参数和服务列表以 `pdf2zh --help` 为准。"
   - 理由：标准 ②③。互斥关系和"`precise` 依赖 `pdf2zh_next`"是本 skill 的判断依据，必须保留；其余参数是通用的 CLI 信息。
2. `SKILL.md:33-80`（Init 步骤 1–6）
   - 修改前：6 个小节，每节一个代码块。
   - 修改后：一张 6 行的表：
     | 探测 | 命令 | 判定 |
     |---|---|---|
     | CLI 路径 | `which pdf2zh` | — |
     | 解释器 | `head -1 "$(which pdf2zh)"` 的 shebang | — |
     | 安装方式 | `$PY -c "import pdf2zh; print(pdf2zh.__file__)"` | 含 `site-packages` 为 regular，否则为 editable 并记录仓库根 |
     | 版本 | `pdf2zh --version` | — |
     | precise | `$PY -c "import pdf2zh_next"` | 无报错为可用；`ModuleNotFoundError` 为不可用 |
     | PYTHONPATH | `echo "$PYTHONPATH"` | 指向其他 Python 版本的环境时记为风险，规避方法是 `unset PYTHONPATH` |
   - 理由：标准 ③⑤。命令和判定一条不少。

**必须保留、不能动：**
- 配置路径 `~/.hskill/pdf-math-translate/config.md`，探测结果 `EXISTS` / `NOT_FOUND`，config.md 的模板字段（Execute 阶段按字段读取）。[读到]
- "重新初始化"的触发语，以及"该文件可随时手动编辑，是之后每次调用的唯一依据"。[读到]
- Execute 阶段的 5 条规则（`SKILL.md:129-133`）。[读到]
- 输出文件名约定 `*-mono.pdf` / `*-dual.pdf` / `document-mono.md`、`images/` 子目录、Obsidian wikilink 格式。[读到]
- frontmatter 中的 `metadata.hermes.related_skills: [ocr-and-documents, extract-vision]`（Hermes 平台用的跨 skill 声明）。[读到]

**未确认：**
- 未确认：`ZH-EN` / `EN-ZH` 是 `pdf2zh` 的哪个参数取值，或是否已经过时。[未查]
- 未确认：`~/.paddlex/` 是否真是 pdf2zh 的模型缓存目录。[未查]

---

### 2.5 fetch-paper（中）

**问题，按 7 条标准归类：**

- **② 重复措辞**
  - "宿主的 X 能力"出现 14 次；"若使用 shell，这是一种示例写法 / 例如"出现 6 次（`SKILL.md:37`、`45`、`51`、`153`、`161`、`167`）。可以在「路径变量」之后加一句总述（下文 shell 片段都是示例；文本读写用宿主的文件能力；PDF 是二进制，只能用复制写盘），逐句的套话就可以删掉。[读到]
- **⑥ 解释混在指令里**
  - PMC 渠道（`SKILL.md:135`，一整段）和出版商 OA 页渠道（`SKILL.md:136`，一整段）大部分是实测经过，例如 301 跳转、Proof-of-Work 中间页、ScienceDirect/MDPI 返回 403。影响决策的只有"直链必然失败，记入 B，不重试"和"遇到 403 或非 PDF 即判失败，记入 B，不重试同一出版商"。[读到]
- **⑤ 含糊的表述**
  - `SKILL.md:130` 规定"把 `auto: true` 的站点按 `success_count` 降序排序，依次尝试"，紧接着 `SKILL.md:132-137` 又用 1–6 的固定编号列出渠道，而且 5、6 两项并不在种子 `sources.json` 里（`SKILL.md:56-61`）。到底按哪套顺序执行，原文没有写清。[读到]

**代表性修改：**

1. `SKILL.md:135`（PMC）
   - 修改前：约 260 字的实测说明。
   - 修改后："**PMC**：仅限生物医学论文。用 `idconv` 接口换取 PMC ID（301 跳转后重请求一次，ID 在 `records[0].pmcid`）。PMC 的 PDF 直链需要浏览器完成 JS 挑战，普通请求必然失败：直接把落地页记入「B 手动候选」，不尝试下载。"
   - 理由：标准 ⑥。Unpaywall / Semantic Scholar 也会返回 PMC 落地页这一观察，可以作为一个从句附在后面，也可以删掉，需要用户定。
2. `SKILL.md:37`、`45`、`51`（以及 `153`、`161`、`167`、`191`）
   - 修改前："用户回复后，用宿主的文本写入能力创建配置（……）。若使用 shell，这是一种示例写法："
   - 修改后："用户回复后写入配置（路径用 `$HOME` 展开，不写字面量 `~`）："，前提是文首已有总述。
   - 理由：标准 ②。**`SKILL.md:140` 与 `SKILL.md:167` 中关于下载能力、临时文件、不得把二进制交给文本写入的约束保留原文**，它们是行为约束，也是测试断言的对象。

**必须保留、不能动：**
- 测试断言（`tests/skill-portability.test.mjs:13`）：SKILL.md 必须含"下载能力""临时文件"，不得含 `WebFetch`、`WebSearch`、`Read 工具`、`Write 工具`、`Bash 工具`。改写时不能顺手换成具体的工具名。[读到]
- 路径与字段：`~/.hskill/fetch-paper/config.json` 的 `download_dir`；`sources.json` 的 `name` / `type` / `auto` / `success_count`，以及"保留其余字段不变"。[读到]
- 4 种结果标签 A/B/C/D 及其分支条件（`SKILL.md:144-147`）；D 不创建目录、不写文件。[读到]
- `metadata.md` 的模板，以及 B、C 两种"获取渠道"行的写法。[读到]
- 各 API 端点与取值字段：`best_oa_location.url_for_pdf`、`openAccessPdf.url`、`records[0].pmcid`，以及 Unpaywall 的 `email=fetch-paper@localhost`。[读到]
- 「边界」5 条，其中"不自动调用 `learn-paper`"是跨 skill 边界。[读到]

**未确认：**
- 未确认：渠道顺序以 `success_count` 排序为准还是以 1–6 的编号为准；渠道 5、6 是否参与排序。[推出]
- 未确认：description 写"Maintains a growing list of free sources"，但正文只给已有站点的 `success_count` 加 1，没有任何一步会新增站点。description 不在本次修改范围内，只是指出它和正文对不上。[读到]

---

### 2.6 survey-skillrepo（中）

**问题，按 7 条标准归类：**

- **⑦ 过时内容**
  - 正文头 `> **版本：** v2.0.0`（`SKILL.md:10`）与文末 `*survey-skillrepo v2.0.0 | 2026-06-19*`（`SKILL.md:200`）都和 frontmatter 的 `2.0.2` 不一致。[读到]
  - `SKILL.md:44` 的示例写成"`/analyze-skill ~/path/to/skill-repo`"，`SKILL.md:152` 的依赖图示例写成"`analyze-skill` → `learn-skill`"，用的都是旧命令名。[读到]
- **② 重复**
  - 「触发条件」（`SKILL.md:16-22`）是在重复 description。[读到]
  - `references/prohibitions.md` 的 8 条里，第 1 与第 4 条重复，并且和 `SKILL.md:75-76`、`SKILL.md:125` 重复；第 2 条重复 `SKILL.md:71`；第 5 条重复 `SKILL.md:142`；第 8 条重复 Step 2。真正新增的只有第 3、6、7 三条。[读到]
  - `references/output-template.md` 的"幽灵文件检查"（`references/output-template.md:50-52`）与"附录 / 幽灵文件列表"（`references/output-template.md:137-141`）重复。[读到]
  - Step 4 的 frontmatter（`SKILL.md:181-188`）与模板的「元信息」（`references/output-template.md:11-18`）字段重叠。这是输出契约，要不要合并由用户决定。[读到]
- **④ 渐进式披露（方向反过来）**
  - prohibitions 是始终生效的约束，按标准 ④"保留共同规则与始终生效的约束"，应该并进 SKILL.md 的必检清单，再删掉"执行前必须读取 `references/prohibitions.md`"（`SKILL.md:78`）这一跳。[推出]
- **⑤ 含糊的表述**
  - Step 0 第 4 步（`SKILL.md:34`）写"将解析后的绝对路径写入 `$HOME/.hskill/config.json`（文件不存在则新建）"，没有说明文件已存在时只增改 `skillDir`。这个文件里还有 learn-video、clip-url 等 skill 共用的 `knowledgeRoot`，照字面执行可能把它覆盖掉。learn-video 的 `SKILL.md:32` 已经写了"只增改、不覆盖"。[推出]

**代表性修改：**

1. `SKILL.md:44`
   - 修改前："**带路径参数**（如 `/analyze-skill ~/path/to/skill-repo`）→ 直接使用该路径"
   - 修改后："**带路径参数**（如 `/survey-skillrepo ~/path/to/repo`）→ 直接使用该路径"
   - 理由：标准 ⑦，与 description 和 `SKILL.md:18` 对齐。
2. `SKILL.md:34`
   - 修改前："将解析后的绝对路径写入 `$HOME/.hskill/config.json`（文件不存在则新建）"
   - 修改后："写入 `$HOME/.hskill/config.json` 的 `skillDir` 字段（文件不存在则新建；已有其他字段时只增改 `skillDir`，不覆盖）"
   - 理由：标准 ⑤。这是把原文的含糊处写明确，没有新增行为；但它涉及共享配置，需要用户确认原意确实如此。
3. `SKILL.md:78` 加 `references/prohibitions.md`
   - 修改前：必检清单之后写"执行前必须读取 `references/prohibitions.md`"，那份文件共 8 条。
   - 修改后：在必检清单中补上 3 条：每个列出的文件都要验证存在；`allowed-tools` 必须从实际 SKILL.md 读取，不得取自 `.tmpl` 或记忆，且描述不得与表格矛盾；三种关系类型不得混淆。删掉第 78 行的读取指令和 `prohibitions.md` 文件。
   - 理由：标准 ②④。

**必须保留、不能动：**
- 与 learn-skill 的接口：共享配置键 `skillDir`；learn-skill 的产物路径 `{skillDir}/{repo-name}/{skill-name}.md`；Layer 3"对每个 skill 调用 `learn-skill`"。[读到]
- 输出路径 `{skillDir}/{repo-name}/analysis-{YYYY-MM-DD}.md`（同名覆盖），以及 `repo-name` 的取法。[读到]
- 报告 frontmatter 的字段 `repo` / `path` / `version` / `analyzed_at` / `skills_count`。[读到]
- 工具权限矩阵的列头，以及"三类交互关系"的名称（自动触发 / 建议序列 / 前置配置）。[读到]
- 结束时告知用户的 3 项内容。[读到]

**未确认：**
- 未确认：`output-template.md` 中的「构建流水线」「模版文件」两节，在 Layer 1–4 里都没有对应的指令，它们来自哪一版需求，以及要不要保留。[读到/未查来源]
- 未确认：`SKILL.md:142` 要求从 `allowed-tools` 字段读工具权限，而本仓库的 research skill 都没有 `allowed-tools` 字段，这张矩阵在大多数仓库里会是空的。这是方法设计问题，不在精简范围内。[推出]

---

### 2.7 learn-paper（中）

**问题，按 7 条标准归类：**

- **② 重复**
  - 5C 维度先在分析表（`SKILL.md:140-146`）里写一遍，又在产出模板（`SKILL.md:161-167`）里写一遍。[读到]
  - 第三遍的分析任务（`SKILL.md:257-263`）与模板各节（`SKILL.md:284-298`）一一对应。[读到]
  - 诚实性标注的三个标签先在 `SKILL.md:265-269` 定义，又在模板的 `SKILL.md:280`、`290`、`294`、`298` 重复列出。[读到]
  - `--pass` 表（`SKILL.md:90-95`）与依赖检查代码（`SKILL.md:99-105`）讲的是同一件事。[读到]
- **③ 压缩**
  - 读结论页的策略（`SKILL.md:119-134`）把 3 次 Read 调用分别写出来，一句"从末页起每次向前读 4 页，找到 Conclusion / 结论 / Discussion 即停，最多 3 次"就能表达。[读到]
- **⑥ 解释**
  - `SKILL.md:190` 的"（避免 context 溢出）"、`SKILL.md:192` 的"——References 之后已无需提取的正文内容"都是理由，可以删。[读到]
- **⑦ 不一致**
  - 正文标题是 `# read-paper`（`SKILL.md:8`），name 是 `learn-paper`。[读到]

**代表性修改：**

1. `SKILL.md:119-134`
   - 修改前：一句策略说明，加 3 段 Read 伪代码，再加一段关于 `<total>` 的说明。
   - 修改后："从末页起每次向前读 4 页（`pages="<total-3>-<total>"`，依次前移），见到 Conclusion / 结论 / Discussion 即停，最多 3 次；`<total>` 取第 1 页读取时返回的总页数。"
   - 理由：标准 ③⑤。
2. `SKILL.md:8`
   - 修改前：`# read-paper`
   - 修改后：`# learn-paper`
   - 理由：标准 ⑦。只改显示标题，配置路径不动。

**必须保留、不能动：**
- 配置路径 `~/.hskill/read-paper/config.json` 与字段名 `output_dir`：虽然沿用了旧名，但这是已部署用户的数据位置，改了会读不到原有配置。[推出]
- 产物文件名 `1-orientation.md` / `2-extraction.md` / `3-critique.md`，`--pass 1|2|3` 及其依赖检查；slug 规则；3 份模板的节标题；3 个标签 `[基于论文]` / `[Agent推断]` / `[需核实]`。[读到]
- 第三遍"不重读 PDF"的约束。[读到]

**未确认：**
- 未确认：本机还装有另一个名为 `read-paper` 的 skill（中文 description，同样是"三遍精读"），它和本 skill 是什么关系、会不会争抢触发。这在精简范围之外，建议单独核实。[读到 skill 列表 / 未查来源]

---

## 3. 潜力低 / 无的 skill

- **probe-session（低）**：步骤 2、3 的 Python `subprocess` 样板（`SKILL.md:39-46`、`SKILL.md:67-76`）可以各压成一条命令，例如"运行 `python3 SKILL_DIR/scripts/list_profiles.py`，解析 stdout 的 JSON"，大约能减 15 行。步骤 4 的 3 条解读与 `scripts/probe.py:238-243` 的输出文字一一对应，必须保留。标题 `# probe-chrome-session`（`SKILL.md:8`）与 name 不一致。description 里的 "extract-url" 指的是一个已归档的 skill，属于触发文本，只标出不改。[读到]
- **extract-vision（低）**：「常见问题」的后两条（`SKILL.md:70-71`）重复了 `SKILL.md:63-65` 的分支规则，可以删。其余每行都是条件或接口：`--lang` 表、退出码 `2`、`{文字} | conf=` 格式、goal 模板。测试要求保留"当前 agent 顺序处理 OCR 文本"和"无原图视觉能力则停止"两句（`tests/skill-portability.test.mjs:43-47`）。[读到]
- **explain-design（无）**：已经按"条件 → 动作 → 产出"写好；`references/archify-usage.md` 是从 archify 原文提炼的约束，已经做了渐进式披露（只读用到的 schema）。唯一可删的是 `SKILL.md:12` 末尾"要求准确、完整、结构清晰"这句空泛要求。跨 skill 接口（archify 的路径查找顺序、`bin/archify.mjs`、`agents/openai.yaml`、frontmatter 的 `disable-model-invocation` / `model`）都不能动。[读到]

---

## 4. 未确认项汇总

| # | skill | 事项 | 把握度 |
|---|---|---|---|
| 1 | extract-cognition | 硬停机检查排在 `mkdir` 之后，片段输入会留下空目录 | 推出 |
| 2 | extract-cognition | 归因层移进 references 后 eval 1 是否仍通过 | 未查 |
| 3 | learn-video | HTTP API 换 focus 与 `rerun summary` 是配合使用还是二选一 | 推出 |
| 4 | learn-video | 失败处理段移出 SKILL.md 会打破测试正则（`SKILL.md:180`） | 读到 |
| 5 | clip-url | Claude 补丁中的 `sessions_spawn` 可能是旧平台语法 | 推出 |
| 6 | clip-url | `CONTENT_THIN` / `THIN_RETRY_USED` 判定的理由与字段含义相反 | 推出 |
| 7 | clip-url | `fixed_tags.txt` 缺失提示在初始化后是否还能触发 | 推出 |
| 8 | pdf-math-translate | `ZH-EN` / `EN-ZH` 的用途；`~/.paddlex/` 是否真是 pdf2zh 的缓存目录 | 未查 |
| 9 | fetch-paper | 渠道顺序以哪套为准；description 写"growing list"但正文没有新增站点的步骤 | 推出 / 读到 |
| 10 | survey-skillrepo | 写 `config.json` 时是否会覆盖 `knowledgeRoot` 等其他字段 | 推出 |
| 11 | survey-skillrepo | 模板中「构建流水线」「模版文件」两节的来源 | 未查 |
| 12 | learn-paper | 与另装的 `read-paper` skill 的关系 | 未查 |

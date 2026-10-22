# simplify-skill 扫描：bundle「coding」

- 扫描日期：2026-10-22；仓库：`/Users/harveyzhang96/Projects/harveyz-skill`（`staging`，工作树干净，只读，没有改动）
- 标准：`.claude/skills/simplify-skill/SKILL.md` 里「拟定建议」的 7 条（下文简称 S1–S7）。只做到拟定建议这一步，没有执行。
- 把握度标注：**【读到】**＝原文或代码里直接看到的；**【推出】**＝根据读到的内容推断的；**【未查】**＝没核实。
- 主线：这个 bundle 里，写得长的 skill（handoff、setup-debug、init-workflow）冗余主要出在「同一条规则写好几遍」和「规则后面跟着很长的理由」，不在判断规则本身。另有 3 个 skill 存在跨 skill 或跨文件的**事实不一致**，比篇幅更值得先修。

**改动前必须知道的护栏【读到】**

- `tests/skill-portability.test.mjs:98-118` 锁定了 `question-me`(3.0.2)、`rephrase`(1.0.2)、`init-project`(0.1.3) 三个 skill 的 version 和 `skills-index.json` 里的 `contentHash`。改这三个 skill 的正文，必须同时升版本号、更新 index 里的 hash、更新测试里写死的版本号。
- 同一个测试文件还按字符串断言正文内容：
  - `init-project` 必须含 `TARGET` 和 `AGENTS.md`，禁止出现 `~/.claude/skills`、`--target claude`；
  - `init-goal` 禁止出现 `/loop`，必须含「持续执行」；
  - `question-me` 禁止出现 `Claude` 字样，必须含「自动提议（等用户确认 y/n）」「当前 agent」；
  - `rephrase` 必须含「仅手动调用」「猜错的代价」以及两条分支原句；
  - `capture-vocab` 必须含 `SKILL_DIR/scripts/vocab.py`。
- `skills/coding/init-goal/tests/init-goal.bats` 按字符串 grep `SKILL.md`，涉及「唯一产物」「不写任何文件」「运行本持续执行的 agent」、`## Step 0/1/2`、`0a/0b/0c`、5 个模版名、`## GOal` 等标题。

---

## 1. Bundle 总览

规模列的口径：`SKILL.md` 加上 agent 会读的 references/assets 文本；括号里另列脚本、测试和 evals，这部分不计入可减比例。

| skill | 当前规模（行） | 优化潜力 | 预估可减比例 | 一句话主要问题 |
|---|---|---|---|---|
| handoff | 424（SKILL 330 + template 66 + schema 28）（+ 脚本 221、bats 415、evals） | 高 | SKILL 约 30%；若按 phase/宿主拆分，单次加载可再少约 30% | 同一禁令重复 4–6 次（如「不要 `git worktree remove`」），设计理由和指令混写，各宿主、画布相关的条件内容全量加载 |
| setup-debug | 866（SKILL 470 + refs 396）（+ evals 44） | 高 | SKILL 约 30%，refs 约 10% | 「执行总览／快速参考」「原则／常见错误」「步骤 4／完成前检查」三组内容重复；验证状态词前后不一致；references 里的命名、路径和 SKILL 对不上 |
| init-workflow | 1062（SKILL 257 + refs md 706 + yml 99）（+ render_docs.py 261） | 中 | SKILL 约 20%，refs 约 10% | Step 7b 复述了脚本已经做的事；Step 5 示例和 reference 逐字重复；lock 文件名有两种写法；references 里残留旧名 `git-workflow-init` |
| question-me | 214（+ scripts 384） | 中 | 约 20% | 选项格式写了 4 遍；反模式表 5 行里有 4 行在复述正文；`infer` 规则只写在阶段 2，阶段 1 没有 |
| init-goal | 247（SKILL 151 + templates 78 + platforms 18）（+ bats 89） | 中 | 约 15% | 「不写文件」讲了 4 遍，而 Step 1 的提示语又说「确认后直接生成文件」，前后矛盾；模版匹配置信度低时没写怎么办 |
| init-project | 376（SKILL 163 + refs 119 + assets 94） | 中（以澄清为主） | 约 10% | 骨架 `AGENTS.md` 指向的 `docs/git-workflow.md` 和 init-workflow 实际产出的 `docs/reference/git-workflow.md` 不一致；跳转语句和失败态有重复 |
| analyze-claudemd | 256（SKILL 114 + criteria 142） | 中（以澄清为主） | 约 10% | Step 4 的「阻塞／建议」分档和 `criteria.md` 每条判据的 `[阻塞]`/`[建议]` 标签冲突 |
| explain-pm | 60 | 低 | 约 10% | 触发、不做、输出三处重复说「不主动、不存档」 |
| capture-vocab | 188（SKILL 42 + refs 146）（+ vocab.py 207、tests） | 低 | < 5% | 已经做过渐进式披露，只剩一句重复 |
| rephrase | 25 | 无 | 0–5% | 25 行，几乎每句都被测试锁定 |
| fork-topic | 20（+ evals 106） | 无 | 0 | 20 行，每行都是规则 |

---

## 2. 潜力为高／中的 skill

### 2.1 handoff（高）

**问题按 7 条标准归类**

- **S2 重复**【读到】
  - 「不要 `git worktree remove`／不要销毁工作区」出现在 `SKILL.md:51-52`、`:69-71`、`:147`、`:150`、`:247`、`:301`。其中 `:147` 和 `:150` 在同一个列表里相隔两行，是同一句话写了两遍。
  - `validate-handoff.sh` 的作用讲了 4 次：`:96-100`、`:127-129`、`:216-219`、`:265-267`。
  - Phase 2.5「打回后必须重走」讲了 4 次：`:20-22`、`:186`、`:244`、`:254-255`。
  - 写入权规则重复：`:263` 与 `:271`，以及 `:173-177`。
  - 冷读测试 `:115-117` 和 `:118-120` 用了同一句括注：「脚本只能校验填了的值合不合法，判断不了你本该填而没填」。
  - 通用兜底 `:321-322` 和 `:48-50` 都在说「裸 cd 不可靠」。
- **S6 解释和指令混写**【读到】：下面这些整句都是「为什么」，不改变任何动作：`:10` 后半、`:36-37`、`:44-47`、`:61-62`、`:158-160`、`:179-180`、`:184`、`:197-199`、`:207-209`、`:237-239`、`:269`（「这条不是流程洁癖……」整段）、`:293-295`。理由并非都该删：`:44-47`（不显式写基线会静默夹带别人的提交）和 `:224-226`（不能写成 `<集成分支>..HEAD`）直接影响执行时怎么判断，建议压成一句保留。
- **S4 渐进式披露**
  - 【读到】`## 平台适配`（`:273-330`，58 行）分 Claude Code、Codex、通用兜底三节，每次运行只会用到其中一节。另外 Phase 1 里散着 Codex 专属的句子：`:39-41`、`:79-80`、`:85-86`、`:89-90`。
  - 【读到】画布节点相关内容（`:59-67`、`:118-120`、`:132-143`）只在 `agent-canvas-ctl` 存在时才生效。
  - 【推出】每次调用只走一个 phase，但 accept（`:195-247`，约 53 行）和自测（`:156-193`，约 38 行）每次都全量加载。拆成 `references/phase-*.md` 后，author 调用可以少加载约 90 行。代价是每次调用多读一个文件，而且 author 起草锚点时看不到 accept 的判法。是否值得拆【未确认】，需要你决定。
- **S5 含糊或矛盾**【读到】
  - `:125` 的标题写着「verify（可选）」，可 `:84` 交付给接手方的指令写的是「先调用 verify 核对，无缺口再开工」。而且 `status → 执行中`（`:154`）、进工作区的规则（`:144-153`）都只写在 Phase 2 里。如果跳过 verify，谁来改 status、按什么规则进工作区，没有着落。
  - `:252`「打回（……退回执行中）」和 `:241`「未达成 → status 置打回」放在一起，看不出接手方开始复修时要不要把 `打回` 改回 `执行中`。
- **S7 跨文件一致性**【读到】`assets/handoff-template.md:59-66` 的「起草流程」复述了 `SKILL.md` Phase 1 第 5–7 步；`:3` 和 `:57` 是同一句话。

**代表性修改**

1. `SKILL.md:144-150`，同一个列表里的重复项
   - 修改前：
     ```
     - **绝不要销毁这个工作区**（`git worktree remove`，或平台的"退出并删除"）——验收还要用。
     - **不要自己 `git worktree add`。** ……
     - **不要 `git worktree remove`**，验收还要用。
     ```
   - 修改后：删掉第三条，只保留第一条。
   - 理由：S2。第一条已经覆盖 `remove` 和平台的「退出并删除」两种情况，第三条没有新信息。

2. `SKILL.md:265-271`，写入权一节
   - 修改前：共 4 段约 9 行，从「校验脚本查不了『谁写的』」一直到「接手方若跳档自填，accept 方按未验收处理，照常逐条重跑。」，中间包括 `:269`「这条不是流程洁癖……字段失效……更难被怀疑」整段。
   - 修改后：
     ```
     脚本不校验值由谁写入，只在 `status: 待验收` 且正文没有标题含「自测」的小节时 exit 1；自测结论的真假靠 accept 方逐条重跑兜底。接手方若自填 `已验收`/`打回`，accept 方按未验收处理，照常重跑。
     ```
   - 理由：S6 和 S2。`:269` 讲的是设计动机，删掉不改变任何一方的动作。「脚本 exit 1」这个条件在 `:216-219` 已经写过，这里只留一句就够。

3. `SKILL.md:10`，开篇定位
   - 修改前：一段 5 句话，夹着「一旦指令里塞进摘要，接手方就会读指令不读文档，摘要与文档立刻变成两个真相源」，以及「不是无论目的是什么都写一份详实清单……」。
   - 修改后：
     ```
     产出并驱动一份自包含交接文档：接手 session 只读它即可续做，完成后由原 session 按约定判据验收。另交付一段可粘贴的接手指令，只含寻址信息（工作区路径、分支、文档路径），不含文档内容摘要，避免形成两个真相源。章节按本次交接目的取舍：缺了会让接手方出问题的才写。
     ```
   - 理由：S6。动作和边界都保留了，因果链压成半句。

**必须保留、不能动的语义**（跨 skill 接口用 ★ 标注）

- ★ phase 名 `author`/`verify`/`accept`，Phase 2.5 没有命令；调用语法 `/handoff <phase> <file>` 和 `$handoff <phase> <file>`。
- ★ frontmatter 字段及枚举值：
  - `status` 取值：`待执行|执行中|待验收|已验收|打回`；
  - `date` 必须与文件名一致；
  - `acceptance: hard|soft`；
  - `workspace_mode: shared-worktree|same-workspace`；
  - 其余字段：`branch`/`worktree`（成对）、`base_commit`（40 位）、`source_node`/`target_node`（uuid）。
- ★ 正文锚点：`**交接目的**`、`## 最小验收锚点`；自测小节标题必须含「自测」。`validate-handoff.sh:184-196` 按这三个字符串认。
- ★ `.hskill/handoff/config.md` 的 `output_dir`/`workflow`/`verification`/`authority`；默认输出到 `docs/commute/`；文件名格式 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`。
- ★ worktree 默认路径 `.claude/worktrees/<分支名把 / 换成 +>`；必须显式写基线分支；`EnterWorktree` 只用 `path` 模式，离开用 `ExitWorktree(action: "keep")`；工具没出现时先用 ToolSearch 找；Codex 用 `codex -C`，verify/accept 阶段不用 `--worktree`。这些内容和仓库根 `CLAUDE.md`「跨 session 交接」一节同源。
- ★ `agent-canvas-ctl whoami / link-nodes / node-relations`，关系类型 `hands-off-to`；不建 `implements`，不调 `capture-requirement`。
- ★ 和 `fork-topic` 的分界（`:33`，以及 description）。
- accept 的规则：
  - 只采信锚点，自己逐条重跑；
  - 回归面按 `merge-base` 取（不能写成 `<集成分支>..HEAD`）；
  - 红了先在分叉点上复跑归因；
  - 重建工作区必须带 `--detach`；
  - 验收记录追加到锚点章节末尾（evals id 2 有断言），与接手方的记录并列、不覆盖；
  - 打回时写清三件事。
- 判成败的命令不接管道；交接文档里不写 memory 内容。
- `assets/handoff-template.md:27-37` 的「接手方须知」会原样落进每份交接文档，属于**输出契约**。它和 SKILL 正文重复，但缩写它就会改变产出物。【未确认】是否允许动。

**拿不准的地方**

- 【未确认】按 phase 拆 references 会不会让 author 写锚点时少考虑 accept 的判法。只靠读文档推不出来，需要跑 evals 0/1 对比。
- 【未确认】verify 标「可选」是有意为之（就地续做时可跳过），还是旧标题没更新。
- 【未查】仓库根 `CLAUDE.md` 的「跨 session 交接」一节和本 skill 大段重叠。那是 analyze-claudemd 的管辖范围，本次没展开。

### 2.2 setup-debug（高）

**问题按 7 条标准归类**

- **S2 重复**【读到】
  - `## 快速参考`（`:456-470`）和 `## 执行总览`（`:26-36`）列的是同一组 9 步，只多了「关键产出」一列。
  - `## 常见错误`（`:348-354`）5 行里有 4 行在复述正文：`:350` 对应原则 2（`:233`），`:351` 对应原则 3（`:240`），`:353` 对应步骤 4 时序条件（`:265`），`:354` 对应原则 1（`:231`）。
  - `## 完成前检查`（`:358-387`）逐条复述步骤 2–4 的要求。
  - 步骤 1 的维度列表（`:77-82`）和紧跟着的摘要表（`:93-99`）字段一一对应。
- **S2 通用教程**【读到】：`:71-73`（「用什么方法都行……」）、`:317-333`（单层查询、诊断顺序，属于通用排障常识）、`:244-245`（原则 4）、`:423`、`:452`。
- **S5 含糊或矛盾**【读到】
  - 验证结果的状态词不统一：
    - `:273` 规定的输出状态是 `OK / MISSING / NO_NEW_OUTPUT`；
    - `:158`、`:278` 另有 `SKIP`；`:285` 用的是 `FAIL`；
    - `:272` 要求检查时间戳格式，但没有给对应的状态名；
    - `:302-307` 的 FAIL 类型表里又出现了「文件为空」「ISO 8601 检查失败」。
  - 验证脚本到底输出哪几种状态，写脚本的 agent 只能自己猜。
- **S7 顺序和一致性**【读到】
  - `## 完成前检查` 放在步骤 7 和步骤 8 之间，但最后一项 `:386-387`「本次新设计的捕获方案**已记录到** references」对应的是步骤 9，而且是无条件要求，和 `:437`「五条全满足才写」矛盾。
  - `:295` 写死了 `verify-logs.sh`，`:51`/`:61` 用的是 `verify-logs.<ext>`。
  - `:35` 写的是「README.md（Reference）」，`:395` 是 `harness/debug/README.md`，前者没写全路径。
- **S7 references 和 SKILL 不一致**【读到】
  - `electron.md:18` 用了「策略 B」，SKILL 里叫「模式 A/B」，而且 SKILL 的模式 B 指「集成到启动脚本」，不是「包裹启动命令」。
  - `electron.md:104`、`:110` 写的是 `main-process.log`，`:76` 和 SKILL `:122` 是 `main.log`。
  - `electron.md:106` 写「第二阶段」，`references/README.md:3` 写「第三阶段」，SKILL 现在叫「步骤 N」。
  - 示例路径全用 `/tmp/myproject-logs`（`docker-compose.md:32`、`electron.md:30`、`:54`、`:84`，`node-process.md:50`、`:53`），而 SKILL `:40-46` 的默认路径是 `<project-root>/tmp/logs/`。
  - 同一条 python 时间戳单行命令，在 `electron.md` 里出现两次（`:9`、`:34`），在 `node-process.md` 里也出现两次（`:18-23`、`:48-50`）。
- 【推出】`node-process.md:30` 的 `sed 's/^\([0-9-]* [0-9:]*\)/\1Z/'` 处理后得到 `2024-01-15 14:30:01Z`，日期和时间之间仍是空格、没有 `T`，过不了 SKILL 要求的 ISO 8601 检查。这属于行为问题，不在精简范围，但建议单独修。

**代表性修改**

1. `SKILL.md:456-470`，`## 快速参考`
   - 修改前：「步骤详情见上方对应节……」加一张 9 行表（步骤 | 关键产出）。
   - 修改后：整节删除，把「关键产出」并进 `:28-36` 每一行的破折号后面。例如 `5. **运行验证脚本** — 非任务驱动型来源全部 OK 才继续`。
   - 理由：S2。两张表的步骤名和顺序完全一样。

2. `SKILL.md:273`，以及 `:285`、`:302`，统一状态词
   - 修改前：
     ```
     - 输出必须逐项列出 OK / MISSING / NO\_NEW\_OUTPUT，不能只打印一个汇总结论
     ```
   - 修改后：
     ```
     - 逐项输出一个状态，不能只打印汇总：`OK` / `MISSING`（文件不存在）/ `NO_NEW_OUTPUT`（无新内容）/ `BAD_TIMESTAMP`（行首非 ISO 8601）/ `SKIP`（任务驱动型，见下）。除 `OK`、`SKIP` 外都算 FAIL。
     ```
     `:302` 的表头相应改成按这几个状态分行。
   - 理由：S5 和 S7。原文的时间戳检查没有对应状态，`FAIL` 也没有定义。【未确认】新增 `BAD_TIMESTAMP` 这个名字会改变验证脚本的输出契约，需要你决定是否接受；保守做法是不新增名字，只写明「时间戳不合格报 FAIL」。

3. `SKILL.md:386-387`，完成前检查里的 references 一项
   - 修改前：
     ```
     **references 更新**
     - [ ] 本次新设计的捕获方案已记录到 `references/tech-stacks/` 对应文件（或新建），供下次复用
     ```
   - 修改后：删掉这一项。步骤 9 本身已经规定了「五条全满足才写」。
   - 理由：S7。原句是无条件要求，和 `:437` 冲突，而且位置在步骤 9 之前。

另外建议把 `## 常见错误` 压成两行：只留正文里没有的那条，即 `:352`「同一后端进程可能同时写 stdout 和文件」，并入步骤 2 的说明。

**必须保留、不能动的语义**

- 产出路径：日志在 `tmp/logs/<source>.log`（gitignore），验证脚本在 `harness/debug/verify-logs.<ext>`（提交），文档在 `harness/debug/README.md` 和 `docs/how-to/debug-env.md`；调用时指定的路径优先。evals 1、2 对这些路径都有断言。
- 每个来源一个独立文件；行首 ISO 8601；已有时间戳的不重复注入；不改变应用行为。
- `[常驻]`/`[任务驱动型]` 的划分，任务驱动型报 `SKIP` 且不计入统计（evals 2 断言 worker 报 SKIP），有 FAIL 时非零退出。
- 模式 A/B，以及模式 B「默认开启、可关闭」的开关。
- 步骤 2 的推导表（`:106-144`）是判断依据，保留。
- 等待时长的校准规则：实测值加 50% 缓冲，不用固定值。
- 写回 references 的五条标准，以及 `references/README.md` 规定的新文件结构和命名。
- 9 步的顺序（先验证、后运行场景、后写文档）。

**拿不准的地方**

- 【未确认】`## 完成前检查` 整节能不能删到只剩步骤 4 没覆盖的几项（比如 `.gitignore`、浏览器 hook）。它可能是有意留的最终闸门。
- 【未确认】references 示例路径改成 `tmp/logs/` 会不会影响你已有项目里按 `/tmp/myproject-logs` 搭好的环境。【未查】

### 2.3 init-workflow（中）

**问题按 7 条标准归类**

- **S2 复述脚本行为**【读到】：`render_docs.py:254-261` 自己会比对、`makedirs`、写文件并打印 `NEW/UPDATED/UNCHANGED`，而 SKILL `:187-192`（7b 第 1、2 条）把这些又描述成 agent 要做的动作。`:185` 列出 7 个占位符后又说「无需逐一处理」。
- **S2 跨文件重复**【读到】
  - Step 5 的呈现示例 `SKILL.md:105-120` 和 `conflict-analysis.md:107-124` 逐字相同。
  - 类型 E 写了三处：`SKILL.md:84-97`、`conflict-analysis.md:130-172`、`lock-file-format.md:39`。
  - hash 计算写了两处：`conflict-analysis.md:50-56`、`hook-templates.md:223-229`。
  - `:241` 把首次安装跳过 Step 4 又说了一遍（`:68` 已写）。
- **S5 含糊**【读到】`:23`「用户拒绝则优雅停止」没说停止时要不要输出什么；`:243`「若有保留的无法映射规则，附注提示」里的「无法映射规则」全文没有定义。
- **S7 字段和路径不一致**【读到】
  - lock 文件名：`:73`、`:215` 和 `lock-file-format.md:3` 是 `.githooks/.workflow-config.lock.yml`，`:225` 的汇报示例是 `.githooks/.workflow-config.lock`。
  - 旧名 `git-workflow-init` 残留在 `lock-file-format.md:5`、`:8`，`hook-templates.md:43`、`:88`、`:134`、`:194`，`acceptance-test.md:147`，`workflow-config.yml:2`、`:4`，`git-workflow-template.md:5-6`。
  - `workflow-config.yml:4`「将此文件复制到项目根目录」和 SKILL Step 2 的首选路径 `.hskill/init-workflow/` 矛盾。
  - `acceptance-test.md:147` 叫用户「重跑 `/git-workflow-init`」，这个命令不存在。

**代表性修改**

1. `SKILL.md:187-193`，Step 7b
   - 修改前：三条，包括「若 `docs/reference/` 不存在则创建」「与现有文件对比……标记 UNCHANGED／UPDATED 或 NEW」「若 `docs/INDEX.md` 存在，追加索引行」。
   - 修改后：
     ```
     #### 7b. 索引
     脚本已负责建目录、比对与写入（输出 NEW / UPDATED / UNCHANGED）。若 `docs/INDEX.md` 存在，追加索引行（已存在则跳过）。
     ```
   - 理由：S2。前两条是脚本行为【读到 `render_docs.py:254-261`】。如果 agent 照着再写一遍，就成了重复劳动。

2. `SKILL.md:105-122`，Step 5 示例
   - 修改前：16 行示例块，加「各冲突类型的完整选项定义见……」。
   - 修改后：
     ```
     呈现格式与 A–E 各类型的选项见 `references/conflict-analysis.md`（「Step 5 冲突呈现格式」「类型 E」两节）；Step 4 已读过该文件。
     ```
   - 理由：S2 和 S4。参考表 `:252` 已经规定 Step 4/5 要读这个文件，示例和 reference 逐字相同。

3. `SKILL.md:225`，lock 文件名
   - 修改前：`.githooks/.workflow-config.lock    UPDATED（记录新配置快照）`
   - 修改后：`.githooks/.workflow-config.lock.yml UPDATED（记录新配置快照）`
   - 理由：S7。另外三处都带 `.yml`。

**必须保留、不能动的语义**

- ★ 配置查找顺序：先 `.hskill/init-workflow/workflow-config.yml`，再两条向后兼容路径，并询问是否迁移。`init-project` 骨架里的 `.gitignore` 注释也点名了这个文件（`gitignore-code:2`）。
- ★ 设 `core.hooksPath .githooks` 和 `merge.ff false`。仓库 `CLAUDE.md` 和 handoff 的工作流都依赖这两项。
- ★ 产出 `docs/reference/git-workflow.md`，Step 8 往 `CLAUDE.md`/`AGENTS.md`/`GEMINI.md` 追加引用段。
- ★ 可以重复运行、做差量检测。`init-project` 的模板故意不给它加 `probe`（`template-schema.md:53-55`、`code.yml:24`）。
- ★ 拒绝 `git init` 时「停止」。`init-project:109` 引用了这个行为。
- 审核规则要一次报全；Step 4 首次安装时跳过；解析 YAML 用 python3、不用 grep；MANAGED 块格式和 hash；冲突类型 A–E，E 默认选 A；MANAGED 块外的用户代码永不覆盖；`enforce: false` 时删除对应块；`NEW/UPDATED/UNCHANGED` 标签；Step 6.5 的 `[y/N]`；lock 文件格式。
- hooks 头部的 `# Generated by git-workflow-init v4.1.0` 和文档模板里的旧名会写进用户仓库，属于**输出契约**。改名会让已部署的 hooks 在下次运行时出现差异，【未确认】要不要一起改。

**拿不准的地方**

- 【未确认】`:243`「无法映射规则」指的是什么，以及能不能删。
- 【未查】`:154` 说「`merge.ff false` 让 pre-commit 能检查合并来源」。git 在干净合并时默认调用的是 `pre-merge-commit`，不是 `pre-commit`，这句的机制前提可能不成立。这是行为问题，不在本次范围，建议另查。

### 2.4 question-me（中）

**问题按 7 条标准归类**

- **S2 重复**【读到】
  - 「至少 3 个选项 + 自定义」出现在 description、`:10`、`:63`、`:79`、`:102`；选项块在 `:65-74` 和 `:104-109` 写了两遍。
  - 渲染命令在 `:83`、`:89-92`、`:199-202` 写了三遍。
  - 「分支切换是自动的」（`:124`）复述了选题逻辑（`:197`）。
  - 反模式表（`:208-214`）里，`:211` 复述 `:151`，`:212` 复述 `:10`，`:213` 复述 `:31`、`:57`，`:214` 复述 `:146`。只有 `:210`「顺序操纵」是新规则。
- **S5 含糊**【读到】
  - 阶段 1 的子节点评估（`:80-82`）只有「是 → 生成／否 → 叶子」，没有阶段 2 `:115` 的「可合理默认的标 `infer`」。三道固定问题的子问题能不能标 infer，原文没说。
  - `:176` 说 `id` 是「2–3 字母」，但示例 `Q1`、`Q2a` 含数字。`render_tree.py:16-21` 的正则是 `\w+`。

**代表性修改**

1. 新增一节「提问格式」放在 `## 流程` 前，`:63-74` 和 `:102-109` 改成引用
   - 修改前（阶段 2 第 2 步）：
     ```
     2. 提问（附至少 3 个选项 + 自定义）：
        [当前节点文本]？
        A. [选项1]  ← 推荐 …… D. 自定义...
     ```
   - 修改后：
     ```
     2. 按「提问格式」提问当前节点
     ```
   - 理由：S2。格式只定义一处，后面改格式时不会出现两处不一致。

2. `:206-214`，反模式表
   - 修改前：5 行表。
   - 修改后：删掉整张表，只把 `:210` 并进选题逻辑（`:197` 之后）：「dep 已满足的 open 节点必须问答或当场评估 infer，不能以『其他节点的答案已覆盖』为由跳过。」
   - 理由：S2。另外 4 行都是正文规则的反面说法。

3. 子节点评估只定义一次（放在「决策树格式」一节），阶段 1 `:80-82` 和阶段 2 `:111-115` 都引用它
   - 理由：S5。顺带消除阶段 1 缺少 `infer` 分支的问题。【未确认】阶段 1 不允许 infer 是否是有意设计；如果是，引用时要写明「阶段 1 不标 infer」。

**必须保留、不能动的语义**

- ★ 测试锁定的字符串：「自动提议（等用户确认 y/n）」「当前 agent」；正文不能出现 `Claude`；version 和 contentHash 被锁定。
- ★ `rephrase` 把多轮澄清交给本 skill（`rephrase/SKILL.md:14`）；`init-project` 的模板 skills 列表里有它。
- ★ 树文本格式 `[label:status]  id=XX  [dep=YY]  文本`，status 取 `done|open|infer|skip`，必须和 `scripts/render_tree.py:16-21` 的正则一致；输出路径 `/tmp/question-me-tree.html`，首次渲染加 `--open`。
- 固定的 Q1–Q3；一次只问一题；选题规则（被依赖次数最多，并列时取最早）；兄弟扫描；重大方向修正的三步；停止条件；阶段 3 摘要格式，以及等用户确认后才执行；「不在范围内」的 6 条。

**拿不准的地方**

- 【未确认】`SKILL_DIR` 在本 skill 里没有定义（`capture-vocab:12` 定义过）。是否要补一句定义，属于澄清，但会改动被 hash 锁定的正文。

### 2.5 init-goal（中）

**问题按 7 条标准归类**

- **S2 重复**【读到】
  - 「本 skill 不写文件、文件由执行 agent 写」讲了 4 遍：`:12`、`:106`、`:148-149`，以及模板本身 `:137-141`。
  - 三个文件路径在 `:14-17` 和 `:149` 各列了一遍。
  - 「一次一条消息」在 `:19` 和 `:57` 写了两遍。
  - `:147` 的顺序执行说明和 `platforms/SKILL.codex.md:7` 重复。
- **S5 矛盾**【读到】`:98` 的提示语「确认后直接**生成文件**」和 `:12`「不写任何文件」矛盾，用户会被误导。
- **S5 缺分支**【读到】`:51`「置信度高时直接套用」，但置信度低时怎么办没写。

**代表性修改**

1. `:98`
   - 修改前：`询问：「确认后直接生成文件，或告诉我需要调整哪个字段。」`
   - 修改后：`询问：「确认后生成 Goal Prompt，或告诉我需要调整哪个字段。」`
   - 理由：S5。这是对用户说的话，和 skill 的输出契约冲突。

2. `:14-17`
   - 修改前：「执行期间由持续执行 agent 生成的文件（slug 取自 GOAL）：」加三行路径。
   - 修改后：删除。路径和时机已经写在嵌入模板的 `## 文档维护` 里（`:137-141`），那一份才是真正交给执行 agent 的。
   - 理由：S2。`bats` 只 grep `~/.hskill/init-goal`、`log.md`、`summary.md` 这几个字符串，模板里都有【读到 `tests/init-goal.bats:81-89`】。

3. `:148-149`
   - 修改前：「首轮运行时，持续执行 agent 会按 `## 文档维护` 的指令把它存为……每轮追加 `log.md`，结束时写 `summary.md`。平台专用启动方式只在 `platforms/` 适配器中说明。」
   - 修改后：只留「平台专用启动方式见 `platforms/` 适配器。」
   - 理由：S2。

**必须保留、不能动的语义**

- ★ 测试锁定：`## Step 0/1/2`、`0a/0b/0c`、「唯一产物」「不写任何文件」、`## 文档维护`、「运行本持续执行的 agent」、5 个模版名（必须留在 `SKILL.md` 的匹配表里）、模板里的 6 个 `##` 标题；`SKILL.md` 里不能出现 `/loop`，必须含「持续执行」。
- ★ 运行时数据目录 `~/.hskill/init-goal/<goal-slug>/{prompt,log,summary}.md`，log 的条目格式 `### Round N — YYYY-MM-DD HH:MM`。
- ★ `platforms/SKILL.claude.md`（`/loop`）和 `platforms/SKILL.codex.md`（「顺序执行」，有测试）是平台补丁。
- 字段名 GOAL/EXECUTION/EVAL/CONSTRAINTS/EXIT_EXPLICIT/EXIT_FALLBACK；澄清优先级和停止条件；slug 规则；`references/templates.md` 的字段值。

**拿不准的地方**

- 【未确认】置信度低时是「退到从零开始」还是「在 0c 顺带确认模版」。这两种做法行为不同，要你定；也可以维持现状不写。

### 2.6 init-project（中，以澄清为主）

**问题按 7 条标准归类**

- **S7 跨 skill 路径不一致**【读到】`assets/skeleton/AGENTS.md:15` 写的是「分支命名与合并流程：见 `docs/git-workflow.md`（由 `/init-workflow` 生成）」，而 init-workflow 实际写入的是 `docs/reference/git-workflow.md`（`init-workflow/SKILL.md:181`）。【推出】init-workflow 的 Step 8 只检查文件里有没有 `docs/reference/git-workflow.md` 链接（`:199`），所以新项目的 `AGENTS.md` 里会同时出现一条错链接和一段追加的 `## Git 工作流`。
- **S2 重复**【读到】
  - `:19-20` 和边界第 2 条 `:25` 重复。
  - 确定 TARGET 的规则写了两遍：`:33-34`、`:59`。
  - Step 3 的「回到下一步」写了两遍：`:105` 和 `:112`。
  - 失败态表 `:153`、`:156` 复述了 Step 1 `:65-66` 和 Step 3 `:109`。
- **S5 措辞**【读到】`:83`、`:95`、`:124` 的「→ 回到 Step N」实际意思是「进入下一步」。Step 3 用「回到」是为了在子 skill 交还控制权后找回跳点，有道理；顺序推进的步骤也用「回到」，就有点费解。
- **S7 自相矛盾**【读到】`:133` 说第 4 段列「首次使用时会问你配置的 skill」，但表里 `:143` 的 `capture-vocab` 写的是「无需配置」。

**代表性修改**

1. `assets/skeleton/AGENTS.md:15`
   - 修改前：`- 分支命名与合并流程：见 \`docs/git-workflow.md\`（由 \`/init-workflow\` 生成）`
   - 修改后：`- 分支命名与合并流程：见 \`docs/reference/git-workflow.md\`（由 \`/init-workflow\` 生成）`
   - 理由：S7。这会改变骨架的产出内容（输出契约），需要你批准。改完要跑 `node --test tests/templates.test.mjs`。

2. `SKILL.md:19-20`
   - 修改前：「**这个 skill 不写任何 `.hskill/<skill>/` 配置**——那些归各 skill 自己，它们都内建了「配置不存在就问用户并写下来」的分支。本 skill 只做编排。」
   - 修改后：删除，并把理由并进边界第 2 条：「**不写任何 `.hskill/<skill>/` 配置**——归各 skill 自己（配置缺失时它们会问用户）」。
   - 理由：S2。

3. `SKILL.md:105-112`
   - 修改前：`:105-107` 一段，`:112`「→ 全部处理完，回到 Step 4。」
   - 修改后：删掉 `:112`。
   - 理由：S2。`:105` 已经写了「全部处理完回到 Step 4」。

**必须保留、不能动的语义**

- ★ 测试锁定：必须含 `TARGET`、`AGENTS.md`，禁止出现 `user.claude.status`、`--target claude`、`~/.claude/skills`；version 和 contentHash 被锁定；`tests/templates.test.mjs` 会校验模板。
- ★ 调用 `/init-workflow`（不带 probe）、`/release-project 重新初始化`；探测路径 `.hskill/release-project/release-profile.md`；`hskill status --json` 的 `user.TARGET.status`/`project.TARGET.status` 判定；`hskill install --scope project --target TARGET`；`hub projects add`。
- 每条命令都用 `cd <PROJECT> && hskill ...`；`update` 状态按「已有」处理；5 条边界；`{{PROJECT_NAME}}` 是唯一的占位符；`on_exists` 取 `skip|append-missing-lines`；Step 0 要建 todo；收尾清单分 5 段；懒配置表。
- `check` 分支只读，不提任何问题。

**拿不准的地方**

- 【未确认】顺序推进处的「回到 Step N」是否有意保持统一措辞。改它不影响行为，但会改动被 hash 锁定的正文。

### 2.7 analyze-claudemd（中，以澄清为主）

**问题按 7 条标准归类**

- **S7 分档规则自相矛盾**【读到】
  - `SKILL.md:94-95` 规定：阻塞 = C2/C3/C4/C5，建议 =「结构类（C11–C14）、措辞类（C16）」。
  - 但 `criteria.md` 把 C6（`:56`）、C10（`:88`）、C13（`:110`）、C17（`:137`）都标成了 `[阻塞]`，其中 C13 恰好在 SKILL 说的「建议」组里。
  - 结果是同一条命中会因为看的文件不同而分到不同档。
- **S2 重复**【读到】
  - Step 2.2（`:65`）复述 C6（`criteria.md:58-62`）。
  - Step 5.4（`:105`）复述 C7 的代价（`criteria.md:68-69`）。
  - `:34` 和 `:71` 都在说「读 criteria、不要凭记忆」。
  - Step 3 的 `:73` 复述 `criteria.md:98-99`。
  - `## 不在范围内`（`:109-114`）和「不触发」（`:24-28`）有 2 条重合。

**代表性修改**

1. `SKILL.md:94-95`
   - 修改前：
     ```
     - **阻塞**：两处都写、改一处会打架的（C3/C4/C5），以及 agent 执行不了的指令（C2）。
     - **建议**：结构类（C11–C14）、措辞类（C16），不改也能用。
     ```
   - 修改后：
     ```
     - 分档按 `criteria.md` 每条的标签：`[阻塞]` 命中 → 阻塞，`[建议]` 命中 → 建议。
     ```
   - 理由：S7。只保留一个来源。【未确认】如果你的本意是 SKILL 里这张列表才算数，就反过来改 criteria 的标签。

2. `SKILL.md:65`
   - 修改前：一长句，讲权威源的查找顺序，以及装机副本会造成两类误判。
   - 修改后：
     ```
     按 C6 定位权威源：项目内源文件 → skill 源仓库 → 装机副本（`~/.claude/skills/`，找到后必须再上溯一层，版本号对上才采信）。
     ```
   - 理由：S2 和 S6。误判的原因已经写在 C6 里。

**必须保留、不能动的语义**

- ★ 指向 `init-skill` 的 `references/skill-standard.md`（存在于 `skills/mint/init-skill/references/skill-standard.md`）【读到】；和 `init-workflow` 的分界。
- 17 条判据 C1–C17 分五组；C11–C14 只适用于流程主导型文档；证据格式 `<源文件>:<行号>`；标注 `[Agent 推断]`/`[需核实]`。
- Step 1 的三项前置检查，以及 `git status` 非空时只读；Step 5 默认不改文件、要等 y/n、不在受保护分支上直接改、不 push；命中 C7 的条目不动。
- description 里的「17 falsifiable criteria」。

**拿不准的地方**

- 【未确认】上面第 1 条，分档以哪一边为准。

---

## 3. 潜力低／无的 skill

- **explain-pm（低）**：「仅手动、不主动、默认不存档」在 `:19`、`:56`、`:60` 说了三遍；「组织维度」`:45-48` 和「保留」清单 `:29-32` 有一半重叠。能删约 6 行，规则都很具体。
- **capture-vocab（低）**：已经按查词／写操作／接入拆好了 references；`SKILL.md:40` 和 `references/project-setup.md:7` 是同一句话，只剩这一处可删。`:42` 的维护者注是有意保留的。
- **rephrase（无）**：一共 25 行，`:14`、`:20`、`:21` 的原句被测试锁定。`:25`「不做」和 `:14` 部分重复，删了只省一行，还得改 hash。
- **fork-topic（无）**：一共 20 行。每行都是一个决策规则或输出约束，和 handoff 的分界写在 description 里（跨 skill 接口，不能动）。

---

## 未确认项汇总

1. handoff：按 phase 或宿主拆分 references 是否值得（多读一次文件，换单次少加载约 90 行）；verify 标「可选」是不是有意的；`打回` 之后 status 怎么流转；「接手方须知」块（输出契约）要不要动。
2. setup-debug：要不要新增 `BAD_TIMESTAMP` 状态名（会改变验证脚本的输出契约）；「完成前检查」整节能不能删减；references 示例路径要不要统一成 `tmp/logs/`。
3. init-workflow：「无法映射规则」的含义；写进 hooks 和文档里的旧名 `git-workflow-init` 要不要改（会让已部署的 hooks 出现差异）；`merge.ff false` 和 pre-commit 的机制关系（【未查】，属于行为问题）。
4. question-me：阶段 1 不允许 infer 是不是有意的；要不要补 `SKILL_DIR` 的定义。
5. init-goal：模版匹配置信度低时怎么处理。
6. init-project：骨架 `AGENTS.md` 的路径修正会改变产出内容，需要批准；「回到 Step N」的措辞。
7. analyze-claudemd：分档以 SKILL 还是 criteria 为准。
8. 范围外，【推出】：`setup-debug/references/tech-stacks/node-process.md:30` 的 sed 产物不符合 ISO 8601。

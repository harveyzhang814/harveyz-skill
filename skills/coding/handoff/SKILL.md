---
name: handoff
description: Use when handing a task across sessions — writing a self-contained handoff doc for a fresh session to pick up (author), sanity-checking an inbound handoff before starting (verify), self-testing against the agreed criteria before reporting the work done or re-submitting after a rejection (self-test), or accepting completed work against the criteria agreed at handoff time (accept). Triggers on phrases like "write a handoff", "hand this off", "pick up this task", "sign off on this work". Not for carrying discussion conclusions into a new topic with no acceptance — use fork-topic for that. Generic skill — project-specific conventions are read from .hskill/handoff/config.md.
version: "1.17.1"
user_invocable: true
---

# 跨 session 任务交接（handoff）

产出并驱动一份自包含交接文档：接手 session 只读它即可续做，完成后由原 session 按约定判据验收。在画布节点里，author 建接手节点并用画布消息往返（见「画布通信」）；否则交付一段可粘贴的接手指令。消息和指令都只含寻址信息（工作区路径、分支、文档路径），不含文档内容摘要。

## Phase 触发判定（先做这一步）

1. 解析 handoff 调用后的文本：`author` / `verify` / `accept`。调用语法按宿主选择：Claude Code
   用 `/handoff accept <file>`，Codex 用 `$handoff accept <file>`；没有 skill 调用语法的宿主直接执行
   对应 phase。
2. 文本未指明 → 看上下文：刚做完规划 → author；拿到别人的交接文档准备开工 → verify；接手方回报完成、要核收 → accept。
   输入以 `[agent-canvas 消息 …]` 开头时，它是另一个节点按「画布通信」发来的，按其中的事件选：
   派发 → verify；verify 缺口 → 回 author 补文档；待验收 → accept；打回 → 复修（Phase 2.5 复修轮）；
   已验收 → 接手方停手。
3. 仍不确定 → **问用户，不猜**。

**Phase 2.5（自测）没有调用命令**：接手方把 `status` 推到「待验收」之前执行，被打回、复修完再执行一遍。

## Phase 1 — author（写交接）

1. **初始化探测**：查 `.hskill/handoff/`。
   - 存在 `config.md` → 读取 `output_dir/workflow/verification/authority`，注入对应章节。
   - 不存在 → **问用户一次**："本项目有无特殊交接约定（输出路径/分支工作流/验证工具）？"
     - 有 → 按 `references/config-schema.md` 引导生成 `.hskill/handoff/config.md`。
     - 无 → 用通用默认（`output_dir=docs/commute/`），以后不再问。
2. **判断目的**：用一句话写出这次交接为了什么（如"接手方续做同一个实现任务"），作为文档的「交接目的」。只带讨论结论开新话题、不需要回来验收的，改用 fork-topic。
3. **汇集上下文**：以**当前对话**为真相源，现状以 git/仓库为准。涉及代码时读 `git status` / `git diff` 核对现状和受影响文件（纯规划交接可跳过）；spec/plan 只给指针。**不引用 memory**（可能陈旧，接手方也读不到）：必要的背景核实后内联写进文档，不留 `[[memory]]` 链接。
4. **备好交接工作区**（接手方会在**另一条分支**上开工时才做；就地同分支续做则整步跳过）：
   分支和 worktree 都由**你**建好，不留给接手方建。
   - 已经在一条 feature worktree 里干活 → 就用它，别新建。
     但如果它是宿主临时创建的 detached/disposable worktree（Codex managed worktree 是典型），
     不要直接把它交给 fresh session：先把工作落到命名分支与可持续存在的共享 worktree。Codex App
     的同一 chat Handoff 不是这里说的 fresh-session 交接。
   - 否则 `git worktree add <路径> -b <分支名> <基线分支>`；路径按 `.hskill/handoff/config.md`
     的 workflow 段给的习惯，没给就用 `.claude/worktrees/<分支名把 / 换成 +>`。
     **基线分支必须显式写出来**（通常是 `staging`）：不写就从主工作树当前 HEAD 拉分支，可能
     静默夹带别的 session 没合并的提交，merge 也不报错。
   - **建完立刻进去**（见文末「平台适配」，进不去时按其「通用兜底」）。不进去，后面不带限定的
     git 命令都作用在**主工作树**上。
   - **建完不要 `git worktree remove`**：它要一直留到验收通过。同一时刻只有一方在里面动手（你写完
     交接就停手），否则会互踩暂存区。
   - 把 `workspace_mode` 填成 `shared-worktree`，分支名填进 `branch`、工作区**绝对路径**填进
     `worktree`。若需要记录分叉依据，可把完整 40 位提交写进 `base_commit`；它只是基线锚点，
     不代表文档或最终改动所在的提交。就地续做填 `same-workspace`，也可为了兼容旧文档省略该字段。
5. **起草**：读 `assets/handoff-template.md`，按其中的候选内容清单逐类过必要性测试——"不写这条信息，接手方会不会出问题"，答案是"会"才写出对应章节，答案是"不会"整节跳过，不留空标题。**交接目的**和**最小验收锚点**这两项任何情况下都必须写。指针式引用权威依据，只内联接手方开工必需的硬核，不重抄 spec 全文。写到**第 4 步那个工作区**里的 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`，按模板填 frontmatter（`status: 待执行`、`date` 与文件名日期段一致、`acceptance` 按最小验收锚点是硬判据还是软判据填 `hard`/`soft`；跨工作区时 `workspace_mode`/`branch`/`worktree` 第 4 步已填）。
6. **建执行节点**（仅当 `agent-canvas-ctl whoami` 能取到自己的节点 id 时做；不在 Agent Canvas
   画布节点里就整步跳过，不报错，第 9 步改走可粘贴指令，`source_node`/`target_node` 两个字段删掉）。
   命令用法以 `agent-canvas-ctl help <命令>` 为准：
   - `whoami` 取到的自己的节点 id 填进 frontmatter 的 `source_node`。
   - 建接手节点：`agent-canvas-ctl create-pty-node --node-type claude-code --title "接手：<任务一句话>"
     --cwd <工作区绝对路径> --task-type execute`。类型默认 `claude-code`，用户点名了别的 agent（如
     `codex`）就用那个。`--cwd` 填第 4 步的 worktree；就地续做填当前工作目录。**这里不带
     `--message`**：文档还没过门禁、没提交，派发消息留到第 9 步发。
   - `agent-canvas-arrange put <接手节点 id>` 放上画布（建出来默认不在画布上）。
   - 建关系 `agent-canvas-ctl link-nodes --from <自己的 nodeId> --to <接手节点 id> --type hands-off-to`，
     把接手节点 id 填进 `target_node`。接手方在 verify 只核对、不重复建。
   - 建节点失败 → 把报错告诉用户，`target_node` 留空，第 9 步退回可粘贴指令，由接手方在 verify
     回填。**不要换个参数再建一个**；退出码 2 先 `agent-canvas-ctl search-nodes <标题关键词> --kind pty`
     核对是不是已经建出来了（旧版 App 不认 `--kind` 时去掉它；结果是顶层数组或 `{results}` 里的数组）。
7. **跑完整性门禁**（见下），不过不放行。
8. **落库**：把交接文档 commit 进这条分支（没提交的文档接手方看不到）。同目录同分支续做、或把
   文档整份贴给对方时，此步可省。
9. **派发**：第 6 步建出了接手节点 → 把下面这段接手指令写进临时文件，追加一行
   「你由节点 <source_node> 派来；verify 有缺口、自测后推「待验收」，都按 handoff skill 的「画布通信」
   用 `agent-canvas-ctl send <source_node>` 回报」，然后 `agent-canvas-ctl send <target_node> --file <临时文件>`
   发出去（不加 `--expect-reply`）。告诉用户派给了哪个节点、`messageId` 是什么，**结束本轮**；
   不 sleep、不轮询、不 `wait-reply`，接手方的回报会作为新的一轮到达。
   不在画布里，或第 6 步没建成 → 给用户输出这段**可粘贴的接手指令**。

   两种情况都只放寻址信息，不放文档内容摘要。形如：

   ```
   接手任务。工作区已建好，不要自己建：
     <worktree 绝对路径>
   按你所在平台的方式进入它（Claude Code 用 EnterWorktree(path: "<路径>")；
   Codex 从该路径启动/绑定 workspace，或把每次操作显式限定到该绝对路径；别靠跨调用的裸 cd）。
   分支 <branch>，已被这个工作区 checkout（git worktree add 会失败，属正常）。
   <若 config.md 的 workflow 段有开工前置命令，原样列在这里>
   交接文档：<相对于工作区的文档路径>
   先调用 handoff 的 verify phase 核对，无缺口再开工：
     Claude Code: /handoff verify <文档路径>
     Codex: $handoff verify <文档路径>
   ```

   **同一段指令换个动词就是验收指令**（Claude Code 用 `/handoff accept <文档路径>`，Codex
   用 `$handoff accept <文档路径>`）——两种情况都一并给用户，
   将来验收若换了新 session，它靠这段就能回到正确的工作区。用户把这段弄丢了也不致命：
   `git worktree list` 能查回分支与工作区的对应关系，只是要多问一步。

## 完整性门禁（author 收尾硬动作）

**第一道，机器校验**：`bash <skill 目录>/scripts/validate-handoff.sh <文档路径>`。
它查 frontmatter 字段齐不齐/枚举值合不合法、`date` 与文件名对不对得上、`branch` 在本仓库
存不存在、`source_node`/`target_node` 是不是合法 uuid、正文有没有「交接目的」与
「最小验收锚点」，并对指不到文件的引用路径给 WARN。**exit 非 0 不放行**；WARN 逐条判断
是笔误还是指向本次待创建的产物。

**第二道，冷读测试**（查脚本查不了的够不够、对不对）：假装自己是零上下文的接手方，只有这份文档，逐项自问——

- **交接目的**和**最小验收锚点**（脚本已确认它们在）**内容够用吗**？目的这一句说得清这次交接
  是为了什么吗？
- 文档里**实际出现**的每个章节是否自洽：
  - 出现了「关键决定」→ 够不够让接手方**不用回问**原 session？
  - 出现了「范围铁律」→ in/out 是否都点名，没有模糊地带？
  - 出现了「受影响文件/落点」→ 与「相关文档索引」描述是否自洽？
  - 最小验收锚点若是硬判据 → **可证伪**吗？（有明确对/错判定，不是"让它工作"这种软标准）
    并与 frontmatter 的 `acceptance` 对得上吗？（硬判据填 `hard`，软判据填 `soft`——accept
    阶段按这个字段分叉，填反了验收方式就跑偏）
- 接手方要在**另一条分支**上开工 → `branch` 与 `worktree` 都填了吗？（脚本查不出漏填；漏了
  接手方不知道去哪开工，你验收时也找不回它改过的文档）
- 你**在画布节点里**（`agent-canvas-ctl` 存在）→ frontmatter 的 `source_node` 填了吗？第 6 步建成了
  接手节点时 `target_node` 也填了吗？（同样查不出漏填；缺了往返消息找不到收件方）
- **反向检查**：有没有哪类内容被必要性测试判定为"不需要"，但其实接手方会因此卡住、走错方向、或推翻已定方案？（防止必要性判断本身错判）

任一项答不上 → 补文档、重跑门禁。核对结论可选择性附在文档末尾。

## Phase 2 — verify（接手方开工前）

- **先跑机器校验**：`bash <skill 目录>/scripts/validate-handoff.sh <文档路径>`。exit 非 0
  说明这份文档本身不合规（字段缺失/枚举非法/`branch` 在本仓库不存在），直接打回原 session，
  不要自己猜着补。WARN（引用路径指不到文件）不阻断，但要当作可疑点带进下面的怀疑视角核对。
- 读交接文档，以**怀疑视角**核对可执行性，逐项列出缺口/断链/歧义（复用上面的冷读测试项，只核对文档里实际出现的章节）。
- 有缺口 → 打回原 session 补，别硬开工。画布内按「画布通信」把缺口清单 `send` 给 `source_node`，
  然后结束本轮等它补完再发回来。
- **建 `hands-off-to` 关系**（仅当 `agent-canvas-ctl` 存在、且 frontmatter 有 `source_node` 时做；
  任一条件不满足就整步跳过，不报错）：
  1. `agent-canvas-ctl whoami` 取自己的节点 id。
  2. `agent-canvas-ctl node-relations <自己的 nodeId> --direction in --type hands-off-to` 核对——
     已经有一条来自交接源节点的边（author 那边建过）就跳过，不重复主张。
  3. 没有 → `agent-canvas-ctl link-nodes --from <source_node> --to <自己的 nodeId> --type hands-off-to`。
  4. 把自己的节点 id 填进 frontmatter 的 `target_node`——两端都填齐，这次交接在画布上才是闭环的，
     accept 时一眼看得出关系建没建。author 已经填了却不是你的 id → 打回确认，不要自己改。

  **只建这一条边。**不要顺带把自己挂到交接源节点实现的需求上（不建 `implements`），也不要调
  `capture-requirement` 另立需求——需求已经挂在交接源节点上，接手节点该不该关联需求是另一个
  问题，不在这次交接的范围内。
- **进 author 备好的工作区开工**（frontmatter 的 `workspace_mode` 是 `shared-worktree`，或旧文档
  有 `worktree` 时）：按文末「平台适配」进去，然后核对 `git branch --show-current` 与 `branch`
  一致且不为空，就在这里干活。
  - **绝不要销毁这个工作区**（`git worktree remove`，或平台的"退出并删除"）——验收还要用。
  - **不要自己 `git worktree add`。** 那条分支已经被这个工作区 checkout 了，再建会直接失败；
    而且你另建一个，原 session 验收时会回到它自己建的那个，看不到你的改动。
  - 路径不存在（被误删了）→ 打回原 session 重建，别自己找地方开工——你选的位置它不知道。
  - `branch` 与实际不符 → 以**文档**为准打回确认，不要自己改字段。
- 无缺口 → `status` 置 `执行中`，若文档有「工作流约定」章节按其开工，没有就直接开工。

## Phase 2.5 — 自测（接手方推 `status` 到「待验收」之前的硬闸门）

**「待验收」的意思是「我已按锚点跑过一遍、拿得出结果」，不是「我改完了」。**

推 `status` 之前做完这四件事，缺一件就别推：

1. **逐条实跑「最小验收锚点」全集**——不是只跑你改动相关的那几条。`acceptance: hard`
   逐条判对错；`soft` 按其描述做定性判断。文档若还点名了「必须复跑的既有资产」，一并跑。
   项目自己的验证约定（跑什么测、要不要真产物 E2E）见 `.hskill/handoff/config.md` 的
   `verification` 段。
2. **判成败的命令不接管道**（`| tail` 的退出码恒为 0，输出也会被截断）。
3. **结果写成独立小节**，标题形如 `## 接手方自测记录（<日期>）`——**标题里必须有「自测」
   二字**，`validate-handoff.sh` 按这个词认这一节。逐条列 pass/fail，附实际跑的命令。
   写进你自己这一节，别混进原 session 的验收记录。
4. **有红就不许推 `status`。** 两条出路，没有第三条：
   - 修到绿；
   - 或者认为那条红不构成未达成（例如它在你动手之前就红），**在自测记录里那一条旁边写出
     归因证据**（比如在分叉点上跑同一条命令的结果），并显式声明「带着这条红送验」。
     **不许沉默推上来。**

四件都做完、`status` 置「待验收」后，画布内按「画布通信」通知 `source_node` 来验收，然后停手。

自测不替代 accept：accept 方仍逐条自己重跑（Phase 3）。

### 复修轮（被打回之后）

- 开始复修时，把 `status` 从 `打回` 改回 `执行中`。
- 复修完**重新走一遍本 phase**，`status` 才能再置回「待验收」。
- **自测范围默认是锚点全集，不是被打回的那几条。** 要缩小，必须在复修自测记录里给出两样
  东西：改动范围证据（`git diff --name-only <打回点提交>..HEAD`）+「为什么其余条目不可能
  被这些改动波及」的论证。给不出就跑全集。
- 记录**另起一节**，标题形如 `## 接手方复修自测记录（第 N 轮）`，同样必须含「自测」二字。
  不覆盖、不合并前几轮。
- 打回记录点名了修法就照做；**不认同要在复修记录里写出理由退回讨论，不要静默换一种改法**。
  尤其不要把一条刚开始真的会红的断言改回恒真。

## Phase 3 — accept（原 session 验收）

**先到位，再验收**：验收命令在**被验代码所在的工作区**跑，不在主工作树或 staging/main/master
上。那里没有接手方的改动，跑出来的绿是**别的代码的绿**。

1. **回到交接工作区**：按文末「平台适配」进 author 阶段第 4 步建的那个 worktree。
   路径取自你自己的上下文、author 第 9 步的验收指令，或 frontmatter 的 `worktree`；都没有就用
   `git worktree list` 按分支名查。只有同目录同分支续做才跳过本步。
   - **在那里重读一遍交接文档。** 你手上这份可能是 author 时写的旧版；接手方的自测记录、
     `status`、以及被修正过的字段，全都只存在于那个工作区里的那一份。
   - 后面**每一条**验收命令都在这个工作区里跑。
   - 路径不在了（被谁 remove 了）→ `git worktree list` 看这条分支现在挂在哪；都没有就用
     `git worktree add --detach <临时路径> <branch>` 重建，验完 remove。**必须带 `--detach`**——
     一条分支不能被两个 worktree 同时 checkout。
   - 跑第一条验收命令之前确认到位：`git -C <验收目录> rev-parse --abbrev-ref HEAD` 落在
     staging/main/master 上，说明你还在主工作树，停下来查，别接着跑。
2. **先跑一次机器校验**：`bash <skill 目录>/scripts/validate-handoff.sh <文档路径>`。
   `status` 是「待验收」却没有含「自测」的小节 → 脚本直接 exit 1。**这种情况按未达成处理，
   当场置「打回」退回去，不必开始逐条重跑。**

3. 找文档里的**最小验收锚点**——这是唯一固定依据（第 4 步的回归面核对不算另加判据）。**接手方自填的结论一律不采信，逐条自己跑。** frontmatter 的 `acceptance` 指明是哪一档：`hard`（逐条对/错）→ 按锚点描述**逐条实跑**（单测/E2E/核验）；`soft`（定性描述）→ 按其描述做定性判断。字段与锚点正文不符时**以正文为准**并把字段改对——字段是索引，正文才是判据。
4. **回归面核对**（锚点跑完之后；锚点已点名的不重复跑）。
   - **取实际改动面**：`git -C <验收目录> diff $(git -C <验收目录> merge-base <集成分支> HEAD)..HEAD --name-only`。
     `<集成分支>` 是 author 建分支时写明的基线（通常是 `staging`）。**不要写成
     `<集成分支>..HEAD`**：集成分支在分叉之后前进过，别人合入的改动会被混成本分支的。
   - **找被波及组件现有的回归测试**：按上面的文件找它们所属组件在仓库里已有的测试，锚点没点名
     的也跑。怎么跑、要不要真产物 E2E、隔离方式，按 `.hskill/handoff/config.md` 的
     `verification` 段和项目自己的验证 skill。判成败的命令同样不接管道。找不到被波及的既有测试，
     就在验收记录里写"已核对，无"并附改动面。
   - **红了先归因，再定性**：在分叉点上跑同一条命令（`git worktree add --detach <临时路径>
     $(git merge-base <集成分支> HEAD)`，验完 remove；别在交接工作区里切走）。
     分叉点绿、现在红 → 本次改动引入，**按回归打回**；分叉点也红 → 既有的红，不打回，
     在验收记录里写明命令和两边结果。
   - **锚点遗漏要记**：跑到了锚点没点名的回归项，不论绿红都记入验收记录。**本次改动引入的回归
     照样打回，哪怕锚点没点名**；锚点漏写的责任在写交接/验收一方，不在接手方——接手方只对被
     约定的判据负责。
5. 把验收结果（每条 pass/fail，或整体达成/未达成，含第 4 步的回归面核对）追加记录到最小验收锚点所在章节末尾。**接手方若已自填过验收记录，另起小节并列，不覆盖也不合并。** 其中若有与实跑不符的陈述，**显式写出更正**，不要静默改掉。
6. 达成 → `status` 置 `已验收`；未达成 → `status` 置 `打回`。打回记录必须写清三件事：
   **哪几条未达成**、**为什么**（判据原文 vs 实跑结果）、以及
   **复修后要重跑的范围**（默认全集；认为可以只跑子集就在这里点名）。
7. 画布内写完 `status` 后按「画布通信」通知 `target_node`：打回 → 让它复修；已验收 → 让它停手。
8. 若第 1 步通过宿主能力进入了工作区，按文末对应宿主的方式离开并**保留**工作区；使用显式路径
   兜底时无需切换会话状态，停止操作即可。任何情况下都不 remove，合并与清理由 author 后续处理。

## 状态生命周期

`待执行`（author 写完）→ `执行中`（verify 通过 / 接手方开工）→ `待验收`（接手方自测通过后，
见 Phase 2.5）→ `已验收` / `打回`（accept 判定）。

`打回` → 接手方开始复修时改回 `执行中` → 重走 Phase 2.5 → 才能再置回 `待验收`。

`status` 是各 phase 间唯一协调锚点，无需外部状态存储。

要扫「哪些交接还没验收」，**别在当前工作树里 grep**——在途交接的文档都在各自的交接工作区里，
主工作树上那份（如果有）是合并后的历史归档，状态是旧的。正确做法是先 `git worktree list`
列出所有工作区，再到每个工作区的 `<output_dir>` 里 grep `status`。

**写入权按 phase 分：接手方最多只能把 `status` 推到「待验收」，且推之前必须过 Phase 2.5。`已验收` / `打回` 只能由原 session 在 accept 之后写。**

接手方若自填 `已验收`/`打回`，accept 方**按未验收处理**，照常重跑。

## 画布通信（往返消息）

frontmatter 的 `source_node` 和 `target_node` 都填了、且你在画布节点里时，交接双方的往返一律用
`agent-canvas-ctl send <对方 nodeId> <正文>`（长正文用 `--file`）。收件方只取 frontmatter 的这两个
字段，不从信封头或节点标题去猜。任一条件不满足 → 不发消息，告诉用户由用户转达。

| 事件 | 方向 | 正文（文档路径 + 一句结论） |
|---|---|---|
| 派发 | author → 接手方 | author 第 9 步的接手指令 |
| verify 有缺口 | 接手方 → author | 缺口清单，`status` 不动 |
| 补完文档 | author → 接手方 | 补了哪几处，请重新 verify |
| 自测通过 | 接手方 → author | 已置「待验收」，请 accept |
| 打回 | author → 接手方 | 已打回，见文档里的打回记录 |
| 已验收 | author → 接手方 | 已验收，停手 |

- **消息只寻址，不搬内容**：缺口、自测结果、打回理由先写进工作区里那份文档，消息里只给文档路径和
  一句结论。文档是唯一真相源。
- **发消息就是交出工作区**：发之前把自己的改动写完；发完就停手，不再碰这个工作区。
- **不加 `--expect-reply`，发完结束本轮**：不 sleep、不轮询 `get-message`、不 `wait-reply`。对方回报
  靠它自己 `send` 过来，会作为你的新一轮到达。执行常常跨多轮，等「这一轮结束自动回复」会提前拿到
  半截结果。
- **发之前看对方还在不在**：`agent-canvas-ctl get-node <对方 nodeId>` 的 `actions[]` 里 `send_message`
  不是 `available: true`（进程已退出等）→ 不发，告诉用户，由用户重启节点或转达，不改发给别的节点。
- **审批与失败不重试**：接手方 → author 这个方向，对方不是你建的节点，首次会弹审批卡，等用户在画布
  上批。被拒绝、超时、`held`、`failed`、`interrupted` 都告诉用户，由用户决定，不要重发。

## 平台适配（怎么进出交接工作区）

各 phase 说的「进入工作区」按宿主执行下面对应小节；宿主不在表里、对应能力不可用/被拒绝、或该
小节明确列出的例外，才按「通用兜底」办。**已知宿主不得因兜底也能完成命令就跳过原生进入/离开动作。**
判据：**后续命令的工作目录是不是那个工作区**。

### Claude Code

| 动作 | 手段 |
|---|---|
| 进入 | `EnterWorktree(path: "<工作区绝对路径>")` |
| 离开 | `ExitWorktree(action: "keep")` |

同仓库 worktree 必须走上表：若工具尚未出现在可用工具中，先用 ToolSearch 找到
`EnterWorktree` / `ExitWorktree`，不要直接降级成 `cd`。只有 `path` 被拒绝（例如跨仓库）或工具
确实不可用时才走通用兜底。

- **只用 `path` 模式，绝不用 `name`**：`name` 会自建分支（`worktree-<name 把 / 换成 +>`，常过不了
  分支命名 hook），基线默认取 `origin/<默认分支>`。分支名和基线必须由 author 定，所以只能
  **先 `git worktree add` 建、再 `path` 进**。
- `path` 只认**当前仓库**（或嵌套在其中的仓库）注册过的工作区，跨仓库直接拒绝。
  交接双方在同一仓库时不是问题；跨仓库按「通用兜底」办。
- 必须由当前会话**直接调**，不能交给 fork/subagent 代调。
- 离开一律 `action: "keep"`，交接期间绝不 `remove`。

### Codex

Codex 没有 `EnterWorktree` / `ExitWorktree` 工具。fresh session 接手 author 已建好的共享工作区时，
选择一种能让**该 session 的 workspace 根就是 frontmatter `worktree`** 的启动方式：

- CLI：从该目录启动，或用 `codex -C <worktree>` / `codex exec -C <worktree> ...`。
- Codex App：打开该持久 worktree 作为 workspace，再开始新的接手 chat。
- 宿主无法重新绑定 workspace：按下面「通用兜底」逐条使用绝对路径与显式 working directory。

Codex 的 `--worktree` 会创建**新的 managed worktree**，不是进入 author 已建的路径；verify / accept
阶段不要用它，也不要让接手 session 创建替代 worktree。App 的 **Handoff** 是同一 chat 在 Local 与
Worktree 之间移动，适合延续同一 chat，但不替代这里由独立接手者执行、再由 accept 方复核的流程。

Codex 调用本 skill 用 `$handoff <phase> <文档路径>`；`/skills` 是选择器，不要把 `$handoff`
写成一个不存在的 native slash command。

### 通用兜底（无此类能力，或跨仓库）

每条命令自带限定，**不要靠裸 `cd`**（多数 harness 里它只在单条命令内有效）。

- git：`git -C <工作区> <命令>`
- 其他 shell 命令：`cd <工作区> && <命令>` 写在**同一条**命令里
- **读写文件一律用绝对路径**：`git -C` 管不住 Read / Edit / Write / Grep / Glob，相对路径按会话
  当前目录解析，改到另一份同名文件也**照样成功**。

人类接手时同理：`cd <工作区>` 之后不要再切回去。

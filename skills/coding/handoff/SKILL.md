---
name: handoff
description: Use when handing a task across sessions — writing a self-contained handoff doc for a fresh session to pick up (author), sanity-checking an inbound handoff before starting (verify), or accepting completed work against the criteria agreed at handoff time (accept). Triggers on phrases like "write a handoff", "hand this off", "pick up this task", "sign off on this work". Generic skill — project-specific conventions are read from .hskill/handoff/config.md.
version: "1.7.0"
user_invocable: true
---

# 跨 session 任务交接（handoff）

产出并驱动一份自包含交接文档：接手 session 只读这一份文件即可续做，完成后由原 session 按约定判据验收。文档直接整份喂给新 session，不做可粘贴 prompt。文档内容跟着这次交接的实际目的走——不是无论目的是什么都写一份详实清单，缺了会让接手方出问题的信息才写，其余不写。

## Phase 触发判定（先做这一步）

1. 解析斜杠命令后文本：`author` / `verify` / `accept`（如 `/handoff accept <file>`）。
2. 文本未指明 → 看上下文：刚做完规划 → author；拿到别人的交接文档准备开工 → verify；接手方回报完成、要核收 → accept。
3. 仍不确定 → **问用户，不猜**。

判定后跳到对应 phase 段执行。

## Phase 1 — author（写交接）

1. **初始化探测**：查 `.hskill/handoff/`。
   - 存在 `config.md` → 读取 `output_dir/workflow/verification/authority`，注入对应章节。
   - 不存在 → **问用户一次**："本项目有无特殊交接约定（输出路径/分支工作流/验证工具）？"
     - 有 → 按 `references/config-schema.md` 引导生成 `.hskill/handoff/config.md`。
     - 无 → 用通用默认（`output_dir=docs/commute/`），以后不再问。
2. **判断目的**：从当前对话判断这次交接是为了什么——不套预设分类，一句自然语言判断即可（例如"接手方续做同一个实现任务"或"把讨论结论作为背景传给接手方去开展新话题"）。这句话会写进文档开头的"交接目的"，且始终存在，不可省略。
3. **汇集上下文**：以**当前对话**为真相源。涉及代码时读 `git status` / `git diff` 核对现状、排查受影响文件（若这两类内容按第 4 步判定为必要），并作为门禁的现实校验（纯规划交接可跳过）；spec/plan 作为权威指针。**不把 memory 写进文档**——memory 可能陈旧、且接手方访问不到你的 memory 目录；若某条 memory 是承载性背景，把**核实过的事实**内联进去，别留 `[[memory]]` 死链。现状一律以 git/仓库为准，不以 memory 为准。
4. **备好交接工作区**（接手方会在**另一条分支**上开工时才做；就地同分支续做则整步跳过）：
   分支和 worktree 都由**你**建好，不留给接手方建。这是整条交接链能闭环的关键——工作区是你建的，
   你就一直知道它在哪；验收时直接回到这里读那份被接手方改过的文档，不必去别处找、更不必扫描。
   - 已经在一条 feature worktree 里干活 → 就用它，别新建。
   - 否则 `git worktree add <路径> -b <分支名>`；路径按 `.hskill/handoff/config.md` 的 workflow
     段给的习惯，没给就自己定一个仓库内的稳定位置。
   - **建完不要 `git worktree remove`。** 接手方要进来干活，你验收时还要再进来一次。这个工作区
     在整条交接链上一直活着，直到验收通过。
   - 把分支名填进 frontmatter 的 `branch`、工作区**绝对路径**填进 `worktree`。
   - **同一时刻只有一方在这个工作区里动手**：你写完交接就停手，接手方做完停手，再轮到你验收。
     两个 session 同时在一个工作区里跑 git 会互踩暂存区。
5. **起草**：读 `assets/handoff-template.md`，按其中的候选内容清单逐类过必要性测试——"不写这条信息，接手方会不会出问题"，答案是"会"才写出对应章节，答案是"不会"整节跳过，不留空标题。**交接目的**和**最小验收锚点**这两项任何情况下都必须写。指针式引用权威依据，只内联接手方开工必需的硬核，不重抄 spec 全文。写到**第 4 步那个工作区**里的 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`，按模板填 frontmatter（`status: 待执行`、`date` 与文件名日期段一致、`acceptance` 按最小验收锚点是硬判据还是软判据填 `hard`/`soft`；`branch`/`worktree` 第 4 步已填）。
6. **画布节点登记**（仅当 `agent-canvas-ctl` 命令存在时做；不在 Agent Canvas 画布节点里就整步跳过，不报错）：
   - 跑 `agent-canvas-ctl whoami` 取自己的节点 id，填进 frontmatter 的 `source_node`。
     这个字段是接手方**唯一**能找回你这个节点的线索——文档路径和分支名都指认不到画布上的
     节点实体。不在画布节点里就整个字段删掉，别留空值。
   - 若这次交接**你已经能指认接手节点**（例如接手用的 PTY 节点是你亲手创建的）→ 当场建关系
     `agent-canvas-ctl link-nodes --from <自己的 nodeId> --to <接手节点 nodeId> --type hands-off-to`，
     并把接手节点 id 填进 `target_node`，接手方只核对、不重复建。
   - 指认不到接手节点（常态：接手方是还不存在的下一个 session）→ 只填 `source_node`，`target_node`
     留空给接手方在 verify 阶段回填。归属规则是**谁先能同时指认两端谁建**，另一方只核对。
7. **跑完整性门禁**（见下），不过不放行。
8. **落库**：把交接文档 commit 进这条分支——未提交的文档接手方根本看不到，等于没交出去。
   **不要 `git worktree remove`**（见第 4 步）：这个工作区既是接手方的落脚点，也是你验收时要回来
   的地方。接手方就在同一目录同一分支续做、或文档整份贴给对方时，此步可省。
9. **交付**：告知用户交接文档路径、**worktree 路径与分支名**，说明下个 session 直接整份喂入即可。

## 完整性门禁（author 收尾硬动作）

**第一道，机器校验**：`bash <skill 目录>/scripts/validate-handoff.sh <文档路径>`。
它查 frontmatter 字段齐不齐/枚举值合不合法、`date` 与文件名对不对得上、`branch` 在本仓库
存不存在、`source_node`/`target_node` 是不是合法 uuid、正文有没有「交接目的」与
「最小验收锚点」，并对指不到文件的引用路径给 WARN。**exit 非 0 不放行**；WARN 逐条判断
是笔误还是指向本次待创建的产物。

它查的是**在不在、合不合法**，查不了**够不够、对不对**——那是下面这道。

**第二道，冷读测试**：假装自己是零上下文的接手方，只有这份文档，逐项自问——

- **交接目的**和**最小验收锚点**（脚本已确认它们在）**内容够用吗**？目的这一句说得清这次交接
  是为了什么吗？
- 文档里**实际出现**的每个章节是否自洽：
  - 出现了「关键决定」→ 够不够让接手方**不用回问**原 session？
  - 出现了「范围铁律」→ in/out 是否都点名，没有模糊地带？
  - 出现了「受影响文件/落点」→ 与「相关文档索引」描述是否自洽？
  - 最小验收锚点若是硬判据 → **可证伪**吗？（有明确对/错判定，不是"让它工作"这种软标准）
    并与 frontmatter 的 `acceptance` 对得上吗？（硬判据填 `hard`，软判据填 `soft`——accept
    阶段按这个字段分叉，填反了验收方式就跑偏）
- 接手方要在**另一条分支**上开工 → `branch` 与 `worktree` 都填了吗？（脚本只能校验填了的值
  合不合法，判断不了"你本该填而没填"。这两个字段漏了，接手方不知道去哪开工，而你验收时也
  找不回它改过的那份文档——整条交接链就断在这里）
- 你**在画布节点里**（`agent-canvas-ctl` 存在）→ frontmatter 的 `source_node` 填了吗？（脚本
  只能校验填了的值合不合法，判断不了"你本该填而没填"；缺了接手方就建不出 `hands-off-to`，
  交接关系在画布上永远不成立）
- **反向检查**：有没有哪类内容被必要性测试判定为"不需要"，但其实接手方会因此卡住、走错方向、或推翻已定方案？（防止必要性判断本身错判）

任一项答不上 → 补文档、重跑门禁。核对结论可选择性附在文档末尾。

## Phase 2 — verify（接手方开工前，可选）

- **先跑机器校验**：`bash <skill 目录>/scripts/validate-handoff.sh <文档路径>`。exit 非 0
  说明这份文档本身不合规（字段缺失/枚举非法/`branch` 在本仓库不存在），直接打回原 session，
  不要自己猜着补。WARN（引用路径指不到文件）不阻断，但要当作可疑点带进下面的怀疑视角核对。
- 读交接文档，以**怀疑视角**核对可执行性，逐项列出缺口/断链/歧义（复用上面的冷读测试项，只核对文档里实际出现的章节）。
- 有缺口 → 打回原 session 补，别硬开工。
- **建 `hands-off-to` 关系**（仅当 `agent-canvas-ctl` 存在、且 frontmatter 有 `source_node` 时做；
  任一条件不满足就整步跳过，不报错）：
  1. `agent-canvas-ctl whoami` 取自己的节点 id。
  2. `agent-canvas-ctl node-relations <自己的 nodeId> --direction in --type hands-off-to` 核对——
     已经有一条来自交接源节点的边（author 那边建过）就跳过，不重复主张。
  3. 没有 → `agent-canvas-ctl link-nodes --from <source_node> --to <自己的 nodeId> --type hands-off-to`。
  4. 把自己的节点 id 填进 frontmatter 的 `target_node`——两端都填齐，这次交接在画布上才是闭环的，
     accept 时一眼看得出关系建没建。

  **只建这一条边。**不要顺带把自己挂到交接源节点实现的需求上（不建 `implements`），也不要调
  `capture-requirement` 另立需求——需求已经挂在交接源节点上，接手节点该不该关联需求是另一个
  问题，不在这次交接的范围内。
- **进 author 备好的工作区开工**（frontmatter 有 `worktree` 时）：`cd <worktree>`，核对
  `git rev-parse --abbrev-ref HEAD` 与 `branch` 一致，然后就在这里干活。
  - **不要自己 `git worktree add`。** 那条分支已经被这个工作区 checkout 了，再建会直接失败；
    而且你另建一个，原 session 验收时会回到它自己建的那个，看不到你的改动。
  - **不要 `git worktree remove`**，验收还要用。
  - 路径不存在（被误删了）→ 打回原 session 重建，别自己找地方开工——你选的位置它不知道。
  - `branch` 与实际不符 → 以**文档**为准打回确认，不要自己改字段：字段是 author 立的约，
    改它等于单方面改约。
- 无缺口 → `status` 置 `执行中`，若文档有「工作流约定」章节按其开工，没有就直接开工。

## Phase 3 — accept（原 session 验收）

**先到位，再验收。** 验收在**被验代码所在的工作区**跑——不在主工作树、不在核心分支
（staging / main / master）上跑。主工作树通常停在集成分支，那里根本没有接手方的改动：
在那里跑出来的绿是**别的代码的绿**，比不跑更有害，因为它看起来像验过了。

1. **回到交接工作区**：`cd` 进 author 阶段第 4 步建的那个 worktree（frontmatter 的 `worktree`）。
   没有这个字段 → 这次交接不涉及独立工作区（同目录同分支续做），就地验收，跳过本步。
   - **在那里重读一遍交接文档。** 你手上这份可能是 author 时写的旧版；接手方的自测记录、
     `status`、以及被修正过的字段，全都只存在于那个工作区里的那一份。读错版本不会报错，
     只会让你对着过时的内容验收。
   - 后面**每一条**验收命令都在这个目录里跑（`cd` 进去，或 `git -C <worktree>`）。
   - 路径不在了（被谁 remove 了）→ `git worktree list` 看这条分支现在挂在哪；都没有就用
     `git worktree add --detach <临时路径> <branch>` 重建，验完 remove。**必须带 `--detach`**——
     一条分支不能被两个 worktree 同时 checkout。
   - 跑第一条验收命令之前确认到位：`git -C <验收目录> rev-parse --abbrev-ref HEAD` 落在
     staging/main/master 上，说明你还在主工作树，停下来查，别接着跑。
2. 找文档里的**最小验收锚点**——这是唯一固定依据。**接手方自填的结论一律不采信，逐条自己跑**：验证产物"存在"不等于"跑得过"，点得出脚本名不等于那个脚本此刻是绿的。frontmatter 的 `acceptance` 指明是哪一档：`hard`（逐条对/错）→ 按锚点描述**逐条实跑**（单测/E2E/核验）；`soft`（定性描述）→ 按其描述做定性判断。字段与锚点正文不符时**以正文为准**并把字段改对——字段是索引，正文才是判据。
3. 把验收结果（每条 pass/fail，或整体达成/未达成）追加记录到最小验收锚点所在章节末尾。**接手方若已自填过验收记录，另起小节并列，不覆盖也不合并**——两份并排放着，后来人才看得出哪些结论被第二方复核过。其中若有与实跑不符的陈述，**显式写出更正**，不要静默改掉：静默改掉等于把同一个错误留给下一次。
4. 达成 → `status` 置 `已验收`；未达成 → `status` 置 `打回` 并写明哪里没达成、为什么，退回接手方。
5. **达成才算真正完成**（硬判据要求逐条全绿；软判据按其描述定性判断是否达成）。

## 状态生命周期

`待执行`（author 写完）→ `执行中`（verify 通过 / 接手方开工）→ `待验收`（接手方回报完成）→ `已验收`（accept 判定达成）/ `打回`（accept 判定未达成，退回执行中）。

`status` 是三 phase 间唯一协调锚点，无需外部状态存储。

要扫「哪些交接还没验收」，**别在当前工作树里 grep**——在途交接的文档都在各自的交接工作区里，
主工作树上那份（如果有）是合并后的历史归档，状态是旧的。正确做法是先 `git worktree list`
列出所有工作区，再到每个工作区的 `<output_dir>` 里 grep `status`。

**写入权按 phase 分：接手方最多只能把 `status` 推到「待验收」。`已验收` / `打回` 只能由原 session 在 accept 之后写。**

校验脚本查不了这条——它看不出某个值是谁写的。这是约定，靠 accept 方兜底（见本节末）。

这条不是流程洁癖。「已验收」的全部信息量就是**做事的人之外的另一方查过**；做事的人一旦能自己写它，它就退化成「做事的人说做完了」——而这个信息「待验收」里已经有了，两个状态变成同义词，字段失效。风险还会反向放大：一份自填的「已验收」通常附着一张全 PASS 的表，比没有记录更难被怀疑。

接手方若跳档自填，accept 方**按未验收处理**，照常逐条重跑。

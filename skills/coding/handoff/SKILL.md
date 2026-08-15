---
name: handoff
description: Use when handing a task across sessions — writing a self-contained handoff doc for a fresh session to pick up (author), sanity-checking an inbound handoff before starting (verify), or accepting completed work against the criteria agreed at handoff time (accept). Triggers on phrases like "write a handoff", "hand this off", "pick up this task", "sign off on this work". Generic skill — project-specific conventions are read from .hskill/handoff/config.md.
version: "1.1.0"
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
4. **起草**：读 `assets/handoff-template.md`，按其中的候选内容清单逐类过必要性测试——"不写这条信息，接手方会不会出问题"，答案是"会"才写出对应章节，答案是"不会"整节跳过，不留空标题。**交接目的**和**最小验收锚点**这两项任何情况下都必须写。指针式引用权威依据，只内联接手方开工必需的硬核，不重抄 spec 全文。写到 `<output_dir>/YYYY-MM-DD-<topic>-handoff.md`，状态置 `待执行`。
5. **跑完整性门禁**（见下），不过不放行。
6. **交付**：告知用户文档路径，说明下个 session 直接整份喂入即可。

## 完整性门禁（author 收尾硬动作）

**冷读测试**：假装自己是零上下文的接手方，只有这份文档，逐项自问——

- **交接目的**和**最小验收锚点**都在吗？（这两项任何情况下不能省）
- 文档里**实际出现**的每个章节是否自洽：
  - 出现了「相关文档索引」→ 每个引用路径**真实存在**吗？（实际 `ls`/读一下核对，不靠记忆）
  - 出现了「关键决定」→ 够不够让接手方**不用回问**原 session？
  - 出现了「范围铁律」→ in/out 是否都点名，没有模糊地带？
  - 出现了「受影响文件/落点」→ 与「相关文档索引」描述是否自洽？
  - 最小验收锚点若是硬判据 → **可证伪**吗？（有明确对/错判定，不是"让它工作"这种软标准）
- **反向检查**：有没有哪类内容被必要性测试判定为"不需要"，但其实接手方会因此卡住、走错方向、或推翻已定方案？（防止必要性判断本身错判）

任一项答不上 → 补文档、重跑门禁。核对结论可选择性附在文档末尾。

## Phase 2 — verify（接手方开工前，可选）

- 读交接文档，以**怀疑视角**核对可执行性，逐项列出缺口/断链/歧义（复用上面的冷读测试项，只核对文档里实际出现的章节）。
- 有缺口 → 打回原 session 补，别硬开工。
- 无缺口 → 状态置 `执行中`，若文档有「工作流约定」章节按其开工，没有就直接开工。

## Phase 3 — accept（原 session 验收）

1. 找文档里的**最小验收锚点**——这是唯一固定依据。硬判据（逐条对/错）→ 按其描述**逐条实跑**（单测/E2E/核验）；软判据（定性描述）→ 按其描述做定性判断。
2. 把验收结果（每条 pass/fail，或整体达成/未达成）追加记录到最小验收锚点所在章节末尾。
3. 达成 → 状态置 `已验收`；未达成 → 状态置 `打回` 并写明哪里没达成、为什么，退回接手方。
4. **达成才算真正完成**（硬判据要求逐条全绿；软判据按其描述定性判断是否达成）。

## 状态生命周期

`待执行`（author 写完）→ `执行中`（verify 通过 / 接手方开工）→ `待验收`（接手方回报完成）→ `已验收`（accept 判定达成）/ `打回`（accept 判定未达成，退回执行中）。

状态字段是三 phase 间唯一协调锚点，无需外部状态存储。

---
name: recap
description: "Recap the big picture of the current conversation for a human who has lost track of it or wants to restart the overall work in a fresh session: what it is about and where it stands, current state and next step, decisions (with reasons, including rejected options), open questions, background, and pointers to docs, code and branches for the next agent to investigate. Output is rendered Markdown in the reply, human-first and agent-usable. Text only: no files, branches, or acceptance. Use fork-topic to split off a single side topic; use handoff when work must come back for acceptance. Only on the user's request; do not suggest it unprompted. Triggers: '/recap', 'full recap', 'big picture', 'where are we overall', 'recap the whole conversation'."
user_invocable: true
version: "1.0.0"
---

# recap — 回顾当前对话的全貌

把当前对话写成一份全局回顾。读者主次：人第一，用来找回对全貌的掌控；新 session 的 agent 第二，用来知道从哪开始调查。

- 依据只有当前对话 + 第 2 步的核实结果。memory 不进报告：可能陈旧，新 session 也读不到。
- 只输出文本：不落文件、不建分支、不验收、不替用户派发。

## 步骤

1. **抽取**：通读对话，归入下面七节。对话被压缩过时，压缩前的内容只剩摘要：相关条目标"未核实"，并在第 1 节后注明"早期内容来自压缩摘要"。
2. **轻量核实**：要写进报告的路径、分支、文件逐个查是否存在；涉及代码时看一眼 `git status`。对话所述与磁盘不符的记入第 7 节，不替用户判断哪边对。只查存在，不读内容逐条对照——那是新 session 的调查。
3. **起草**：按七节顺序写，套下面的可读性标准。
4. **删减**：每条问"不写这条，人会不会判断错？agent 会不会走错路？"两个都"不会"就删。篇幅不设上限，靠这一步控制。
5. **输出**：直接输出 Markdown，不包代码块。

## 七节（倒金字塔：读到哪停都不亏）

| # | 章节 | 内容 |
|---|---|---|
| 1 | 一句话 | 在做什么 + 到哪了。必写 |
| 2 | 当前状态与下一步 | 做完了什么、卡在哪、下一步。必写 |
| 3 | 已定结论 | 每条带理由；否决的方案写"否决 X，因为……"，防止新 session 重提 |
| 4 | 未决问题 | 各自卡在什么上 |
| 5 | 背景 | 目标、约束、用户说过的偏好 |
| 6 | 线索 | 文档、代码、分支的指向 |
| 7 | 核实冲突 | 第 2 步发现的不符处 |

3–7 节用不上就整节省略，不留空标题。

## 可读性标准

- **第 1 节一句话可决策**：只读它就能决定要不要往下读。
- **每节首句即该节结论**，之后才展开；只扫各节首句也能拼出全貌。
- **每条脱离上下文可读**：不写"上面那个方案""刚才的问题"；对话里临时起的代号，展开，或首次出现时用一句话锚定。
- **把握度三档分开标**：对话里明确定下的 / 推出来的 / 未核实的。
- **不添加对话里没有的结论。**
- **线索一条一行，只给指向、不抄内容**：`` `路径` — 为什么看 ``。人读破折号后的理由，agent 拿路径；磁盘上查得到的内容不写摘要。

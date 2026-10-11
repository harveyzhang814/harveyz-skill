---
name: fork-topic
description: "Fork a side topic out of the current discussion into a concise, paste-ready prompt for another agent session. Writes in full only what the receiver cannot find on its own (the goal, conclusions reached, rejected options and why, the user's stated preferences); for anything findable in files or the repo, gives a pointer to where to look instead of the content. Outputs text only: no files, branches, or acceptance. Use handoff instead when the work must come back for formal acceptance. Only on the user's request; do not suggest it unprompted. Triggers: '/fork-topic', 'fork this topic', 'split this off into a new session', 'spin off a side discussion', 'take these conclusions into a new topic'."
user_invocable: true
version: "1.0.0"
---

# fork-topic — 把支线话题分出去

讨论中冒出一个支线话题，要交给另一个 agent 单独展开；或者带着本次讨论的结论去开一个新话题。本 skill 把它写成一段**精简的可粘贴 prompt**。

主次：目的是把支线分出去；约束是 prompt 尽可能精简；手段是接手方**查不出**的写全，**查得出**的只给线索。

只输出文本：不落文件、不建分支或工作区、不验收、不替用户派给其他 agent。结果要回来被正式验收 → 用 handoff。

## 流程

1. **确定支线话题**：以用户说的为准。说不清要分出去的是哪个话题 → 问一句，不猜。
2. **抽取**：从当前对话里挑出与这个支线相关的信息，逐条判接手方查不查得出（判据见下）。与支线无关的主讨论内容不进 prompt；用户点名要带过去的背景结论算相关。
3. **判断回流**：主讨论在等这个支线的结论吗（比如主讨论的某个决定被它卡住）？在等 → 写「交回要求」；不等 → 不写。
4. **起草**：按「候选项」顺序组织，语言跟随当前对话。
5. **自检**，三道都过才输出：
   - 查不出的写全了吗？漏了，接手方会重新纠结已定的事、重提已否决的方案、或违背用户偏好。
   - 查得出的是不是只给了线索？逐条找有没有文件内容、代码结构、仓库文档的摘要或推测被写进来，有就删到只剩位置和用途。
   - 每一句都来自对话、且支线用得上吗？自己的推论、扩写、对话里没出现过的约束，删掉。
6. **输出**：prompt 放在一个代码块里。代码块外最多一句说明。

## 判据：查不查得出

| 信息在哪 | 处理 |
|---|---|
| 磁盘、仓库、接手方能访问的系统 | **线索**：位置 + 为什么相关，不写内容 |
| 只在当前对话里（含尚未落盘的草稿） | **写内容**，只写支线用得上的部分 |

线索说清"去哪找、为什么看"，到此为止：

- 对："看 `skills/coding/handoff/SKILL.md` author 第 2 步——它判断交接目的的方式是本话题的起点"
- 错：把第 2 步的内容抄进来，或改写成摘要

## 候选项

按顺序写；除「目标」外，用不上的整项省略，不留空标题、不写"无"。

| 候选项 | 写什么 | 何时写 |
|---|---|---|
| 目标 | 支线要讨论/解决什么，从哪个主讨论分出来。一两句 | 必写 |
| 已定结论 | 主讨论里定下的、与支线相关的结论 | 有相关结论 |
| 否决方案 | 否决了什么 + 为什么 | 有否决过的方案 |
| 偏好与约束 | 用户在对话里明确说过的 | 有 |
| 线索 | 每条一行：位置 + 为什么相关 | 有可查资料 |
| 交回要求 | 结束时给一段可贴回主讨论的结论 | 第 3 步判定主讨论在等 |

这是顺序，不是表单：为了填满而写的项直接删。

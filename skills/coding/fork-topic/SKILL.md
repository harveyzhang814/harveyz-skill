---
name: fork-topic
description: "Fork a side topic out of the current discussion into a concise, paste-ready prompt for another agent session. Text only: no files, branches, or acceptance. Use handoff instead when the work must come back for formal acceptance. Only on the user's request; do not suggest it unprompted. Triggers: '/fork-topic', 'fork this topic', 'split this off into a new session', 'spin off a side discussion', 'take these conclusions into a new topic'."
user_invocable: true
version: "1.0.0"
---

# fork-topic — 把支线话题分出去

把讨论中的支线（或带着本次结论开的新话题）写成一段精简的可粘贴 prompt，交给另一个 agent。

主次：目的是分出去；约束是尽可能精简；手段是查不出的写全，查得出的只给线索。

- **查不出的写全**：只在对话里的东西——目标、已定结论、否决方案及理由、用户说过的偏好与约束、未落盘的草稿。只写支线用得上的。
- **查得出的只给线索**：磁盘、仓库、接手方能访问的系统里的东西，写去哪找 + 为什么看，不抄内容、不写摘要。
- **不添加**对话里没有的结论、约束或推论。
- **交回要求**只在主讨论正等着这个结论时写。
- 只输出文本：不落文件、不建分支、不验收、不替用户派发。prompt 放在一个代码块里（内容含代码块时外层用 4 个反引号），代码块外最多一句说明。

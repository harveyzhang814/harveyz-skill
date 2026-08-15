---
name: rephrase
description: "Single-pass rephrasing of a user statement into a more precise, less ambiguous, more actionable version, then either auto-proceeds or asks for confirmation based on Claude's own reliability judgment. Triggers: '/rephrase', '/rephrase <statement>', 'rephrase this', 'help me restate this more precisely'."
user_invocable: true
version: "1.0.1"
---

# rephrase — 单轮改写澄清

对用户的一句话表述做单轮改写，让它更精确、更少歧义、更可执行。不预设"合格表述"的标准或清单，由 Claude 依据当前语境自行判断。

## 触发

仅手动调用：`/rephrase` 或 `/rephrase <表述>`。不自动检测、不主动建议。多轮追问式澄清是 `question-me` 的职责，不是本 skill。

## 执行

1. **取待改写内容**：带参数用参数；无参数用用户上一条消息；两者都没有就直接问用户要表述。
2. **改写**：消歧义、补全隐含主语/宾语、明确动作对象，视原文缺什么而定——原文已经清楚就不用大改，也不要顺手加原文没提的验收标准/范围。
3. **判断可靠性**：不是看"改写里有没有任何未明说的假设"（几乎总有），而是看**猜错的代价**——如果涉及在多个同权重候选（哪个文件、哪个服务）里武断选一个，选错会做错事，判不可靠；如果只是无关紧要的实现细节、执行风险低、改错了也好回退，判可靠。
4. **分支**：可靠 → 展示改写结果，直接执行，不等确认。不可靠 → 展示改写结果和存疑点，等用户确认要不要改。

## 不做

多轮追问式澄清、强制补充验收标准/范围边界、自动触发。

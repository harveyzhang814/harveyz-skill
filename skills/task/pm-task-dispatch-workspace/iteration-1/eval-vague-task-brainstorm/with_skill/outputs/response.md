# PM Task Dispatch — Eval Response

**Input:** Harvey 说："研究一下 AI 这个方向"

---

## Steps Taken

1. *Read the skill* at `skills/task/pm-task-dispatch/SKILL.md` to understand the full workflow.

2. *Step 1 — Understand the task:* Harvey's instruction is "研究一下 AI 这个方向" (roughly: "do some research on the AI direction"). This is a research-type request with no specified scope, purpose, output format, assignee, constraints, or priority.

3. *Step 2 — Clarification judgment:* Applied the decision tree from the skill:
   - Is this a vague instruction? **Yes.** The skill explicitly flags this pattern in its negative example section:
     > Harvey: "研究一下 AI 模型" → Step 2 triggers: use brainstorming to confirm with Harvey.
   - "AI 这个方向" is even vaguer than the example. No task scope, no research purpose, no constraints, no assignee are provided.
   - **Conclusion: brainstorming is mandatory before any further steps.**

4. *Brainstorming — Clarification questions formulated* (see section below). No task file was created.

---

## Clarification Questions to Ask Harvey

Before proceeding to Step 3 (analysis) or Step 4 (task creation), I would ask Harvey the following:

1. **具体研究哪个 AI 方向？**
   - 例如：大语言模型（LLM）、多模态、AI Agent、语音识别（STT/TTS）、图像生成、推荐系统、AI 基础设施/MLOps、某个具体竞品或开源项目……
   - "AI 方向" 范围太广，需要缩小到一个具体领域。

2. **研究目的是什么？**
   - 技术选型（为某个具体产品/功能选择方案）？
   - 学习/了解某个领域的现状？
   - 竞品分析？
   - 为某个项目做可行性调研？
   - 找到可以落地的商业机会？

3. **期望输出是什么形式？**
   - 一份研究报告（org-mode notes）？
   - 结构化的对比表格？
   - 一个可执行的建议/方案？
   - 简短的摘要还是深度分析？

4. **有没有资源或时间约束？**
   - 是否需要调用付费 API？访问特定数据源？
   - 期望多快完成？

5. **派发给哪个 Agent（或是否需要我来决定）？**
   - 如果已经有倾向的执行 Agent（如 research-scientist），请告知；否则我会在 Step 3 根据任务类型匹配。

---

## Task File Creation

**No task file was created.**

*Why not:* The instruction "研究一下 AI 这个方向" is a vague directive that matches the skill's mandatory brainstorming trigger. Per the skill's Step 2 decision tree, a task file must not be created until Harvey's intent is confirmed. Creating a task file now would result in an underspecified task that would stall or fail when an agent tries to execute it — exactly the failure mode shown in the skill's negative example.

The correct next action is to present the clarification questions above to Harvey and wait for his answers before proceeding to Step 3 (analysis), Step 4 (task document creation), and Step 5 (dispatch).

# init-goal — Codex 适配器

适用平台：Codex

不要声称 Codex 有面向用户的持续执行斜杠命令或内建调度能力。把完整 Goal Prompt 交给当前执行 agent；若控制器提供持续执行或 controller-managed delegated child 调度，控制器负责启动和每轮完成后的继续决定。

若这些能力不可用，必须**顺序执行**：同一执行 agent 完成一轮，读取该轮的评估和 `log.md`，再由用户或控制器明确决定是否继续下一轮；达到明确退出条件、兜底条件或用户中断时写入 `summary.md`。

# clip-url — Codex 补丁

适用平台：Codex

---

## ① Subagent 派发与完成等待

已观察到：控制器管理的 Codex delegated child 可以接收受限任务并在完成后返回结果。需要派发时，由控制器管理该 child 的派发并等待完成通知；只在收到该任务的完成结果后，才读取 `RESULT:` 等报告字段并继续下一步。

不要把这个观察结果表述为面向最终用户的斜杠命令，也不要臆造通用 API 名称或调用语法。若当前会话没有控制器管理的 delegated child 派发与完成等待能力，必须**顺序执行**：当前 agent 直接完成 Subagent 1、3、2 的同一任务内容，每项完成并取得报告后再进行下一项。

## ② 变量来源

`SKILL_DIR` 为 Codex 安装本 skill 的目录（即包含 `scripts/` 的那一级），在 subagent
任务代码中直接使用该路径字符串。

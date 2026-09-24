# clip-url — Codex 补丁

适用平台：Codex

---

## ① Subagent 派发与完成等待

已观察到：控制器管理的 Codex delegated child 可以接收受限任务并在完成后返回结果。需要派发时，由控制器管理该 child 的派发并等待完成通知；只在收到该任务的完成结果后，才读取 `RESULT:` 等报告字段并继续下一步。

不要把这个观察结果表述为面向最终用户的斜杠命令，也不要臆造通用 API 名称或调用语法。若当前会话没有控制器管理的 delegated child 派发与完成等待能力，必须**顺序执行**：当前 agent 直接完成 Subagent 1、3、2 的同一任务内容，每项完成并取得报告后再进行下一项。

## ② 变量来源

文章存储路径由 Python 脚本在运行时从 `~/.hskill/config.json` 的 `knowledgeRoot` 字段
计算（`store_config.py`），固定词表仍从 `~/.hskill/url-extract/config.json` 读取
（`VAULT_PATH` 字段已退休，目录名 `url-extract` 是历史遗留，仅保留固定词表用途），
**均无需 Agent 传参**。默认 Chrome profile 由 browser-fetch 侧持久化，调用方不传。

`SKILL_DIR` 为 Codex 安装本 skill 的目录（即包含 `scripts/` 的那一级），在 subagent
任务代码中直接使用该路径字符串。

# clip-url — Hermes 补丁

适用平台：Hermes

> **⚠️ 未验证。** 本补丁从未在 Hermes 上实际运行过，下方 subagent 派发语法尚未确认。
> Agent 读到本行时，必须先告知用户「clip-url 在 Hermes 平台未验证，subagent 派发
> 语法待补」，再询问是否继续，不要直接尝试派发。

---

## ① Subagent 派发

**待补。** 需要在 Hermes 上实际运行一次，记录可用的 subagent 派发调用语法后填入此处。

## ② 变量来源

`VAULT_PATH` 和固定词表由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json`
读取，**无需 Agent 传参**。默认 Chrome profile 由 browser-fetch 侧持久化，调用方不传。

`SKILL_DIR` 为 Hermes 安装本 skill 的目录（即包含 `scripts/` 的那一级），在 subagent
任务代码中直接使用该路径字符串。

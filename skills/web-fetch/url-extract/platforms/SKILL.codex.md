# url-extract — Codex 补丁

适用平台：Codex

---

## ① Subagent 派发

使用 Codex 平台的 subagent 派发机制执行任务。

## ② 网页内容获取

使用 Codex 平台的网页获取工具获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`。

## ③ 变量注入

通过环境变量或 Codex 平台的变量系统注入，执行 SKILL.md 中的代码时直接使用实际值替换 `VAULT_PATH`、`SKILL_DIR`、`CHROME_PROFILE` 占位。

# url-extract — Hermes 补丁

适用平台：Hermes

---

## ① Subagent 派发

使用 Hermes 平台的 subagent 派发机制执行任务。

## ② 网页内容获取

使用 Hermes 平台的网页获取工具获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`。

## ③ 变量注入

通过 Hermes vars.json 或环境变量注入，执行 SKILL.md 中的代码时直接使用实际值替换 `VAULT_PATH`、`CHROME_PROFILE` 占位。

`SKILL_DIR` 由平台自动提供，无需用户配置：值为 Hermes 安装本 skill 的目录（即包含 `scripts/` 的那一级目录）。

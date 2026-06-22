# url-extract — Codex 补丁

适用平台：Codex

---

## ① Subagent 派发

使用 Codex 平台的 subagent 派发机制执行任务。

## ② 网页内容获取

使用 Codex 平台的网页获取工具获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`。

## ③ 变量来源（运行时 config.json）

`VAULT_PATH` 和 `CHROME_PROFILE` 由 Python 脚本在运行时从以下文件自动读取，**无需 Agent 传参**：

```
~/.hskill/url-extract/config.json
```

`SKILL_DIR` 为 Codex 平台固定值（Codex 安装本 skill 的目录，即包含 `scripts/` 的那一级目录），在 subagent 任务代码中直接使用该路径字符串。

配置文件不存在时，执行 SKILL.md「初始化流程」引导用户写入配置。

# url-extract — Claude Code 补丁

适用平台：Claude Code（harveyz-skill）

---

## ① Subagent 派发

```
sessions_spawn \
  --task "<任务内容>" \
  --runtime "subagent" \
  --mode "run" \
  [--runTimeoutSeconds <秒>]
```

## ② 网页内容获取

使用 `web_fetch` 内置工具获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`。

## ③ 变量来源（运行时 config.json）

`VAULT_PATH` 和 `CHROME_PROFILE` 由 Python 脚本在运行时从以下文件自动读取，**无需 Agent 传参**：

```
~/.hskill/url-extract/config.json
```

`SKILL_DIR` 为 Claude Code 平台固定值，在 subagent 任务代码中直接使用此路径字符串：

```
$HOME/.claude/skills/url-extract
```

配置文件不存在时，执行 SKILL.md「初始化流程」引导用户写入配置。

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

## ③ 变量注入

由 `vars.json` 在安装/运行时替换，语法为 `{{变量名}}`：

| 抽象变量 | 实际语法 |
|----------|----------|
| `VAULT_PATH` | `{{VAULT_PATH}}` |
| `SKILL_DIR` | `{{SKILL_DIR}}` |
| `CHROME_PROFILE` | `{{CHROME_PROFILE}}` |

执行 SKILL.md 中的代码时，将所有 `VAULT_PATH`、`SKILL_DIR`、`CHROME_PROFILE` 占位替换为对应的 `{{变量名}}`，由 vars.json 注入实际值。

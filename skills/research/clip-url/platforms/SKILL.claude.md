# clip-url — Claude Code 补丁

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

## ② 变量来源

`VAULT_PATH` 和固定词表由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json`
读取，**无需 Agent 传参**（目录名 `url-extract` 是历史遗留，clip-url 沿用同一份配置，
以便两者抓过的文章互相去重）。默认 Chrome profile 由 browser-fetch 侧持久化，
调用方不传。

`SKILL_DIR` 为本平台固定值，在 subagent 任务代码中直接使用此路径字符串：

```
$HOME/.claude/skills/clip-url
```

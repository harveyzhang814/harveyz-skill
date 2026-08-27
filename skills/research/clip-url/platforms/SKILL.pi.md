# clip-url — Pi 补丁

适用平台：Pi（需已安装 `pi-subagents` 扩展：`pi install npm:pi-subagents`）

---

## ① Subagent 派发

使用 `subagent` 工具，必须同时提供 `agent` 和 `task` 两个参数（只传 `task` 会报错 `Provide exactly one mode`）：

```
subagent({ agent: "worker", task: "<任务内容>" })
```

`agent` 固定使用 `worker`（实现型子代理，可编辑文件、执行 bash）。超时时间由任务本身的脚本 `timeout` 参数控制，无需在 `subagent` 调用层单独设置。

## ② 变量来源

`VAULT_PATH` 和固定词表由 Python 脚本在运行时从 `~/.hskill/url-extract/config.json`
读取，**无需 Agent 传参**（目录名 `url-extract` 是历史遗留，clip-url 沿用同一份配置，
以便两者抓过的文章互相去重）。默认 Chrome profile 由 browser-fetch 侧持久化，
调用方不传。

`SKILL_DIR` 为本平台固定值，在 subagent 任务代码中直接使用此路径字符串：

```
$HOME/.pi/agent/skills/clip-url
```

# url-extract — Pi 补丁

适用平台：Pi（需已安装 `pi-subagents` 扩展：`pi install npm:pi-subagents`）

---

## ① Subagent 派发

使用 `subagent` 工具，必须同时提供 `agent` 和 `task` 两个参数（只传 `task` 会报错 `Provide exactly one mode`）：

```
subagent({ agent: "worker", task: "<任务内容>" })
```

`agent` 固定使用 `worker`（实现型子代理，可编辑文件、执行 bash）。超时时间由任务本身的脚本 `timeout` 参数控制，无需在 `subagent` 调用层单独设置。

## ② 网页内容获取

Pi 无内置网页抓取工具。使用 bash 工具执行 `curl` 获取目标 URL 的 HTML，保存到 `/tmp/fetched_page.html`：

```bash
curl -sL -A "Mozilla/5.0" "<URL>" -o /tmp/fetched_page.html
```

若结果内容单薄（<20 blocks 或 <3000 字符），`playwright_web.py` 等脚本会自动改用 Playwright + Chrome Cookie 直接导航重试，无需在此步骤处理 JS 渲染或登录态。

## ③ 变量来源（运行时 config.json）

`VAULT_PATH` 和 `CHROME_PROFILE` 由 Python 脚本在运行时从以下文件自动读取，**无需 Agent 传参**：

```
~/.hskill/url-extract/config.json
```

`SKILL_DIR` 为 Pi 平台固定值，在 subagent 任务代码中直接使用此路径字符串：

```
$HOME/.pi/agent/skills/extract-url
```

配置文件不存在时，执行 SKILL.md「初始化流程」引导用户写入配置。

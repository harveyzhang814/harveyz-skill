# sync-ytchannel — Pi 补丁

适用平台：Pi

---

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Pi 平台固定值：`$HOME/.pi/agent/skills/sync-ytchannel`

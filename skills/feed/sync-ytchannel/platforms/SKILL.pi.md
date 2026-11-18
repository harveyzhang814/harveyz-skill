# sync-ytchannel — Pi 补丁

适用平台：Pi

---

## ② 变量来源

名册、游标与存档由 `feedr` 持有（`command -v feedr` 检查），无需 Agent 传参。默认
Chrome profile 由 feedr 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Pi 平台固定值：`$HOME/.pi/agent/skills/sync-ytchannel`

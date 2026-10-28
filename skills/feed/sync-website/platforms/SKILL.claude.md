# sync-website — Claude Code 补丁

适用平台：Claude Code

---

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Claude Code 平台固定值：`$HOME/.claude/skills/sync-website`

## ③ 调度入口

用户已授权定时追更且当前会话确实提供 `/loop` 时，可用它重复调用共享正文的单次 `run`。缺少该能力时只手动运行；不得声称已启用自动调度。首次调度前须完成共享正文的初始化，避免无人值守运行途中向用户提问。

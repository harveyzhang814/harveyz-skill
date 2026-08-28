# sync-ytchannel — Claude Code 补丁

适用平台：Claude Code

---

## ① Subagent 派发

**本 skill 不派发 subagent。** 全部步骤为 `python3 scripts/*.py` 直接调用
（视频标题不翻译）。本小节存在只为与其他 skill 的补丁结构对齐。

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Claude Code 平台固定值：`$HOME/.claude/skills/sync-ytchannel`

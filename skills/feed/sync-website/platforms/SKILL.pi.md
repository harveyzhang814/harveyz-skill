# sync-website — Pi 补丁

适用平台：Pi

---

## ① Subagent 派发

**本 skill 不派发 subagent。** 全部步骤为 `python3 scripts/*.py` 直接调用，
外加 calibrate 流程里几步需要模型直接读 HTML/JSON 并作判断。本小节存在
只为与其他 skill 的补丁结构对齐。

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Pi 平台固定值：`$HOME/.pi/agent/skills/sync-website`

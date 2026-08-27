# sync-xtimeline — Hermes 补丁

适用平台：Hermes

> **⚠️ 未在本平台实测。** 本 skill 全程只调用 `python3 scripts/*.py` 与
> `browser-fetch` CLI，理论上平台无关，但从未在本平台实际运行过。首次运行
> 若出现异常，请回报以便补充本补丁。

---

## ① Subagent 派发

**本 skill 不派发 subagent。** 全部步骤为 `python3 scripts/*.py` 直接调用，
推文翻译在主对话内完成（纯文本翻译不需要隔离）。本小节存在只为与其他
skill 的补丁结构对齐。

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Hermes 安装本 skill 的目录（即包含 `scripts/` 的那一级）。

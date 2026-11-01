# sync-website — Hermes 补丁

适用平台：Hermes

> **⚠️ 未在本平台实测。** 本 skill 全程只调用 `python3 scripts/*.py` 与
> `browser-fetch`/`roster` CLI，理论上平台无关，但从未在本平台实际运行过。
> 首次运行若出现异常，请回报以便补充本补丁。

---

## ② 变量来源

名册与游标由 `roster` tool 持有，脚本自行定位，无需 Agent 传参。默认
Chrome profile 由 browser-fetch 侧持久化，与 clip-url 共用同一份配置。

`SKILL_DIR` 为 Hermes 安装本 skill 的目录（即包含 `scripts/` 的那一级）。

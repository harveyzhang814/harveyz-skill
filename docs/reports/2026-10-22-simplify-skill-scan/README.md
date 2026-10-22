# simplify-skill 全量扫描汇总（2026-10-22）

按 `skills/mint/simplify-skill` v0.1.2「拟定建议」7 条，对 `skills-index.json` 登记的 10 个 bundle、58 个 skill 做只读扫描（基线 `staging` @ 9af95ab，`skills/archived/` 除外）。只到拟定建议，未执行审批与修改。

主线：最该先处理的不是篇幅，而是 skill 改名或搬目录后没有跟着改的跨 skill 接口（路径、命令名、字段名）。这类问题先修，再按 bundle 逐个精简。

## 分报告

| 文件 | 范围 |
|---|---|
| [mint.md](mint.md) | mint（10） |
| [feed-creative.md](feed-creative.md) | feed（5）+ creative（2） |

其余 7 个 bundle（agent-canvas、superpowers-rewrite、research、coding、devops、writing、design）已精简并合入 staging，分报告已移除。

## 精简范围外的问题（建议先修）

把握度：「已核对」= 汇总时在源码中复核过；「读到」= 扫描时读原文得出，汇总时未复核；「推断」= 未运行验证。

| skill | 问题 | 把握度 |
|---|---|---|
| capture-todo / capture-insight | `\|\| echo "main"` 回退不生效，无 `origin/HEAD` 时分支名为空 | 推断 |
| archive-skill / contribute-skill | 合并流程与 CLAUDE.md 现行规定冲突 | 读到 |

## 精简收益分档

- **高**：sync-website、publish-skill、init-skill、capture-insight。
- **中**：各减 10%–25%，见分报告。
- **低/无**：simplify-skill 等，见分报告。

## 待决定

1. init-skill 与 publish-skill 规则冲突：缺 installScope 是失败还是警告；单段动词名（如 `handoff`）是否允许。

## 修改时的约束

`init-skill`、`publish-skill`、`runby-opencode` 的版本号或原句被 `tests/` 锁定；改正文需同步升版本、更新 `skills-index.json` 的 hash 并改测试。必须保留的字符串见各分报告。

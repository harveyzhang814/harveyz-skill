# simplify-skill 全量扫描汇总（2026-10-22）

按 `skills/mint/simplify-skill` v0.1.2「拟定建议」7 条，对 `skills-index.json` 登记的 10 个 bundle、58 个 skill 做只读扫描（基线 `staging` @ 9af95ab，`skills/archived/` 除外）。只到拟定建议，未执行审批与修改。

主线：最该先处理的不是篇幅，而是 skill 改名或搬目录后没有跟着改的跨 skill 接口（路径、命令名、字段名）。这类问题先修，再按 bundle 逐个精简。

## 分报告

| 文件 | 范围 |
|---|---|
| [mint.md](mint.md) | mint（10） |
| [research.md](research.md) | research（10） |
| [coding.md](coding.md) | coding（11） |
| [feed-creative.md](feed-creative.md) | feed（5）+ creative（2） |
| [writing-design.md](writing-design.md) | writing（4）+ design（3） |
| [devops.md](devops.md) | devops（4，目录 `skills/meta/`） |

## 精简范围外的问题（建议先修）

把握度：「已核对」= 汇总时在源码中复核过；「读到」= 扫描时读原文得出，汇总时未复核；「推断」= 未运行验证。

| skill | 问题 | 把握度 |
|---|---|---|
| build-style | 7 处引用 `skills/writing/build-style/...`，文件实际在 `skills/design/` | 已核对 |
| dedup-skill | `SKILL.md:102` 调用 `dir-manage`，实际名为 `manage-dir` | 已核对 |
| init-project → init-workflow | 骨架 `AGENTS.md` 指向 `docs/git-workflow.md`，init-workflow 产出 `docs/reference/git-workflow.md` | 已核对 |
| init-workflow | references 下 6 个文件仍用旧名 `git-workflow-init` | 已核对 |
| sync-agent | 写回 `config.json` 的 device 键应为 `id`（CLI 读 `device["id"]`），照抄 API 的 `deviceID` 会出错 | 代码已核对，后果推断 |
| draw-diagram | `color-templates.md` 旧色板规则与 SKILL.md 冲突 | 读到 |
| handoff | verify 标「可选」，但进工作区与 `status → 执行中` 只写在 verify 里 | 读到 |
| survey-skillrepo | 写 `~/.hskill/config.json` 未限定只改 `skillDir`，可能覆盖共用的 `knowledgeRoot` | 推断 |
| capture-todo / capture-insight | `\|\| echo "main"` 回退不生效，无 `origin/HEAD` 时分支名为空 | 推断 |
| archive-skill / contribute-skill | 合并流程与 CLAUDE.md 现行规定冲突 | 读到 |

## 精简收益分档

- **高**：init-spec（约 1,490 行未被引用的 `visual-companion.md` 与 `scripts/`，已核对 SKILL.md 无引用）、extract-cognition、sync-design、sync-website、release-project、publish-skill、init-skill、setup-debug、handoff、build-style、draw-diagram、sync-agent、capture-insight。
- **中**：约 20 个，各减 10%–25%，见分报告。
- **低/无**：simplify-skill、fork-topic、rephrase、explain-design、capture-vocab、judge-release 等。

## 待决定

1. init-skill 与 publish-skill 规则冲突：缺 installScope 是失败还是警告；单段动词名（如 `handoff`）是否允许。
2. init-spec 的未引用文件：删除，还是接回流程。
3. draw-diagram 与 build-style 的深色阈值统一为哪一套。
4. release-project 打 tag 用 `-m`（必为 annotated）与「需要时加 -a」的说明不一致，改哪边。

## 修改时的约束

`question-me`、`rephrase`、`init-project`、`init-skill`、`publish-skill`、`runby-opencode`、`learn-video` 的版本号或原句被 `tests/` 锁定；改正文需同步升版本、更新 `skills-index.json` 的 hash 并改测试。必须保留的字符串见各分报告。

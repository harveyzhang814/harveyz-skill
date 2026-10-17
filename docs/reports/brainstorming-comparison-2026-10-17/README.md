# Brainstorming 新旧版同场景对照测试

日期：2026-10-17。两名隔离的子 Agent 使用相同的模型配置、代码工作树和[初始请求](scenario.md)，分别遵循 [brainstorming-zh 0.1.37](inputs/rewrite/SKILL.md) 与 [Superpowers Brainstorming 7.0.0](inputs/original/SKILL.md)。原版固定在上游提交 [`bb92a77`](https://github.com/obra/superpowers/blob/bb92a77/skills/brainstorming/SKILL.md)，其构建者检查提示也已保存。新版 Agent 运行时直接读取本工作树的 `skills/superpowers-rewrite/brainstorming-zh/SKILL.md`，本目录副本仅供复核。

| 输入 | SHA-256 |
|---|---|
| 新版 SKILL.md | `8746509759a8ffb967ffd2628a9d517985a3b46ce37c67d1cc7be8d5f73be361` |
| 原版 SKILL.md | `6ee10d1481b8a2580d5336ff66c5c08acc9d4b251b13bbc3bfd31be99c261d43` |

测试者扮演用户：两边获得相同的业务事实与边界选择，但问题顺序随各自 Skill 自然展开；所有需求和设计批准都由测试者显式给出。两名 Agent 可只读调查代码，只能在各自 `runs/` 目录写设计产物；均未写产品代码、制定计划、提交、合并或部署。对话摘要分别见[新版](runs/rewrite/conversation.md)与[原版](runs/original/conversation.md)。

**产物中的“用户批准”均为测试者的模拟审批，不代表真实用户授权开发；两份设计只作为本次评估证据。**

## 方案对比

| 维度 | 新版 0.1.37 | 原版 7.0.0 |
|---|---|---|
| 需求与代码现状 | 澄清单 bundle、JSON 字段、错误和空 bundle；查 `bin/cli.js`、索引、测试及过时的 CLI 指南示例 | 从实际查找场景入手，澄清相同边界；查 `bin/cli.js`、索引和测试 |
| 关键方案选择 | 文本输出和实现位置各展示两种可行方案及取舍，用户分别选择；决定记录追溯来源和批准 | 提出一种集中在 `list` 分支的建议，文档标明尚未由用户选择；最终用户批准整份设计 |
| 可实施性 | [Spec](runs/rewrite/spec.md)写明有效 ID、空结果、错误输出、帮助更新及五组验收；按简单任务自行做构建者检查 | [设计文档](runs/original/hskill-list-bundle-design.md)覆盖相同核心行为、实现建议与验收；独立构建者检查返回“nothing important left” |
| 审查中发现的问题 | 首版[决定记录](runs/rewrite/record.md)把两个用户选择标成 Agent 推断，漏写 D-014 批准依据，并误提不存在的 `bundle list`；写前人工复核发现后已修正 | 对话中的用户批准没有回写设计文档；测试结束时文件仍标“待用户审查” |
| 最终状态 | Spec 0.1 与决定记录均标已批准，覆盖范围和未决事项一致 | Agent 回复已获批准，但设计文档状态仍是待审 |

两份方案都足以作为开发起点。**就本次用户强调的决定来源、关键方案人工选择和批准状态一致性而言，新版表现更好**；原版用更少文档完成了核心设计，但批准状态留在对话中，文件使用者可能误以为仍待审。新版的写前复核也确实拦下了来源标签、批准依据和代码事实错误，说明该闸门有实际价值。

技术方案最终高度接近：都建议在 CLI 的 `list` 分支按 `bundleMeta` 验证 ID、按 `skills[].bundle` 筛技能，筛选时让 `tools` 为空，并保持无筛选行为。新版把大小写、`all`、工具 bundle、空 bundle 和无筛选回归逐项写进验收，还指出现有 CLI 指南的过时示例；原版也覆盖重复参数、逗号输入、参数顺序和合成空 bundle 测试。差异主要在方案如何获得批准、决定能否追溯，以及批准后文档状态是否可靠。

## 成本与边界

- 新版产生 13 项当前决定和 1 项失效决定，决定记录约 7.9 KB、Spec 约 6.9 KB；原版单份设计约 5.1 KB。对这个单命令的小需求，新版追溯能力伴随明显的对话与文档成本。
- 原版多了一次可视化邀约，用户拒绝；新版多了两轮关键方案选择及写前记录复核。两边的提问不同，测试者补充相同事实，不能把轮数差异完全归因于 Skill 文本。
- 这是一个定义清晰的 CLI 场景、一次运行、模拟用户审批；没有实现或执行设计中的验收测试，也没有测试探索性需求。结果只支持本场景的流程与文档质量判断。

本报告对照 `bin/cli.js`、`skills-index.json` 和 `docs/reference/agent-cli-guide.md` 核查了现状；发现 CLI 指南中 `list --json` 示例已与实际输出不符、指南提到的 `bundle list` 在当前 CLI 中并不存在。报告保留两版输入、对话摘要和最终产物，未改动技能源码。

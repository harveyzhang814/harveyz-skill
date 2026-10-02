# B 类 Skill 平台适配最小修复设计

## 目标与范围

按独立 `doc/skill-platform-adaptation-standard` 分支的 `docs/reference/skill-platform-adaptation.md` 所定义的共享流程与宿主适配边界，修复第二轮评估中 B 类的七个已发布 skill：`sync-xtimeline`、`sync-ytchannel`、`sync-website`、`question-me`、`rephrase`、`init-project`、`runby-opencode`。目标是移除共享入口对 Claude 命令、身份和固定安装路径的误导，同时保持现有任务语义、授权边界及数据处理顺序。

本批不实现 A2 的三个执行断点，不处理 `build-style`、`scout-brand` 的独立错路径，不新增七平台完整适配器或宣称端到端兼容，也不改变安装器、调度器或 opencode 配置。

## 修复规则

1. 三个 feed skill：共享 `description` 与 `run` 标题只描述“一次运行”及“当前宿主提供且用户已授权时可调度”。已有 `platforms/` 中的宿主命令继续放在各自适配文件；不把 `/loop` 写成所有宿主通用入口。保留无人值守运行的预先配置要求、摘要落盘与游标提交顺序、失败时不虚报成功等语义。
2. `question-me`：保留手动调用与“发现复杂/含糊任务时先提议、等用户确认”的区别；将执行者称为当前 agent，不保证任一宿主会自动触发。
3. `rephrase`：可靠性判断由当前 agent 按原有“猜错代价”规则作出；保留仅手动调用、可靠时直接执行、不可靠时等待确认。
4. `init-project`：`references/template-schema.md` 用当前 skill 实际目录表述模板位置，骨架文件示例与当前 `AGENTS.md` 对齐；一并修正 `assets/skeleton/README.md` 中指向已不存在 `CLAUDE.md` 的链接。不改变模板 schema 或已存在文件的处理规则。
5. `runby-opencode`：`verify` 优先使用用户显式提供的 skill 源目录，其次是仓库源或经确认的目标安装目录；opencode 如何发现 skill 应先检查实际配置，不静默改用户配置。Claude 挂载路径仅作为明确标注的可选示例。`compare` 保留“Claude 与 opencode 对比”的有意限定；缺任一可用端时明确报告，不能把单端验证称为比较结果。

## 版本与验证

所有内容变化对应递增 `SKILL.md` 版本，并更新 `skills-index.json` 的 `contentVersion` 与 `contentHash`。对七项添加或更新定向静态测试：确认共享入口中不再有专有命令作为通用前提、路径引用有效、版本与索引一致；对 feed 调度与单次运行、`runby-opencode` 模式边界做文本契约检查。按仓库规范运行 `npm test`，如已知 Claude hook E2E 基线仍红，记录精确失败并分别运行与本批相关的测试，不称全套通过。真实宿主执行不在本批验收范围，明确列为未验证。

## 风险控制

文案修复可能无意改变触发条件或授权边界，因此逐项对照修改前后指令；若发现必须新增运行时能力或安装行为才能成立，停止该项的文案修复并单列后续问题，不以未经验证的适配承诺掩盖缺口。完成后留在独立 `fix/b-skill-portability` 分支；仅在用户明确要求时合并 `staging`。

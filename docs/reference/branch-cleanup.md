# Branch Cleanup Rules

## Always Delete（已合并后直接删除）
- `chore/bump-*` — 版本号 bump，每次发布新建，无需保留
- `chore/sync-*` — lockfile/版本同步，一次性任务
- `chore/fix-*` — 一次性 chore 修复
- `doc/*` — 文档更新，完成即归档

## Always Keep（无论是否合并都保留）
- `test/*` — 测试基础设施，持续迭代

## LLM 判断上下文
这是一个 Claude Code skills 个人仓库（harveyz-skill）。

保留标准：
- Skill 仍在开发或预期持续迭代的功能分支
- Eval/测试框架类分支（test/、harness 相关）
- 基础设施类（CLI 核心、安装器等有扩展空间的）

删除标准：
- 一次性任务：版本 bump、lockfile 修复、frontmatter 补全
- 已完成的独立功能（合并后明确不再继续）
- 文档类更新（已合并）
- 重构任务（已完成）

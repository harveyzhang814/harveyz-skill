# 对照测试场景

## 相同的初始用户请求

我们用这个仓库的 hskill CLI 管理技能。`hskill list` 输出太多，我想按 bundle 查看技能，比如 `hskill list --bundle research`；`--json` 也应支持筛选。无筛选时的行为不要变。请先把需求和实现方案整理成开发可用的设计，不写产品代码。

## 相同的测试约束

- 两名 Agent 使用同一代码工作树调查现状，分别遵循指定的新版或原版 Brainstorming。
- 测试者扮演用户回答问题与审批；未给出的答复和批准不得假定。
- 两名 Agent 的设计产物分别保存在 `runs/rewrite/` 和 `runs/original/`，不得修改产品代码、提交、合并或部署。
- 完成设计及其审查后停止，不进入 writing-plans。

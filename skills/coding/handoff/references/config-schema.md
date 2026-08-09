# `.hskill/handoff/config.md` schema

项目有特殊交接约定时才建此文件；无则 skill 用通用默认。author 首跑做初始化探测。

## 字段

- **输出路径** `output_dir`：交接文档落哪，默认 `docs/commute/`。
- **工作流样板** `workflow`：注入交接文档「工作流约定」章节的项目规范（分支/worktree/hooks/用哪些 skill）。
- **验证工具** `verification`：注入「验证步骤」章节的项目验证约定（跑什么测、要不要真产物 E2E）；若最小验收锚点已是自解释的硬判据，可不单独起验证步骤章节。
- **权威依据指向** `authority`：起草「背景与现状」「相关文档索引」等章节时自动挂链的**可移植权威**位置（spec 目录、架构文档）。不含 memory——交接文档不引 memory（可能陈旧、接手方访问不到）。

## 示例（占位，按本项目实际填写）

```yaml
output_dir: <交接文档目录，如 docs/commute/>
workflow: |
  <本项目分支/worktree/hooks 规范；git 工作流文档路径；建议配合的 skill>
verification: |
  <本项目单测命令；UI/端到端变更要用的验证工具与要求>
authority:
  specs: <设计规格目录，如 docs/superpowers/specs/>
  architecture: <架构北极星文档路径>
```

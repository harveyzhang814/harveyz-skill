## 指令源与能力检测

<!-- @if agent_canvas -->
- `rephrase`、`question-me`、`handoff`、画布 skill 与
<!-- @else -->
- `rephrase`、`question-me`、`handoff` 与
<!-- @endif -->
  `superpowers:*` 等是跨平台部署的共享 skill，不属于 Claude Code、Codex 或其他宿主的专属
  指令。各平台只负责用自己的入口调用它们；skill 名称、语义和职责边界保持一致。
- 只有当前会话实际暴露的工具和应用能力才算可用。共享 skill 若意外缺失，应报告部署或配置
  问题，不得虚构调用结果，也不要自行复制其内部流程作为长期替代。
- 平台的个人配置或项目专属设置文件不能替代本文件中的仓库规则。
- 本项目禁止使用通用的 `finishing-a-development-branch` 和 `using-git-worktrees` 流程；分支、
  worktree 与合并必须按本文及项目的分支规则执行。即使某个平台已安装这些
  skill，也不得让它们覆盖仓库流程。worktree 的建立、复用、进出与检测一律调用共享 skill
  `manage-worktree`，不手写 `git worktree add`；它不可用时停下报告，不自行兜底建 worktree。
- 搜索文本或文件优先使用 `rg` / `rg --files`。

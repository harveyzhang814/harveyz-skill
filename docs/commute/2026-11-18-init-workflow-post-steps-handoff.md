---
status: 执行中
date: 2026-11-18
author_model: claude-opus-5-5
acceptance: hard
workspace_mode: shared-worktree
branch: feature/init-workflow-post-steps
worktree: /Users/harveyzhang96/Projects/harveyz-skill/.worktrees/feature+init-workflow-post-steps
base_commit: fd60ab4e389ded0430d39be83c7de17aa9ec8c15
source_node: e5fda1ce-857b-4f9e-97b3-c407d3e61768
target_node: 9afed50d-7b62-4ba0-80ff-d128083a4bf7
---

# 交接：init-workflow 5.1.0，新增 `merge.post_steps`（合并后步骤）

**交接目的**：接手方在 harveyz-skill 仓库里，用 TDD 给 init-workflow 增加一个"合并成功后，在后台执行配置好的命令"的扩展点，版本升到 5.1.0。完成后交回交出方验收和合并。

---

## 背景

agent-canvas 仓库正在改造测试运行方式：合并进 `staging` 之后，要在后台自动跑一轮全量测试，跑完立即返回，不阻塞合并。合并脚本 `scripts/merge-to-staging.sh` 由 init-workflow 生成，目前只有 `merge.pre_checks`（合并前检查）这一个扩展点，所以需要在 init-workflow 里新增一个合并后的对称扩展点。

agent-canvas 那边怎么使用这个扩展点（后台运行器、通知等），**不在本次范围内**。

## 相关文档索引（权威依据）

本任务的 spec 和计划都在 **agent-canvas 仓库**里。请按提交号读取，不要去那个仓库的工作区里找：

- spec §5.2（接口约定）和判据 J5：
  `git -C /Users/harveyzhang96/Projects/agent-canvas show e058b324:docs/superpowers/specs/2026-11-18-test-run-strategy-design.md`
- 计划 Task 0：
  `git -C /Users/harveyzhang96/Projects/agent-canvas show e058b324:docs/superpowers/plans/2026-11-18-test-run-strategy.md`

如有冲突，以这两份为准。下面「接口约定」一节是从中摘出的开工必需内容。

**执行技能**：`superpowers:test-driven-development`。计划里 Task 0 只有一个任务，用不上按任务派 subagent 的执行方式。

## 接口约定（不可修改）

- **配置项**：`workflow-config.yml` 新增 `merge.post_steps: string[]`，默认值 `[]`。要在 `references/workflow-config.yml` 的注释里说明，写法参照 `pre_checks`。
- **默认关闭**：`post_steps` 为空或者没有这个键时，生成的合并脚本与改动前的行为完全一致。不能影响其他使用 init-workflow 的项目。
- **占位符**：沿用 `{script_dir}`、`{target}`，再新增三个：
  - `{merge_commit}`：新的合并提交；
  - `{base_commit}`：合并前 target 指向的提交；
  - `{feature_branch}`：被合并的分支名。
- **环境变量**：每一项命令执行时，都导出 `MERGE_COMMIT`、`MERGE_BASE_COMMIT`、`MERGE_FEATURE_BRANCH`、`MERGE_TARGET`。
- **执行时机**：`git update-ref` 成功，并且 `sync_staging_worktree` 返回之后才执行。"已经包含在 target 里、无需合并"、冲突、重试耗尽这几条退出路径**都不执行**。
- **执行方式**：
  - 每一项都在本次合并的 worktree 根目录下，用 `nohup sh -c '<命令>' >/dev/null 2>&1 &` 脱离启动，不等它结束；
  - 启动本身失败时，只往 stderr 打一行警告；
  - 合并脚本的**退出码和原有 stdout 输出都不变**。
- **版本**：`SKILL.md` 的 `version` 改为 `"5.1.0"`；同步更新 `skills-index.json` 里这个 skill 的 `contentHash` 和 `contentVersion`，规则见 `AGENTS.md`；在 CHANGELOG 里记一笔，写法按本仓库的惯例。

## 范围铁律

- **做**：`skills/coding/init-workflow/` 下的模板（`references/merge-script-template.sh`）、配置参考（`references/workflow-config.yml`）、渲染与解析脚本（`references/workflow_resolve.py`、`references/render_docs.py`，按实际需要改）、`SKILL.md`、该 skill 的 `tests/`，以及 `skills-index.json` 和 CHANGELOG。
- **不做**：
  - 把 skill 部署到 `~/.claude/skills` 或其他宿主目录。部署由交出方在合并后从 `staging` 提取；
  - 改 agent-canvas 仓库的任何文件；
  - 合并到 `staging`；
  - `git worktree remove`；
  - 修改上面「接口约定」里的任何一项。约定与代码现状冲突、或者无法照做时，停下来打回交出方。

## 工作流约定

按 `.hskill/handoff/config.md` 的 `workflow` 段执行，要点如下：
- 用 `manage-worktree` 的「进入」进入 frontmatter 里的 `worktree`，核对 `branch`；确认 `core.hooksPath` 为 `.githooks`、`merge.ff` 为 `false`。
- 提交信息遵循 Conventional Commits，类型写 `docs` 而不是 `doc`，首行不超过 80 个字符，末尾带 `Co-Authored-By` trailer。
- 写新测试之前，先读 `docs/reference/testing-guide.md`。

## 最小验收锚点

以下全部满足才算达成，验收方会逐条重跑：

1. **J5 的三条 bats 用例都在这个 skill 的测试里，并且全部通过**。测试名分别以 `J5a`、`J5b`、`J5c` 开头：
   - `J5a post_steps 为空时生成的合并脚本与改动前一致`：用同一份不含 `post_steps` 的配置，分别以 `fd60ab4` 版本和新版本的模板生成脚本，两者的差异**只在版本号所在的行**；
   - `J5b 后台步骤 sleep 30 后 touch 标记，合并 2 秒内返回且退出码为 0，约 30 秒后标记出现`：标记出现的等待上限可以放宽到 40 秒；
   - `J5c 后台步骤执行失败不改变合并的退出码`：退出码为 0，stdout 与无步骤时一致。
2. 另外加一条 `J5d 占位符与环境变量都按约定传入后台步骤`：步骤把 `{merge_commit}`、`{base_commit}`、`{feature_branch}`、`{target}` 和四个 `MERGE_*` 环境变量写进一个文件，断言取值都正确。还要验证"无需合并"那条路径不会执行步骤。
3. `npm test` 退出码为 0。
4. 这个 skill 自带的既有测试（`skills/coding/init-workflow/tests/` 下的 bats 与 pytest）全部通过，自测记录里写明实际执行的命令。
5. `grep '^version:' skills/coding/init-workflow/SKILL.md` 输出 `version: "5.1.0"`；`skills-index.json` 里这个 skill 的 `contentHash` 和 `contentVersion` 已更新。
6. `git diff --check fd60ab4..HEAD` 没有输出；`git status --short` 为空。

**自测要求**：自测记录逐条列出上面 1–6 条的结果并附命令。按 handoff skill 的 Phase 2.5 执行。完成后用 `agent-canvas-ctl send e5fda1ce-857b-4f9e-97b3-c407d3e61768` 回报。

---
name: close-node
description: Wrap up the current canvas node when a round of work is done — advance requirement status, verify handoff closure, merge the branch, stop the process, and hide the node from the canvas; only usable inside an Agent Canvas node.
disable-model-invocation: true
user_invocable: true
version: "1.0.3"
---

# 节点收尾（close-node）

如果当前不在 Agent Canvas 的画布节点里（即环境变量 `AGENT_CANVAS_MCP_URL` 未设置，
或 `agent-canvas-ctl` 命令不存在），这个 skill 不适用，直接跳过，不要尝试执行下面的命令。

**人工触发**，不自动触发。Codex 通过 `agents/openai.yaml` 禁止隐式调用；用户必须以 `$close-node` 显式调用。触发时机：你这一轮工作已经做完、已经汇报过、确认不再有后续动作。

## 步骤

### 1. 认清自己

```
agent-canvas-ctl whoami                       → 自己的 nodeId
agent-canvas-ctl node-relations <自己的 nodeId>  → implements 边 / hands-off-to 边
```

### 2. 判角色

在 `docs/commute/` 下找 frontmatter 的 `source_node` 或 `target_node` 等于自己 nodeId
的交接文档：

| 角色 | 判据 |
|---|---|
| **独立节点** | 没有 `hands-off-to` 边，也没有一份交接文档点名自己 |
| **交出方** | 自己的 nodeId == 某份交接文档的 `source_node` |
| **接手方** | 自己的 nodeId == 某份交接文档的 `target_node` |

"验收方"不是第四类——`/handoff` 的 accept 阶段由原 session 做，验收方就是交出方本人。

### 3. 推进需求状态

沿 `implements` 边找到需求节点。判断它现在该是什么状态，然后：

```
agent-canvas-ctl update-node-requirement <需求节点id> --status <verifying|done>
```

- 活干完了、还没人验 → `verifying`
- 已经验收通过 → `done`
- 这条需求要搁置（`deferred` 与 `status` 正交，不是它的取值）→ `--deferred true`
- **拿不准就别改**，如实报告"需求状态维持 X，因为 Y"。改错了比不改更难发现。

没有 `implements` 边 → 跳过这一步，不要顺手立项一个需求。

### 4. handoff 收口

**独立节点**：跳过，直接进第 5 步。

**接手方**：
- 核对交接文档 frontmatter 的 `status` 是否已置 `待验收`，没置就置上。
- 核对 `hands-off-to` 边两端是否都齐、`target_node` 是否已回填自己的 nodeId。
- **不合并、不 `git worktree remove`。** 要离开用 `ExitWorktree(action: "keep")`。

**交出方**：
- 核对交接文档 `status` 是否已到 `已验收`。
- **没到 `已验收` 就停在这里报告，不要继续往下走。** 收尾不等于验收通过。
- 到了 `已验收` 之后，再核对本分支是否已经合并进 staging
  （`git merge-base --is-ancestor HEAD staging` 成功即已合并）。
  **未合并就停在这里报告，不要进第 7 步。** 合并是 `/handoff` accept 阶段由你自己跑
  `scripts/merge-to-staging.sh` 的动作，本 skill 不代跑；把没合并的分支连同节点一起
  关掉，等于把工作弄丢了。

> **只有交出方能合并、能 `git worktree remove`。** 这是硬约束，不是建议。

### 5. 合并或确认已合并（仅独立节点）

合并是待确认的状态转换，不是必经动作。先进入仓库根目录，确认当前分支与本地 `staging`
都可识别：

```
repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"
current_branch="$(git branch --show-current)"
git show-ref --verify --quiet refs/heads/staging
```

- 本地没有 `staging`、`current_branch` 为空（detached HEAD），或当前是 `main`：**停下报告，
  不执行 merge、不清理 worktree、不要进第 7 步。** 这些状态都不能推断为"已经合并"。
- 当前是 `staging`：已经在目标分支。**跳过 merge，也跳过 worktree 清理**，直接进第 6 步。
  不要运行 `scripts/merge-to-staging.sh`，它会拒绝这个分支。
- 其他分支先检查是否已进入 `staging`：

  ```
  git merge-base --is-ancestor HEAD staging
  ```

  成功表示该分支提交已合并，跳过 merge；失败才进入下一条的合并路径。
- 尚未合并时，先确认 `scripts/merge-to-staging.sh` 存在、且当前仓库确实采用本 skill 描述的
  流程。不存在就**停下报告，不要自行换用别的合并手法**；存在才运行：

  ```
  scripts/merge-to-staging.sh
  ```

  **合并失败就停在这里报告，不要进第 7 步。** 把没合并的分支连同节点一起关掉，等于把工作
  弄丢了。

已确认合并，或脚本合并成功后，才可以考虑清理当前工作区。先确认它真的是 linked
worktree：

```
git_dir="$(cd "$(git rev-parse --git-dir)" && pwd -P)"
git_common_dir="$(cd "$(git rev-parse --git-common-dir)" && pwd -P)"
```

- 只有 `git_dir` 与 `git_common_dir` 不同，才运行 `git worktree remove "$repo_root"`。
- 两者相同代表主工作树：跳过清理并在第 6 步说明原因，**不要删除它**。
- 若 `git worktree remove` 提示有未提交改动，**停下报告，不要加 `--force`**。

### 6. 汇报

把上面每一步做了什么、跳过了什么、为什么，一次说完。

> **第 7 步一执行就没有输出了。所有要给人看的东西必须在这里说完。**

### 7. 关闭自己

先自查：有没有 subagent 还在后台跑？有就等它们完成，不要现在关。

```
agent-canvas-arrange hide <自己的 nodeId>
agent-canvas-ctl stop-node <自己的 nodeId>
```

**顺序不能反。** `stop-node` 一执行进程就没了，排在它后面的命令发不出去。

这一步之后没有任何输出是**预期行为**，不是故障。

## 边界

- **不代跑 `describe-node`、`relate-node`。** 那两个的第二次调用仍按 CLAUDE.md 由你自己
  在收尾前调，本 skill 与它们**并列**，不是它们的编排器。调本 skill 之前先把它们调完。
- **不调 `capture-requirement`。** 需求立项只在闸门 2 发生一次，收尾不重复立项。
- 不动 `implements` 边——只改需求节点自己的 `status`/`deferred`。
- `stop-node` 不走 UI 那套阻断策略（busy / 有活跃 subagent / 绑着 worktree）。
  那三条是防人手滑的护栏，你显式调用是有意图的动作。**代价是这个工具很锋利**——
  第 7 步的自查是唯一的缓解，机制不会替你挡。

---
name: manage-worktree
description: "Prepare, enter, inspect, or leave the git worktree a task works in — reuse the task's existing worktree or create one from an explicit, rule-derived base after one user confirmation, bind the session to it on Claude Code, Codex, or any other host, and check it is a linked worktree on a named non-integration branch. Called by init-spec, develop-plan, and handoff; never merges, removes worktrees, or deletes branches. Triggers: 'prepare a worktree', 'enter this worktree', 'check my worktree'."
user_invocable: true
version: "0.1.5"
---

# 管理 worktree

## 作用（说明）

一个任务从建档、写计划到交接、验收，始终在同一个命名分支的 worktree 里进行。本技能是建立或复用、进出、检测 worktree 的唯一写法，init-spec、develop-plan、handoff 统一调用它，不各自另写。

**边界：** 不合并、不清理 worktree、不删除分支：绝不执行 `git worktree remove`、`git branch -d/-D`、`git merge` 或其他删除工作区、分支的命令；不迁移、不改写规则文件；检测不通过时只报告，不自行切换分支或修复。

## 触发条件

- 调用方：init-spec 建档前、develop-plan 开工前、handoff 的 author 阶段起草交接文档前调用「准备」；handoff 的 verify 与 accept 调用「进入」。
- 用户直接要求，例如“准备一个 worktree”“进入这个 worktree”“检查我的 worktree”。

调用方约定：本技能不可用时，调用方停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree，不自行兜底建 worktree。

## 动作

| 动作 | 输入 | 行为 | 结果 |
|---|---|---|---|
| 「准备」 | 任务 topic（用作分支名 slug）；可选的期望分支类型（默认 `feature`）；可选的锚点文件路径（本任务已产生的决定记录、Spec 或计划） | 找到或建出工作区，进入 | 工作区绝对路径、分支名、基线（新建时）、检测结果 |
| 「进入」 | 已有工作区的绝对路径；可选的期望分支名 | 检测后按宿主进入；分支与期望不符时报告，不切换 | 同上 |
| 「检测」 | 无（检测当前所在工作区） | 只读检测 | 检测结果 |
| 「离开」 | 无 | 按宿主离开，保留工作区 | — |

## 「检测」

各动作的判断都以检测脚本的一次输出为准。脚本只读，不建、不删、不改任何 worktree、分支或配置：

```bash
bash <skill 目录>/scripts/inspect-worktree.sh [--path <目录>] [--type <分支类型>] [--branch <分支名>]
```

`--path` 默认当前目录；`--type` 默认 `feature`，只影响 `base`；`--branch` 只用来算 `default_path`。stdout 每行一个 `key=value`：`root linked branch detached rule_file integration is_integration base default_path hooks reusable verdict`，每个未通过项另起一行 `reason=<代码>`。

| 检测项 | 未通过时的 `reason` |
|---|---|
| 目标目录是一个链接 worktree（`git worktree add` 建出的工作区，不含主工作树）的根目录 | `not-root`（不在根目录）、`not-linked`（是主工作树） |
| 处于命名分支，不是 detached HEAD | `detached` |
| 当前分支不是集成分支 | `integration-branch` |
| 仓库存在 `.githooks/` 目录时，`core.hooksPath` 指向它（无该目录时 `hooks=n/a`） | `hooks-missing` |

`reusable=yes` 表示除 hooks 外全部通过，可以直接复用为任务工作区。其余输出：

- `rule_file`：按 init-workflow 的查找顺序（`.hskill/init-workflow/workflow-config.yml` → 项目根 `workflow-config.yml` → `.claude/workflow-config.yml`）取到的第一个规则文件，只读不迁移；没有时为 `none`。
- `integration`、`base`：从规则文件的受保护分支及其 `merge_from` 推出；没有规则文件时都取仓库默认分支。
- `default_path`：`<主工作树根>/.worktrees/<分支名，/ 换成 +>`，即仓库相对路径 `.worktrees/<分支名，/ 换成 +>`，例如 `feature/foo` → `.worktrees/feature+foo`；从链接 worktree 里调用也落在主工作树下。

脚本不核对分支命名：分支名须匹配规则文件的 `branch_naming.allowed_patterns`，由你读规则文件核对。

| 退出码 | 含义 | 处理 |
|---|---|---|
| 0 | `verdict=pass` | 全部通过 |
| 1 | `verdict=fail` | 按 `reason` 逐项报告 |
| 2 | 用法错误 | 修正调用参数后重跑 |
| 3 | 目标路径不存在或不是 git 目录，`verdict=n/a` | 「准备」「检测」在当前目录遇到（非 git 目录）：返回“不适用”，不建、不进，调用方在当前目录继续；「进入」遇到：报告不通过 |

向调用方报告时，四个检测项逐项给出通过或不通过及原因。`merge.ff=false` 等项目特有设置不在检测范围内，由项目指令规定。

## 「准备」

先在当前目录检测一次，带上 `--type <分支类型> --branch <分支类型>/<slug>`（后者即期望分支）。退出码 3 → 返回“不适用”。否则先找已有，找不到再新建。

### 找已有（命中即止，不询问）

1. **锚点所在的工作区**：锚点按绝对路径解析（相对路径相对当前目录），取它所在的工作区根（`git -C <锚点所在目录> rev-parse --show-toplevel`）检测，`reusable=yes` 就复用；否则报告原因（文件不存在、在主工作树、detached 或在集成分支上），继续往下。换会话后回到建档时的工作区靠这一条。
2. **当前目录**：`reusable=yes` 就复用。
3. **已 checkout 期望分支的链接 worktree**：用 `git worktree list --porcelain` 查（第一项是主工作树，不算），有就复用。

### 新建（路径取 `default_path`）

- **期望分支已存在，且没有被任何工作区 checkout** → `git worktree add <路径> <分支>`，不建分支，不问基线。
- **其他情况**（含主工作树停在功能分支上、detached HEAD、集成分支、未给锚点的新会话）→ 新建前向用户一次确认基线、分支名和路径，确认后 `git worktree add <路径> -b <分支> <基线>`：
  - 基线：取 `base`；当前所在分支若是非集成的命名分支，列为可选的另一基线。不从当前 HEAD 静默拉分支——那会夹带其他会话未合并的提交。
  - 分支名：默认期望分支，须匹配命名模式。期望分支已存在但正被主工作树占用时，一个分支不能同时被两个工作区 checkout，确认时说明并请用户另取分支名。
- **`.gitignore`**：`git -C <主工作树根> check-ignore -q .worktrees/`（主工作树根即 `default_path` 中 `/.worktrees/` 之前的部分）失败（未被忽略）时，补写一行 `.worktrees/` 须经用户确认：有上面那次确认就并入，没有就单独问这一项；确认后在新工作区里补写并提交。

停止条件：

- 用户拒绝确认 → 不建；调用方停下，告诉用户可改选基线、分支名或路径后重来。
- 基线分支在本地不存在（`git show-ref --verify refs/heads/<基线>` 失败）或推断不出 → 不新建，报告原因，请用户指定基线。
- 目标路径已存在 → 不覆盖，报告并请用户另选路径。

### 收尾

复用当前目录时，开头那次检测就是结果。其他情况按「进入」进入找到或建好的工作区。返回工作区绝对路径、分支名、基线（仅新建时）和检测结果。

## 「进入」

1. 对目标路径检测一次：`--path <工作区绝对路径>`。退出码 3，或结果含 `not-root`、`not-linked` → 报告不通过，不进入，也不在当前目录继续；由调用方按自己的规则打回或重建，本技能不自行修复。
2. 按「按宿主进出」进入，核对后续命令的工作目录确实是该工作区。第 1 步的检测就是结果，进入后不重跑。
3. 给了期望分支名而 `branch` 与之不符 → 报告不通过，不切换分支。

## 按宿主进出

各动作说的「进入」「离开」按宿主执行下面对应小节；宿主不在其中、对应能力不可用或被拒绝，才按「通用兜底」办。**已知宿主不得因兜底也能完成命令就跳过原生进入/离开动作。** 进入是否完成的判据：**后续命令的工作目录就是那个工作区**。

### Claude Code

| 动作 | 手段 |
|---|---|
| 进入 | `EnterWorktree(path: "<工作区绝对路径>")` |
| 离开 | `ExitWorktree(action: "keep")` |

- 工具尚未出现在可用工具中时，先用 ToolSearch 找到 `EnterWorktree` / `ExitWorktree`，不要降级成 `cd`。
- **只用 `path` 模式，绝不用 `name`**：`name` 会自建分支（`worktree-<name 把 / 换成 +>`，常过不了分支命名规则），基线默认取 `origin/<默认分支>`。分支名和基线必须由本技能按规则定，所以只能先 `git worktree add` 建、再用 `path` 进。
- `path` 只认当前仓库（或嵌套在其中的仓库）登记过的工作区，跨仓库直接拒绝，此时按通用兜底办。
- **会话已经在某个 worktree 里时，只能直接切进 `.claude/worktrees/` 下的工作区**；目标在 `.worktrees/` 等其他位置会被拒，报 “Switching from this session is limited to worktrees managed by Claude Code”。此时先 `ExitWorktree(action: "keep")` 回到启动目录，再 `EnterWorktree(path:)`。从启动目录首次进入不受这条限制。
- 必须由当前会话直接调用，不能交给 fork 或 subagent 代调。
- 离开一律 `action: "keep"`，绝不 `remove`。

### Codex

Codex 没有 `EnterWorktree` / `ExitWorktree` 工具。进入已建好的工作区时，选择一种能让会话的 workspace 根就是该工作区的启动方式：

- CLI：从该目录启动，或用 `codex -C <工作区>` / `codex exec -C <工作区> ...`。
- Codex App：打开该持久 worktree 作为 workspace，再开始新的 chat。
- 宿主无法重新绑定 workspace：按「通用兜底」逐条使用绝对路径与显式工作目录。

不要用 `--worktree`：它会另建新的 managed worktree，不是进入已建的路径。App 的 Handoff 是同一 chat 在 Local 与 Worktree 之间移动，不能替代进入指定工作区。离开无需专门动作，工作区保留。

### 通用兜底（其他宿主、能力不可用或跨仓库）

每条命令自带限定，不要靠单独的 `cd`（多数宿主里它只在单条命令内有效）：

- git：`git -C <工作区> <命令>`
- 其他 shell 命令：`cd <工作区> && <命令>` 写在同一条命令里
- 读写、搜索文件一律用工作区内的绝对路径——相对路径按会话当前目录解析，会静默改到另一份同名文件。

离开时停止指向该工作区即可，工作区保留。

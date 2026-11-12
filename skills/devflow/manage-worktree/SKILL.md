---
name: manage-worktree
description: "Prepare, enter, inspect, merge, or leave the git worktree a task works in — reuse the task's existing worktree or create one from an explicit, rule-derived base after one user confirmation, bind the session to it on Claude Code, Codex, or any other host, check it is a linked worktree on a named non-integration branch, and merge it into the repo's merge target through the repo's own merge script. Called by init-spec, develop-plan, and handoff; never pushes, removes worktrees, or deletes branches. Triggers: 'prepare a worktree', 'enter this worktree', 'check my worktree', 'merge this worktree'."
user_invocable: true
version: "0.2.0"
---

# 管理 worktree

## 作用（说明）

一个任务从建档、写计划到交接、验收，始终在同一个命名分支的 worktree 里进行。本技能是建立或复用、进出、检测 worktree 的唯一写法，init-spec、develop-plan、handoff 统一调用它，不各自另写。

**边界：** 不清理 worktree、不删除分支：绝不执行 `git worktree remove`、`git branch -d/-D` 或其他删除工作区、分支的命令；不 push；不迁移、不改写规则文件与 `resolved.env`；检测不通过时只报告，不自行切换分支或修复。唯一的合并路径是「合并」调用仓库部署的合并脚本，不自己拼 `git merge`。

## 触发条件

- 调用方：init-spec 建档前、develop-plan 第 1 步、handoff 的 author 第 4 步调用「准备」；handoff 的 verify 与 accept 调用「进入」。
- 用户直接要求，例如“准备一个 worktree”“进入这个 worktree”“检查我的 worktree”“合并”。
- 「合并」只在用户明确说“合并”，或项目指令规定时由调用方触发（见「合并」一节）。

调用方约定：本技能不可用时，调用方停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree，不自行兜底建 worktree。

## 动作

| 动作 | 输入 | 行为 | 结果 |
|---|---|---|---|
| 「准备」 | 任务 topic（用作分支名 slug）；可选的期望分支类型（默认 `feature`）；可选的锚点文件路径（本任务已产生的决定记录、Spec 或计划） | 找到或建出工作区，进入 | 工作区绝对路径、分支名、基线（新建时）、检测结果 |
| 「进入」 | 已有工作区的绝对路径；可选的期望分支名 | 检测后按宿主进入；分支与期望不符时报告，不切换 | 同上 |
| 「检测」 | 无（检测当前所在工作区） | 只读检测 | 检测结果 |
| 「合并」 | 无（作用于当前所在工作区） | 调用 `scripts/merge-worktree.sh`，由仓库的合并脚本把当前分支并入合并目标 | 合并脚本的输出与退出码 |
| 「离开」 | 无 | 按宿主离开，保留工作区 | — |

## 规则来源

所有动作的取值（集成分支、基线、合并目标、worktree 目录）都来自 `.hskill/init-workflow/resolved.env`，以基线分支上已提交的那份为准，不读规则文件，也不 `source` 它（逐行读取）。`inspect-worktree.sh` 分两步取：

1. 引导：依次取当前工作区根、主工作树根下的 `resolved.env`，用第一份得到 `base.<类型>`（「准备」用期望分支类型，其余动作用 `feature`；该键缺失时改用 `base.feature`，再缺失用第一个集成分支，仅用于定位第 2 步）；两处都没有，也按未部署处理。
2. 权威：`git show <该基线分支>:.hskill/init-workflow/resolved.env`，以它的取值输出。这一份读不到（基线分支上没有此文件）→ 退出码 4。

因此主工作树停在别的会话的分支上，或目标工作区是部署前建的分支，都不影响取值。任何取值都不按默认分支猜：`resolved.env` 没有 `base.<类型>` 时 `base` 为空；没有集成分支（`integration_branches` 缺失或为空）时整份视为无效，退出码 4。退出码 4 时各动作停下，提示先在该仓库（重新）部署 init-workflow。

## 「检测」

各动作的判断都以检测脚本的一次输出为准。脚本只读，不建、不删、不改任何 worktree、分支或配置：

```bash
bash <skill 目录>/scripts/inspect-worktree.sh [--path <目录>] [--type <分支类型>] [--branch <分支名>]
```

`--path` 默认当前目录；`--type` 默认 `feature`，只影响 `base`；`--branch` 只用来算 `default_path`。stdout 每行一个 `key=value`：`root linked branch detached resolved integration is_integration base merge_target merge_script default_path hooks reusable verdict`，每个未通过项另起一行 `reason=<代码>`。

| 检测项 | 未通过时的 `reason` |
|---|---|
| 目标目录是一个链接 worktree（`git worktree add` 建出的工作区，不含主工作树）的根目录 | `not-root`（不在根目录）、`not-linked`（是主工作树） |
| 处于命名分支，不是 detached HEAD | `detached` |
| 当前分支不是集成分支 | `integration-branch` |
| 仓库存在 `.githooks/` 目录时，`core.hooksPath` 指向它（无该目录时 `hooks=n/a`） | `hooks-missing` |

`reusable=yes` 表示除 hooks 外全部通过，可以直接复用为任务工作区。其余输出：

- `resolved`：`resolved.env` 的仓库相对路径 `.hskill/init-workflow/resolved.env`；仓库未部署时为 `missing`。
- `integration`、`base`、`merge_target`、`merge_script`：取自 `resolved.env`（`integration_branches`、`base.<类型>`、`merge_target`、`merge_script`）；`resolved.env` 没有 `base.<类型>` 键时 `base` 为空（不退回默认分支）；没有 `merge_target` 键（本仓库未配置合并目标）时 `merge_target`、`merge_script` 为空。
- `default_path`：`<主工作树根>/<worktree_dir>/<分支名，/ 换成 +>`，`worktree_dir` 取自 `resolved.env`；默认 `worktree_dir=.worktrees` 时即仓库相对路径 `.worktrees/<分支名，/ 换成 +>`，例如 `feature/foo` → `.worktrees/feature+foo`；从链接 worktree 里调用也落在主工作树下。

脚本不核对分支命名：分支名须匹配 `resolved.env` 的 `naming.<n>`（`naming_exempt` 所列分支豁免），由你读 `resolved.env` 核对，不读规则文件。

| 退出码 | 含义 | 处理 |
|---|---|---|
| 0 | `verdict=pass` | 全部通过 |
| 1 | `verdict=fail` | 按 `reason` 逐项报告 |
| 2 | 用法错误 | 修正调用参数后重跑 |
| 3 | 目标路径不存在或不是 git 目录，`verdict=n/a` | 「准备」「检测」在当前目录遇到（非 git 目录）：返回“不适用”，不建、不进，调用方在当前目录继续；「进入」遇到：报告不通过 |
| 4 | `resolved.env` 不可用，只输出 `resolved`、`verdict=n/a`、`reason` 三行：仓库未部署（`resolved=missing`、`reason=workflow-not-deployed`），或文件无效——缺 `integration_branches` 或其值为空（`resolved=<相对路径>`、`reason=resolved-invalid`）；非 git 目录先于此判断 | 所有动作停下，提示该仓库需（重新）部署 init-workflow，按 `reason` 说明原因，不继续、不兜底 |

向调用方报告时，四个检测项逐项给出通过或不通过及原因。项目特有设置不在检测范围内，由项目指令规定。

## 「合并」

由 `scripts/merge-worktree.sh` 完成，你只调用、呈现结果：

```bash
bash <skill 目录>/scripts/merge-worktree.sh
```

无参数，作用于当前目录；在 Claude Code、Codex、其他宿主下都在当前工作区直接执行，不需要进出。

**时机：** 只在用户明确说“合并”，或项目指令规定了合并时机时，由调用方触发。其他动作（「准备」「进入」「检测」「离开」）绝不顺带合并。

**脚本内部依次做**（说明它做什么，不是要你逐步执行）：

1. 对当前目录跑 `inspect-worktree.sh`。
2. 读 `merge_target`、`merge_script`。
3. 检查 `<工作区根>/<merge_script>` 存在且可执行。
4. 在工作区根执行该脚本，输出与退出码原样透传。

**退出码：**

| 退出码 | 含义 | 处理 |
|---|---|---|
| 0 | 已合并，或已包含在合并目标里 | 报告结果 |
| 1 | 合并脚本出错（含 `merge.pre_checks` 未通过，脚本会打印失败的命令）；也可能是 `merge-worktree.sh` 自身的用法错误（带了参数）或检测脚本异常退出 | 报告输出，不合并 |
| 2 | 真实冲突，冲突标记已落在当前工作区 | 解决冲突并提交后重新「合并」 |
| 3 | 当前目录不是 git 目录 | 报告，不合并 |
| 4 | 仓库未部署 `resolved.env`，或它无效（`resolved-invalid`） | 停下，提示先（重新）部署 init-workflow |
| 5 | 检测未通过：当前目录不是链接 worktree 的根目录（含其子目录）、detached HEAD、或处于集成分支 | 按输出的 `reason` 报告，不合并 |
| 6 | `resolved.env` 没有合并目标 | 报告“本仓库未配置合并目标”，不合并 |
| 7 | 本工作区缺合并脚本（本分支早于部署） | 提示先把 `<merge_target>` 并入本分支再「合并」，不退回 `git merge` |

合并脚本返回 0、1、2 以外的退出码时，原样透传，不改写；按脚本输出报告。

不 push（合并只更新本地合并目标分支），不移除 worktree，不删除分支；合并后清理由用户另行决定。

## 「准备」

先在当前目录检测一次，带上 `--type <分支类型> --branch <分支类型>/<slug>`（后者即期望分支）。退出码 3 → 返回“不适用”。否则先找已有，找不到再新建。

### 找已有（命中即止，不询问）

1. **锚点所在的工作区**：锚点按绝对路径解析（相对路径相对当前目录），取它所在的工作区根（`git -C <锚点所在目录> rev-parse --show-toplevel`）检测，`reusable=yes` 就复用；否则报告原因（文件不存在、在主工作树、detached 或在集成分支上），继续往下。换会话后回到建档时的工作区靠这一条。
2. **当前目录**：`reusable=yes` 就复用。
3. **已 checkout 期望分支的链接 worktree**：用 `git worktree list --porcelain` 查（第一项是主工作树，不算），有就复用。

### 新建（路径取 `default_path`）

- **期望分支已存在，且没有被任何工作区 checkout** → `git worktree add <路径> <分支>`，不建分支，不问基线。
- **其他情况**（含主工作树停在功能分支上、detached HEAD、集成分支、未给锚点的新会话）→ 新建前向用户一次确认基线、分支名和路径，确认后 `git worktree add <路径> -b <分支> <基线>`：
  - 基线：取 `base`；当前所在分支若是非集成的命名分支，列为可选的另一基线。不从当前 HEAD 静默拉分支——那会夹带其他会话未合并的提交。`base` 为空时不新建（见停止条件）。
  - 分支名：默认期望分支，须匹配命名模式。期望分支已存在但正被主工作树占用时，一个分支不能同时被两个工作区 checkout，确认时说明并请用户另取分支名。
- **`.gitignore`**：worktree 目录的忽略规则由 init-workflow 部署时补写，本技能不检查、不改 `.gitignore`。

停止条件：

- 用户拒绝确认 → 不建；调用方停下，告诉用户可改选基线、分支名或路径后重来。
- 基线推断不出（检测输出 `base` 为空，即 `resolved.env` 没有该分支类型的 `base.<类型>`），或基线分支在本地不存在（`git show-ref --verify refs/heads/<基线>` 失败）→ 不新建，报告原因，请用户指定基线；不拿默认分支或当前 HEAD 顶替。
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

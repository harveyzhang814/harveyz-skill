---
name: manage-worktree
description: "Prepare, enter, inspect, merge, or leave the git worktree a task works in — reuse the task's existing worktree or create one from an explicit, rule-derived base without asking, bind the session to it on Claude Code, Codex, or any other host, check it is a linked worktree on a named non-integration branch, inside an Agent Canvas node also create worktrees through the App and report enter/leave to the node's worktree lease (optional, harmless elsewhere), merge it into the repo's merge target through the repo's own merge script, and on leave inside an Agent Canvas node let the App delete the worktree only if it is merged and no one else uses it. Called by init-spec, develop-plan, and handoff; never pushes, never deletes branches, never forces. Triggers: 'prepare a worktree', 'enter this worktree', 'check my worktree', 'merge this worktree', 'leave this worktree'."
user_invocable: true
version: "0.5.0"
---

# 管理 worktree

## 作用（说明）

一个任务从建档、写计划到交接、验收，始终在同一个命名分支的 worktree 里进行。本技能是建立或复用、进出、检测 worktree 的唯一写法，init-spec、develop-plan、handoff 统一调用它，不各自另写。在 Agent Canvas 节点内，「离开」还会把已合并、不再有人占用的 worktree 交给 App 删除，免得用完的工作区越积越多。

**边界：** 只在 Agent Canvas 节点内、经 App 校验后删除已合并且无人占用的 worktree（「离开」调 `leave-worktree.sh`，删不删全由 App 判定）；绝不删分支、绝不 `--force`。禁止手写 `git worktree remove`、`git branch -d/-D` 或其他删除工作区、分支的命令，删除只经 App 的检查；不 push；不迁移、不改写规则文件与 `resolved.env`；检测不通过时只报告，不自行切换分支或修复。唯一的合并路径是「合并」调用仓库部署的合并脚本，不自己拼 `git merge`。

## 触发条件

- 调用方：init-spec 建档前、develop-plan 开工前、handoff 的 author 阶段起草交接文档前调用「准备」；handoff 的 verify 与 accept 调用「进入」。
- 用户直接要求，例如“准备一个 worktree”“进入这个 worktree”“检查我的 worktree”“合并”“离开这个 worktree”。
- 「合并」只在用户明确说“合并”，或项目指令规定时由调用方触发（见「合并」一节）。
- 「离开」：handoff 各阶段结束时、「合并」返回 0 后（项目指令规定时），或用户要求时由调用方触发（见「离开」一节）。

调用方约定：本技能不可用时，调用方停下，告诉用户需要安装 `devflow` bundle 中的 manage-worktree，不自行兜底建 worktree。

## 动作

| 动作 | 输入 | 行为 | 结果 |
|---|---|---|---|
| 「准备」 | 任务 topic（用作分支名 slug）；可选的期望分支类型（默认 `feature`）；可选的锚点文件路径（本任务已产生的决定记录、Spec 或计划） | 找到或建出工作区，进入 | 工作区绝对路径、分支名、基线（新建时）、检测结果 |
| 「进入」 | 已有工作区的绝对路径；可选的期望分支名 | 检测后按宿主进入；分支与期望不符时报告，不切换 | 同上 |
| 「检测」 | 无（检测当前所在工作区） | 只读检测 | 检测结果 |
| 「合并」 | 无（作用于当前所在工作区） | 调用 `scripts/merge-worktree.sh`，由仓库的合并脚本把当前分支并入合并目标 | 合并脚本的输出与退出码 |
| 「离开」 | 可选：离开前所在工作区的绝对路径（调用方知道自己在离开哪个时必须给） | 按宿主离开；画布节点内再运行 `scripts/leave-worktree.sh`，释放本节点对该工作区的占用并经 App 做删除检查；画布外工作区保留 | `leave-worktree.sh` 的输出（画布外为 `canvas=no`，报告注明工作区保留） |

## 规则来源

所有动作的取值（集成分支、基线、合并目标、worktree 目录）都来自 `.hskill/init-workflow/resolved.env`，以基线分支上已提交的那份为准，不读规则文件，也不 `source` 它（逐行读取）。`inspect-worktree.sh` 分两步取：

1. 引导：依次取当前工作区根、主工作树根下的 `resolved.env`，用第一份得到 `base.<类型>`（「准备」用期望分支类型，其余动作用 `feature`；该键缺失时改用 `base.feature`，再缺失用第一个集成分支，仅用于定位第 2 步）；两处都没有，也按未部署处理。
2. 权威：`git show <该基线分支>:.hskill/init-workflow/resolved.env`，以它的取值输出。这一份读不到（基线分支上没有此文件，或该分支在本地不存在）→ 退出码 4，`reason=base-not-deployed`，并输出 `base=<该基线分支>`。

因此主工作树停在别的会话的分支上，或目标工作区是部署前建的分支，都不影响取值。任何取值都不按默认分支猜：`resolved.env` 没有 `base.<类型>` 时 `base` 为空；没有集成分支（`integration_branches` 缺失或为空）时整份视为无效，退出码 4。退出码 4 时各动作停下：仓库未部署或文件无效，提示先在该仓库（重新）部署 init-workflow；`base-not-deployed` 时仓库已部署，提示把部署合进 `base` 所指的分支，或核对该类型的基线是否推断正确。

## 画布节点内补调租约

Agent Canvas 会记录每个节点占用哪个 worktree（租约），删除 worktree 时靠它避开仍在使用的目录。这一节是可选的补充，只在 Agent Canvas 的节点里生效；其他环境（普通终端、别的项目与宿主）完全不受影响，照旧只做「准备」「进入」「离开」本身。

**什么时候算「在画布节点内」：** 环境变量 `AGENT_CANVAS_NODE_TOKEN` 非空，**且** `command -v agent-canvas-ctl` 有结果。只看环境，不调用 App。不满足就是画布外：画布外不调用任何 `agent-canvas-ctl` 命令，也不提示、不报错。

- **「进入」完成后**（含「准备」复用或新建后的进入），在画布节点内执行一次：

  ```bash
  agent-canvas-ctl claim-worktree --path <工作区绝对路径>
  ```

  - 必须传绝对路径：opencode、Pi 等宿主的节点一般停在启动目录，不传 `--path` 会领用错目录。
  - Claude Code 的 `EnterWorktree` 已经自动领用，再补调一次只是幂等刷新，照样执行，不按宿主区分。
- **「准备」新建时**，画布节点内由 `create-worktree.sh` 调 `agent-canvas-ctl create-worktree`，新建与登记占用一步完成（见「准备」）；之后「进入」的补调照常执行（幂等）。
- **「离开」完成后**，释放占用（`exit-worktree`）与删除检查都由 `leave-worktree.sh` 完成，不再单独补调（见「离开」）。
- **失败不阻断：** `claim-worktree` 或 `leave-worktree.sh` 里的租约调用失败时，只把错误原文写进本动作的报告，不影响「进入」「离开」本身的结果，也不重试、不改走别的路径。例外是「准备」新建时的 `create-worktree` 失败：没建成就停下，见「准备」。常见错误：`lease-service-unavailable`（App 未在线、不是租约的写者，或版本不带租约）、`not-ready`（服务还没就绪）、`no-node-identity`（当前进程拿不到节点身份）。
- **各宿主写法一致：** 一律用这条 CLI，不按宿主改用 MCP；前提是该宿主的工具 shell 能拿到 token 和 PATH，拿不到时按画布外处理。

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
| 4 | `resolved.env` 不可用，只输出 `resolved`、`verdict=n/a`、`reason` 三行（`base-not-deployed` 另加 `base` 一行）：仓库未部署——目标工作区和主工作树都没有（`resolved=missing`、`reason=workflow-not-deployed`）；基线分支未部署——本地有，基线分支上读不到（`resolved=missing`、`base=<基线>`、`reason=base-not-deployed`）；或文件无效——缺 `integration_branches` 或其值为空（`resolved=<相对路径>`、`reason=resolved-invalid`）；非 git 目录先于此判断 | 所有动作停下，按 `reason` 说明原因，不继续、不兜底：`base-not-deployed` 提示把部署合进 `base` 所指的分支或核对基线；其余提示该仓库需（重新）部署 init-workflow |

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
| 4 | 仓库未部署 `resolved.env`，或它无效（`resolved-invalid`）；或基线分支上没有它（`base-not-deployed`） | 停下：前两种提示先（重新）部署 init-workflow；`base-not-deployed` 提示把部署合进输出点名的基线分支 |
| 5 | 检测未通过：当前目录不是链接 worktree 的根目录（含其子目录）、detached HEAD、或处于集成分支 | 按输出的 `reason` 报告，不合并 |
| 6 | `resolved.env` 没有合并目标 | 报告“本仓库未配置合并目标”，不合并 |
| 7 | 本工作区缺合并脚本（本分支早于部署） | 提示先把 `<merge_target>` 并入本分支再「合并」，不退回 `git merge` |

合并脚本返回 0、1、2 以外的退出码时，原样透传，不改写；按脚本输出报告。

不 push（合并只更新本地合并目标分支），不删除分支；合并本身不动 worktree。合并返回 0 后，调用方按项目指令接着「离开」：在画布节点内，本节点若是最后一个占用者，App 会删掉这个已合并的 worktree（分支保留）；画布外工作区保留。

## 「准备」

先在当前目录检测一次，带上 `--type <分支类型> --branch <分支类型>/<slug>`（后者即期望分支）。退出码 3 → 返回“不适用”。否则先找已有，找不到再新建。

### 找已有（命中即止，不询问）

1. **锚点所在的工作区**：锚点按绝对路径解析（相对路径相对当前目录），取它所在的工作区根（`git -C <锚点所在目录> rev-parse --show-toplevel`）检测，`reusable=yes` 就复用；否则报告原因（文件不存在、在主工作树、detached 或在集成分支上），继续往下。换会话后回到建档时的工作区靠这一条。
2. **当前目录**：`reusable=yes` 就复用。
3. **已 checkout 期望分支的链接 worktree**：用 `git worktree list --porcelain` 查（第一项是主工作树，不算），有就复用。

### 新建（路径取 `default_path`）

新建一律调用脚本，不手写 `git worktree add`：

```bash
bash <skill 目录>/scripts/create-worktree.sh --branch <分支> [--base <基线>] --path <default_path> --repo <当前仓库根的绝对路径>
```

- **期望分支已存在，且没有被任何工作区 checkout** → 不带 `--base`：不建分支，不问基线。
- **其他情况**（含主工作树停在功能分支上、detached HEAD、集成分支、未给锚点的新会话）→ 按下面的取值带 `--base <基线>`，不向用户确认；建好后在报告里写明基线、分支名和路径：
  - 基线：只取 `base`。不从当前 HEAD 拉分支——那会夹带其他会话未合并的提交。`base` 为空时不新建（见停止条件）。
  - 分支名：用期望分支，须匹配命名模式。期望分支已存在但正被主工作树占用时，一个分支不能同时被两个工作区 checkout，不新建，报告原因并请用户另取分支名。
- **`.gitignore`**：worktree 目录的忽略规则由 init-workflow 部署时补写，本技能不检查、不改 `.gitignore`。

脚本按环境选择怎么建（画布判定同「画布节点内补调租约」）：

- **画布节点内**：调 `agent-canvas-ctl create-worktree`，由 App 建出 worktree 并登记本节点为占用者（来源 `create`），没有「建好到进入之间未登记」的空档。
- **画布外**：执行 `git -C <仓库> worktree add <路径> <分支>`，带 `--base` 时为 `git -C <仓库> worktree add <路径> -b <分支> <基线>`，与以前相同。

输出每行一个 `key=value`：

| 退出码 | 输出 | 处理 |
|---|---|---|
| 0 | `created=yes`、`path=<绝对路径>`、`branch=<分支>`；画布内另有 `leased=yes\|no`（`no` 时 `detail=` 为登记失败原文） | 按「收尾」进入；`leased=no` 时进入后的 `claim-worktree` 补调会补登记 |
| 1 | `created=no`、`reason=<代码>`、`detail=<原文>` | 停下，按 `reason` 报告，**不退回 `git worktree add` 自建**：退回会绕过 App，留下未登记的 worktree。画布内 `reason` 是 App 返回的 code（`path-exists`、`branch-in-use`、`branch-exists`、`base-required`、`base-not-found`、`not-a-repo`、`git-failed`、`no-node-identity`、`not-ready`、`lease-service-unavailable` …），取不到结构化 code（如 App 不在线时的纯文本错误）为 `create-failed`；画布外 git 失败为 `git-failed` |
| 2 | 用法错误（缺参数、`--path`/`--repo` 不是绝对路径） | 修正调用参数后重跑 |

停止条件：

- 基线推断不出（检测输出 `base` 为空，即 `resolved.env` 没有该分支类型的 `base.<类型>`），或基线分支在本地不存在（`git show-ref --verify refs/heads/<基线>` 失败）→ 不新建，报告原因，请用户指定基线；不拿默认分支或当前 HEAD 顶替。
- 目标路径已存在 → 不覆盖，报告并请用户另选路径。

### 收尾

复用当前目录时，开头那次检测就是结果。其他情况按「进入」进入找到或建好的工作区。无论哪种，工作区就绪后都按「画布节点内补调租约」补调一次（经「进入」的情况已含在其第 4 步，不重复）。返回工作区绝对路径、分支名、基线（仅新建时）和检测结果。

## 「进入」

1. 对目标路径检测一次：`--path <工作区绝对路径>`。退出码 3，或结果含 `not-root`、`not-linked` → 报告不通过，不进入，也不在当前目录继续；由调用方按自己的规则打回或重建，本技能不自行修复。
2. 按「按宿主进出」进入，核对后续命令的工作目录确实是该工作区。第 1 步的检测就是结果，进入后不重跑。
3. 给了期望分支名而 `branch` 与之不符 → 报告不通过，不切换分支。
4. 进入完成且上面都通过后，按「画布节点内补调租约」补调 `claim-worktree`；失败只记入报告。

## 「离开」

1. 记下离开前所在工作区的绝对路径 W：Claude Code 即离开前的工作区根；按「通用兜底」用绝对路径操作工作区的，即那个工作区。
2. 按「按宿主进出」离开。
3. 在宿主离开之后、不在 W 里运行：

   ```bash
   bash <skill 目录>/scripts/leave-worktree.sh --path <W>
   ```

   只在确实不知道离开的是哪个时省略 `--path`：脚本按节点身份查本节点占用的 worktree，恰好一个才处理。
4. 原样呈现输出。你只调用脚本、呈现结果：不自己删工作区、不删分支，结果是「不删」时也不另想办法删。

脚本只处理被离开的那一个工作区，**删不删全由 App 判定**，脚本只在调用前做本地守卫：

- **画布外**（判定同「画布节点内补调租约」）：只输出 `canvas=no`，不调用任何 `agent-canvas-ctl`。工作区保留，报告里注明画布外不删除。
- **节点还没真正离开 W**：本节点就是在 W 里启动的（租约来源含 `spawn-cwd`）→ `started-here`；脚本的当前目录在 W 内 → `cwd-inside`。两种都不释放、不删，W 留到 close-node 或外部收尾停止节点后再删。
- **其余情况**：先释放占用（`exit-worktree`，失败只记入报告），再确认 App 版本、取 `merge_target`（对 W 跑 `inspect-worktree.sh`），最后调 `agent-canvas-ctl remove-worktree --path W --merged-into <merge_target>`，由 App 检查其他占用者、打开的窗口、困在 W 里的会话、锁、未提交改动与是否已合入。
- **App 版本**靠读已安装 CLI 的 `help remove-worktree` 判断，所以 App 已升级但还没重启时也可能通过这一检查。

刚从基线建出、还没有提交的工作区，HEAD 等于基线，会被视为已合入；最后一个占用者离开时它会被删，分支保留，再「准备」会按「期望分支已存在」直接挂回。

**输出**：第一行 `canvas=yes|no`，之后每行一个 `key=value`：

| 键 | 取值 |
|---|---|
| `worktree` | 处理的工作区绝对路径，至多一个 |
| `released` | `yes` 已释放；`no` 本来就没有占用；`error` 释放失败（原文进 `detail`）；`skipped` 没释放（`started-here`、`cwd-inside`） |
| `removed` | `yes` 已删；`no` 保留 |
| `reason` | `removed=no` 时的原因，见下表 |
| `branch_kept` | 删成时保留的分支名 |
| `detail` | 失败原文（单行，多处失败用 ` \| ` 连接） |
| `lookup` | 没有处理时出现：`none`（没给 `--path`，本节点没占用任何工作区）；`ambiguous`（没给 `--path`，占用多个，随后每行一个 `candidate=<路径>`，请带 `--path` 重来）；`error`（查节点身份或租约失败，随后有 `detail=`；给了 `--path` 时前面有 `worktree=` 行）。三种都什么也没释放、没删 |

| `reason` | 含义 |
|---|---|
| `started-here`、`cwd-inside` | 节点还没真正离开 W，见上文 |
| `app-too-old` | 已安装的 App 的 `remove-worktree` 还没有困住会话与窗口检查，只释放、不删；升级并重启 App 后再离开才会删 |
| `no-merge-target` | 取不到合并目标（`resolved.env` 没有 `merge_target`） |
| `workflow-not-deployed`、`base-not-deployed`、`resolved-invalid` | `inspect-worktree.sh` 退出码 4 的 `reason`，`resolved.env` 不可用 |
| `held-by-others` | 还有别的节点占用 W，由最后一个离开的删 |
| `not-merged` | W 的 HEAD 还没并入 `merge_target` |
| `dirty` | W 里有未提交改动 |
| `locked` | W 被 git 锁住；只报告，不解锁 |
| `open-window` | 有窗口开在 W 上 |
| `trapped-session`、`session-scan-failed` | 有会话被困在 W 里；扫描会话失败 |
| `already-removed`、`lease-service-unavailable`、`not-ready` 及 App 返回的其他 code | 原样报告 |
| `remove-failed` | `remove-worktree` 失败但取不到结构化 code（如 App 不在线时的纯文本错误），原文在 `detail` |

**退出码**：`0` 正常，含所有「不删」与 `lookup` 结果，「离开」不会因删除检查而失败；`2` 用法错误（`--path` 缺参数或不是绝对路径、未知参数）。

## 按宿主进出

各动作说的「进入」「离开」按宿主执行下面对应小节；宿主不在其中、对应能力不可用或被拒绝，才按「通用兜底」办。**已知宿主不得因兜底也能完成命令就跳过原生进入/离开动作。** 进入是否完成的判据：**后续命令的工作目录就是那个工作区**。无论哪个宿主，每次「进入」完成后在画布节点内都还要按「画布节点内补调租约」补调 `claim-worktree`，每次「离开」完成后都按「离开」运行 `leave-worktree.sh`（画布外它只输出 `canvas=no`），不因下面某个宿主小节没写而跳过。

### Claude Code

| 动作 | 手段 |
|---|---|
| 进入 | `EnterWorktree(path: "<工作区绝对路径>")` |
| 离开 | `ExitWorktree(action: "keep")`，随后 `bash <skill 目录>/scripts/leave-worktree.sh --path <离开前的工作区根>` |

- 工具尚未出现在可用工具中时，先用 ToolSearch 找到 `EnterWorktree` / `ExitWorktree`，不要降级成 `cd`。
- **只用 `path` 模式，绝不用 `name`**：`name` 会自建分支（`worktree-<name 把 / 换成 +>`，常过不了分支命名规则），基线默认取 `origin/<默认分支>`。分支名和基线必须由本技能按规则定，所以只能先由「准备」的 `create-worktree.sh` 建、再用 `path` 进。
- `path` 只认当前仓库（或嵌套在其中的仓库）登记过的工作区，跨仓库直接拒绝，此时按通用兜底办。
- **会话已经在某个 worktree 里时，只能直接切进 `.claude/worktrees/` 下的工作区**；目标在 `.worktrees/` 等其他位置会被拒，报 “Switching from this session is limited to worktrees managed by Claude Code”。此时先 `ExitWorktree(action: "keep")` 回到启动目录，再 `EnterWorktree(path:)`。前一步也是「离开」，同样随后运行 `leave-worktree.sh --path <刚离开的工作区>`。从启动目录首次进入不受这条限制。
- 必须由当前会话直接调用，不能交给 fork 或 subagent 代调。
- 离开一律 `action: "keep"`，绝不 `remove`：`remove` 会连分支一起删。工作区删不删只经 `leave-worktree.sh` 交给 App 判定。

### Codex

Codex 没有 `EnterWorktree` / `ExitWorktree` 工具。进入已建好的工作区时，选择一种能让会话的 workspace 根就是该工作区的启动方式：

- CLI：从该目录启动，或用 `codex -C <工作区>` / `codex exec -C <工作区> ...`。
- Codex App：打开该持久 worktree 作为 workspace，再开始新的 chat。
- 宿主无法重新绑定 workspace：按「通用兜底」逐条使用绝对路径与显式工作目录。

不要用 `--worktree`：它会另建新的 managed worktree，不是进入已建的路径。App 的 Handoff 是同一 chat 在 Local 与 Worktree 之间移动，不能替代进入指定工作区。离开没有宿主动作：停止在该工作区里操作，再在工作区外按「离开」运行 `leave-worktree.sh --path <工作区>`。会话本身以该工作区为启动目录时，脚本报告 `started-here`，工作区留到节点收尾。

### 通用兜底（其他宿主、能力不可用或跨仓库）

每条命令自带限定，不要靠单独的 `cd`（多数宿主里它只在单条命令内有效）：

- git：`git -C <工作区> <命令>`
- 其他 shell 命令：`cd <工作区> && <命令>` 写在同一条命令里
- 读写、搜索文件一律用工作区内的绝对路径——相对路径按会话当前目录解析，会静默改到另一份同名文件。

离开时停止指向该工作区，再按「离开」运行 `leave-worktree.sh --path <工作区>`。

无论哪个宿主，「进入」完成后都按「画布节点内补调租约」补调 `claim-worktree`，「离开」完成后都运行 `leave-worktree.sh`；它们不属于上面任何宿主的专属手段。

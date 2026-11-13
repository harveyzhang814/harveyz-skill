---
name: init-workflow
description: "Initialize or update git branch management standards: reads .hskill/init-workflow/workflow-config.yml, audits config, incrementally generates and deploys git hooks (pre-commit, commit-msg, pre-push, post-checkout), deploys resolved.env, the workflow doc and the standard merge script, and bootstraps the first commit and missing integration branches. Triggers: initializing a new git repo, first-time git setup, user asks to set/update branch protection or naming rules, reinstalling git hooks, or syncing after skill/template updates."
user_invocable: true
version: "5.0.3"
---

# Git 工作流初始化

读取 `.hskill/init-workflow/workflow-config.yml`，审核配置，差量部署 git hooks、`resolved.env`、工作流文档和标准合并脚本。
重新运行时自动检测配置变更、用户手改冲突、用户代码与新规则的交叉冲突，一次性汇总让用户决策后再写入。

---

## 执行步骤

### Step 1 — 确认 git 仓库

```bash
git rev-parse --show-toplevel
```

若不在 git 仓库中，询问用户是否先执行 `git init`，用户拒绝则停止，告知需先 `git init` 再运行本 skill。`git init` 不必指定分支名，Step 9 的起步引导会把 HEAD 改到根集成分支。

**在哪运行：** 仓库还没有提交时，在主工作树运行即可，部署产物连同已有文件由 Step 9 的起步引导做成根提交。仓库已有提交时，在一条 `chore/` 分支的 worktree 里运行（用 `manage-worktree`「准备」建；合并目标分支还不存在时，基线用根集成分支，如 `main`）：部署产物在这条分支提交，结束后用刚部署的合并脚本合并，再把主工作树切到合并目标（见 Step 9「主工作树常驻合并目标」）。不要在主工作树的集成分支上运行——hooks 部署后立即生效，产物就提交不进去了。

---

### Step 2 — 读取配置

按以下顺序查找配置文件：

1. `.hskill/init-workflow/workflow-config.yml`
2. 项目根目录 `workflow-config.yml`（向后兼容）
3. 项目根目录 `.claude/workflow-config.yml`（向后兼容）

若均不存在，询问用户：
- 使用默认配置（从此 skill 的 `references/workflow-config.yml` 复制到 `.hskill/init-workflow/workflow-config.yml`）
- 还是中止并自行创建后重新运行

**配置的三级查找只在解释器 `references/workflow_resolve.py` 里实现**——`deploy_artifacts.py`（Step 6.0）与文档、合并脚本、`resolved.env` 都经它取值，本步骤的查找顺序只用于告知用户配置在哪、以及是否需要迁移，不要另写一套解析逻辑去生成产物。

找到后读取并解析 YAML。若文件来自向后兼容路径（2 或 3），询问用户是否将其移动到 `.hskill/init-workflow/workflow-config.yml`；用户同意则执行移动，否则继续使用原位置（不影响本次运行）。

---

### Step 3 — 审核配置

对配置内容逐项检查，**发现所有问题后一次性报告，不逐条中止**。

**结构校验：**
- `meta.preset` 若存在，必须是 `gitflow`、`github-flow`、`trunk-based`、`custom` 之一
- `commit_message.format` 必须是 `conventional`、`regex`、`none` 之一
- 若 `format: regex`，必须同时存在 `pattern` 字段

**逻辑校验：**
- `branches.protected` 至少有一个分支；写了 `merge_from:` 的分支须列出条目（块列表 `- 来源` 或行内 `[a, "b/*"]` 均可，缩进任意但须一致；明确为空写 `merge_from: []`）。解释器解析不出时 `deploy_artifacts.py` 以退出码 3 停下，见 Step 6.0
- `branches.protected` 中任何分支的 `merge_from` 不得包含自身（循环依赖）
- `push_rules.block_force_push` 中的分支建议与 `branches.protected` 保持一致，不一致则警告
- `branch_naming.exempt` 中的分支不应同时被 `allowed_patterns` 覆盖（冗余）

**正则校验：**（对每个 pattern 执行，返回 2 = 非法）
```bash
echo "" | grep -E "<pattern>" > /dev/null 2>&1; echo $?
```

**新增字段：**
- `worktree.dir`（缺省 `.worktrees`）：worktree 所在目录，路径为 `<dir>/<分支名，/ 换成 +>`。旧配置没有此节时按缺省值解释，不报错。
- `merge.pre_checks`（缺省 `[]`）：合并前依次执行的命令，在被合并分支的 worktree 根目录执行。占位符：`{target}` 替换为合并目标分支；`{script_dir}` 替换为合并脚本所在目录的绝对路径（已带引号，路径含空格也安全，不要再给它加引号），用于调用放在合并脚本旁边的检查脚本，例如 `- node {script_dir}/check-file-token-budget.js --changed-since {target}`。**只支持块列表写法**（`- 命令` 逐行），**列表项后不得加行内注释**（解释器逐行取值，注释会被当作命令的一部分）。

审核通过打印 `✅ 配置审核通过`，审核失败列出所有问题并停止。

---

### Step 4 — 分析当前状态（仅当 `.githooks/` 已存在时）

**首次安装时跳过此步骤，直接进入 Step 5。**

目标：写入任何文件之前，全面收集需要用户决策的冲突，在 Step 5 一次性呈现。实现细节见 `references/conflict-analysis.md`。

#### 4a. Lock 文件 diff
读取 `.githooks/.workflow-config.lock.yml`（不存在则视为全量新增，跳过）。对比上次配置与当前配置，生成 +/~/- 变更摘要。**提取 YAML 分支名时必须用 python3 精确解析，不得用 `grep "name:"`**（见 reference 中的脚本）。

#### 4b. MANAGED 块 hash 校验
运行 `python3 <skill-path>/references/block_hash.py check .githooks/<hook>...`，输出 `MODIFIED` 的块 → 用户手改，记录为类型 C 冲突（附 diff）。不要手算 hash。

#### 4c. 外部代码扫描
提取每个 hook 中 MANAGED 块外的用户手写代码，识别其中引用的分支名、提交类型、pattern、外部脚本调用。

#### 4d. 冲突检测
综合 4a/4b/4c，识别四种冲突类型（A 条件重叠、B 引用断裂、C 手改冲突、D 新增重叠）；第五种类型 E（git config 漂移）由 Step 4e 另行检测。类型定义与选项见 `references/conflict-analysis.md`。

#### 4e. git config 健康检查

检查 `core.hooksPath`（期望 `.githooks`）和 `merge.ff`（期望 `false`），值不符或缺失 → 类型 E 冲突。Step 5 默认选「自动修复」，Step 6 写完 hooks 后立即执行修复。检测命令、和 lock 的对比规则见 `references/conflict-analysis.md`「类型 E」。

---

### Step 5 — 冲突解决（一次性汇总，用户逐条决策）

将 Step 4 发现的所有冲突**一次性呈现**，每条附带类型标签和选项，用户逐条决策后进入 Step 6。无冲突则直接进入 Step 6。

呈现格式与 A–E 各类型的选项见 `references/conflict-analysis.md`（「Step 5 冲突呈现格式」「类型 E」两节）。

---

### Step 6 — 解释与部署，再差量生成 hooks

#### 6.0 先解释并部署（本步唯一一次运行）

hooks 的取值来自 `resolved.env`，而 `resolved.env` 由部署脚本写出，所以**先**运行：

```bash
python3 <skill-path>/references/deploy_artifacts.py <仓库根>
```

这一次运行同时写出 Step 7 列出的全部产物。**整次 skill 执行只运行这一次，Step 7 不再运行**：重跑时文件已是新内容，输出全变成 `UNCHANGED`，首次运行的 `NEW` / `UPDATED` 行和 `WARN` 行（用户手改被覆盖的唯一提示）就丢了。把这次的 stdout 与 stderr 完整保存，Step 7 和 Step 9 都用它。

非 0 退出时不生成 hooks，按 stderr 的 `ERROR` 行处理（两种情况都在写任何产物之前退出）：

- 退出码 2：找不到规则文件 → 回到 Step 2。
- 退出码 3：配置解释不出必需取值（`branches.protected` 为空，或某分支写了 `merge_from:` 却解析不出条目）→ 回到 Step 3，向用户报告该行并请其修正配置后重跑。

#### 取值来源与顺序

hooks 里用到的集成分支、合并目标、`merge_trailer`、`merge_script` 以及分支命名的**真实 ERE 模式**，一律取自 `.hskill/init-workflow/resolved.env`（或解释器输出），**不得**直接抄 `workflow-config.yml` 的原文——配置里的写法可能和解释后的有效模式不同。映射：

- `hook-templates.md` 里的 `<allowed_patterns>`（`post-checkout/branch-naming`）= `resolved.env` 的 `naming.1` … `naming.n`，按编号顺序；exempt 列表 = `naming_exempt`（空格分隔，生成 `case` 时改用 `|` 连接）。
- 例外：`pre-push/tags` 块里的 `<allowed_patterns>` 是 **tag** 命名模式，`resolved.env` 不含、解释器也不解析 `tags` 节：读 `resolved.env` 的 `rule_file` 所指的规则文件，取其中 `tags.allowed_patterns`。YAML 双引号里的 `\\` 是一个反斜杠，填进 tags 块时还原为 `\`（如 `"^v[0-9]+\\.[0-9]+"` 填作 `^v[0-9]+\.[0-9]+`）。

#### 生成原则

先确保 hooks 目录存在：

```bash
mkdir -p .githooks
```

根据 Step 5 的决策结果，对每个 hook 文件按以下规则处理：

1. **MANAGED 块**：根据当前配置重新生成内容，块标记先写 `(hash:PLACEHOLDER)`，全部写完后用 `block_hash.py stamp` 填入 hash；块的先后顺序与插入点按 `hook-templates.md`「块顺序」
   - 若 Step 5 中用户选择"保留用户修改"→ 跳过此块，保持现有内容和 hash 不变
   - 若配置中某节 `enforce: false` 且对应 MANAGED 块存在 → 删除该块（保留块外用户代码）

2. **用户代码区（MANAGED 块外）**：永远不覆盖，原样保留。唯一例外：块外手写的合并拦截（如在 commit-msg / pre-push 里判断 `MERGE_HEAD` 与 `Merge-Via` 行的旧代码）已被 `merge-via` 块取代，**经用户同意**后可以删除；删除时同时按 `hook-templates.md` 重新生成 `commit-msg/format` 块，确保其首行是合并提交豁免（`[ -f "$(git rev-parse --git-dir)/MERGE_HEAD" ] && exit 0`），且 `commit-msg/merge-via` 位于它之前——否则远端同步合并会被格式检查拒绝，或 merge-via 永远执行不到。用户不同意则原样保留

3. **差量写入**：生成全文后与磁盘文件对比——内容相同标记 `UNCHANGED`，不同标记 `UPDATED`，新建标记 `NEW`

4. **`merge-via` 块仅在存在合并目标时生成**（`resolved.env` 有 `merge_target`，即某个受保护分支的 `merge_from` 列有 `"feature/*"`）：`commit-msg/merge-via` 与 `pre-push/merge-via` 两个 MANAGED 块，并把合并目标分支的 `branches.protected/<merge_target>` 块换成专用变体（保留“禁止直接提交”，提示改用合并脚本）；其他受保护分支的块不变。没有合并目标时三者都不生成，`commit-msg` 仅因 `commit_message.enforce: true` 才生成。
   - 提交标记是**绊线而非强制**：对远端同步合并（主题以 `Merge branch '<目标>' of ` 开头）放行，所以 `merge-via` 能拦住误操作，拦不住有意绕过。
   - 合并目标分支**首次发布**（远端还没有该分支，此时只检查本地尖端提交）且尖端不是脚本产生的合并时，`pre-push/merge-via` 会拒绝，需要一次 `git push --no-verify`；之后的推送正常。Step 9 的起步引导会用 `WARN first-publish` / `WARN unpushed` 提前指出。
   - 快进合并（`git merge --ff-only <功能分支>`）不产生提交，本地不触发任何 hook，只在推送时被 `pre-push/merge-via` 拦下。

各 hook 的触发条件、固定头部代码、MANAGED 块结构与顺序、块 ID 规范、hash 计算方式及多行内容写入技巧，见 `references/hook-templates.md`。

#### 设置权限和 hooksPath

```bash
chmod +x .githooks/*
git config core.hooksPath .githooks
git config merge.ff false
```

---

### Step 6.5 — 验收测试（可选）

完成 hooks 部署后，询问用户：

```
✅ Hooks 已部署完毕。是否运行验收测试？（在当前 repo 中验证 hooks 实际拦截行为）[y/N]
```

- 用户选 **N** → 直接进入 Step 7。
- 用户选 **Y** → 读取 `references/acceptance-test.md`，按其中说明逐 hook 执行验收场景，展示结果表格。全通过则继续 Step 7；有失败则展示详情并询问用户是否仍继续。

---

### Step 7 — resolved.env、工作流文档、合并脚本（已在 Step 6.0 部署）

**不要在这里重跑 `deploy_artifacts.py`**，使用 Step 6.0 那次运行的输出（`NEW` / `UPDATED` / `UNCHANGED` 逐行与 `WARN`），照录到 Step 9 汇报。每次运行都根据当前配置的最终状态一次性重新生成，确保各产物对同一策略给出相同取值。脚本逐行输出 `<状态> <路径>`，写出的产物：

- `.hskill/init-workflow/resolved.env`：解释结果（格式与键集合见 `references/workflow_resolve.py`）；消费方逐行读取，不得 `source`。
- `docs/reference/git-workflow.md`：工作流文档。文末 `<!-- BEGIN PROJECT NOTES -->` 与 `<!-- END PROJECT NOTES -->` 之间是**项目自填区**，重新渲染时原样保留；这对标记之外的内容以模板为准，不要手改。
- `scripts/merge-to-<合并目标>.sh`：标准合并脚本，仅在有合并目标时部署；项目自己的合并前检查改配置里的 `merge.pre_checks`，不要改脚本。`pre_checks` 在“已包含 / 冲突”判断之前执行，任一失败退出码为 1、不合并。
- `.gitignore`：`<worktree.dir>/` 未被忽略时追加一行（状态：文件原不存在为 `NEW`，追加了一行为 `UPDATED`，已忽略则 `UNCHANGED`）。

**`WARN` 行：** 现有文件没有生成标记（或自填区标记）、且内容与新渲染结果不同时，脚本照旧覆盖，并输出 `WARN`：stdout 里是 `WARN <路径>`，紧挨在该文件的 `UPDATED` 行之前；找回命令（如 `git diff HEAD -- docs/reference/git-workflow.md`）的说明文字走 **stderr**。所以运行时 stdout 与 stderr 都要捕获并照录给用户，说明旧内容可用该命令找回、需要保留的部分手工并入自填区。非 0 退出码的处理见 Step 6.0。

脚本不处理索引：若 `docs/INDEX.md` 存在，由你追加 `docs/reference/git-workflow.md` 的索引行（已存在则跳过）。

---

### Step 8 — 更新 AI 配置文件（可选）

若文件中已出现 `docs/reference/git-workflow.md` 这个路径（Markdown 链接或行内代码都算），跳过该文件。

否则询问用户是否在已存在的 `CLAUDE.md`、`AGENTS.md`、`GEMINI.md` 中追加：

```markdown
## Git 工作流

分支命名规范、保护规则与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。
```

---

### Step 9 — 更新 lock 文件并汇报

#### 更新 lock 文件

将本次生效配置的关键字段写入 `.githooks/.workflow-config.lock.yml`，格式见 `references/lock-file-format.md`。

#### 起步引导（每次都跑，已就绪时什么都不做）

hooks 已经生效，集成分支禁止直接提交；全新仓库因此做不出第一个提交，缺 `staging` 的仓库也建不了以它为基线的 worktree。先预演：

```bash
python3 <skill-path>/references/bootstrap_branches.py <仓库根> --dry-run
```

stdout 逐行一项（`--dry-run` 末行为 `DRY-RUN`）：

| 行 | 含义 |
|---|---|
| `ROOT-COMMIT <根分支>` | 仓库还没有提交：把 HEAD 改到根集成分支（不出现在其他受保护分支 `merge_from` 里的那个，如 `main`），收入所有未被 `.gitignore` 忽略的文件（部署产物和用户已有的文件，同 `git add -A`）做根提交，绕过 hooks |
| `FILE <路径>` | 紧跟 `ROOT-COMMIT`，逐个列出根提交将收入的文件 |
| `CREATE <分支> <来源>` | 本地缺这条集成分支：有 `origin/<分支>` 就从它建，否则从它的上游（`merge_from` 里列出它的那个受保护分支）建 |
| `SWITCH <合并目标>` | 仅全新仓库：根提交后把主工作树切到合并目标常驻（两条分支同一提交，只改 HEAD 指向） |
| `EXISTS <分支>` | 已存在，不动 |
| `WARN unpushed <合并目标> <数量>` | 合并目标上有未推送、不带合并标记行的提交，推送会被 `pre-push/merge-via` 拒绝 |
| `WARN first-publish <合并目标>` | 合并目标还没发布到远端，尖端又不是脚本产生的合并，首次推送会被拒 |

只有 `EXISTS` 行时直接进入汇报。否则把预演结果给用户，确认一次后去掉 `--dry-run` 再跑一次。有 `FILE` 行时请用户逐个过目：密钥（如 `.env`）、依赖目录、构建产物不该进根提交，先补进 `.gitignore` 再重新预演。`WARN` 行只提醒、不推送，stderr 里有处理办法。

**主工作树常驻合并目标：** 主工作树停在合并目标（如 `staging`）上，合并脚本每次合并后都会同步它，hooks、工作流文档和规则文件始终是最新的。停在根分支（如 `main`）上时，这些产物要等发版才到那里：hooks 缺席，直接提交不会被拦，`manage-worktree` 也读不到规则文件，推断出错误的基线。全新仓库由 `SWITCH` 自动切换。已有提交的仓库在 chore 分支合并进合并目标之后，把主工作树切过去（`git -C <主工作树> switch <合并目标>`）；主工作树有未提交改动时不切，告诉用户先处理。

退出码：0 正常；2 找不到规则文件（回到 Step 2）；3 受保护分支推不出唯一的根或存在循环（回到 Step 3）；4 仓库已有提交，但根集成分支在本地和 `origin` 都没有（如默认分支叫 `master`）——不猜从哪建，把 stderr 给用户，由用户改名或建好后重跑。2–4 都在改动之前退出。

#### 汇报结果

用表格展示每个操作的状态：

```
文件                                状态
─────────────────────────────────────────────────────
.hskill/init-workflow/workflow-config.yml   已读取
.githooks/.workflow-config.lock.yml UPDATED（记录新配置快照）
.githooks/pre-commit               UPDATED（main 块 hash 更新；develop 块新增）
.githooks/commit-msg               UNCHANGED
.githooks/pre-push                 UNCHANGED
.githooks/post-checkout            NEW
.hskill/init-workflow/resolved.env UPDATED
scripts/merge-to-<目标>.sh         NEW（无合并目标时写“不适用”）
.gitignore                         NEW（原无该文件）/ UPDATED（追加 <worktree.dir>/）/ UNCHANGED（已忽略）
core.hooksPath                     = .githooks  ✅（或 ❌ 已修复 / ❌ 未修复）
merge.ff                           = false      ✅（或 ❌ 已修复 / ❌ 未修复）
docs/reference/git-workflow.md     UPDATED
CLAUDE.md                          已有引用，跳过
WARN <路径>                        （如有）照录 stdout 的 WARN 行，并附 stderr 的找回命令
起步引导                           照录 ROOT-COMMIT / FILE / CREATE / SWITCH / EXISTS 行；WARN 行附 stderr 的说明
主工作树                           = <合并目标>  ✅（或 ⚠️ 停在 <分支>，附切换命令）
─────────────────────────────────────────────────────
冲突决策摘要：
  [1/3] branches.protected/main 手改块 → 用户选择保留修改
  [2/3] develop 分支条件重叠 → 用户选择使用新配置
  [3/3] wip 类型引用断裂 → 用户选择保留用户代码
```

首次安装时，git config 两行均显示 `✅`。

---

## 参考文件

| 文件 | 说明 | 读取时机 |
|------|------|---------|
| `references/workflow-config.yml` | 配置文件模板 | Step 2：用户无配置时复制 |
| `references/conflict-analysis.md` | 4a–4e 实现脚本、冲突类型 A/B/C/D/E 完整定义与选项、Step 5 呈现格式 | Step 4/5：执行分析前读取 |
| `references/hook-templates.md` | 4 个 hook 的代码模板、块 ID 规范、hash 计算、多行写入技巧 | Step 6：生成 hooks 前 |
| `references/acceptance-test.md` | 验收场景 bash 脚本、期望结果、结果表格格式 | Step 6.5：用户选 Y 时读取 |
| `references/lock-file-format.md` | lock 文件 YAML 格式 | Step 9：写入 lock 文件前 |
| `references/workflow_resolve.py` | 单一解释器（三级查找、推断、`resolved.env`） | 由 deploy_artifacts.py 调用 |
| `references/deploy_artifacts.py` | 一次性部署入口 | Step 6.0：直接执行（仅此一次，Step 7 沿用其输出） |
| `references/git-workflow-template.md` | 工作流文档模板（含占位符与自填区） | 由 deploy_artifacts.py 经 render_docs.render 读取 |
| `references/render_docs.py` | 文档渲染 | 由 deploy_artifacts.py 调用 |
| `references/render_merge_script.py` | 合并脚本渲染 | 由 deploy_artifacts.py 调用 |
| `references/merge-script-template.sh` | 标准合并脚本模板 | 由 render_merge_script.py 读取 |
| `references/block_hash.py` | MANAGED 块 hash 的唯一实现：`check` 校验、`stamp` 填 PLACEHOLDER | Step 4b、Step 6 |
| `references/bootstrap_branches.py` | 起步引导：根提交、补建集成分支、推送提醒 | Step 9：写完 lock 文件后执行（先 `--dry-run`） |

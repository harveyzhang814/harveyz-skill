# 仓库 Agent 指南

本文件是本仓库唯一的 Agent 指令文件，各宿主共用；Claude Code 在仓库里没有 `CLAUDE.md` 时直接读取它。不要再新建 `CLAUDE.md`：它一存在，Claude Code 就只读它、不再读本文件。

## 仓库与技能来源

本仓库维护 Harvey 的 Agent 技能。技能在 `skills/` 下编写，再安装或发布到不同宿主。`skills/` 是唯一的内容源；只在这里读取和修改技能，不要编辑已安装的副本或宿主的技能目录，因为它们可能落后于仓库。

用户安装方式：`npm install -g harveyz-skill` 后运行 `hskill` 交互安装。

## 部署与发布

部署时始终从已集成的 `staging` 分支提取技能，不要从当前工作树复制。主工作树不等于 `staging`，它可能停在某个会话的工作分支上，那里的技能内容比刚合并进 `staging` 的旧；直接复制会把旧版本装上，而且不报错。

```bash
git archive staging skills/<category>/<skill> | tar -x -C <temporary-directory>
rsync -a --exclude '.DS_Store' <temporary-directory>/skills/<category>/<skill>/ <target-skill-root>/<skill>/
```

按安装目标确定 `<target-skill-root>`，不要假定宿主配置目录。部署后必须核对版本，例如 `grep '^version:' <target-skill-root>/<skill>/SKILL.md`，与目标版本对上。

技能位于 `skills/<category>/<skill-name>/`，每个目录包含 `SKILL.md`，也可包含 `references/`、脚本、资源和测试。`SKILL.md` 以 YAML frontmatter 开头，包含 `name`、`description`、`user_invocable`、`version` 等字段。格式、命名与注册规则以 [skill 规范](docs/reference/skill-spec.md) 为准。

发布技能时，在 `skills-index.json` 中登记 `path` 和 `bundle`；新增 bundle 时补充 `bundleMeta`；技能内容变化时更新 `contentHash` 和 `contentVersion`。`skills-index.json` 是打包依据，未登记的技能不会进入 npm 包。

## 输出格式

- org-mode：粗体用单个星号；标题以 `*` 开头且不跳级。Denote 文件名格式为 `{YYYYMMDDTHHMMSS}--{title}__{type}.org`，保存到 `~/Documents/notes/`。ASCII 图只能使用这些字符：`+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "`，不用 Unicode 制表符。
- Markdown 报告：可使用 YAML frontmatter 和用户配置的 `skillDir`，不受上述 org-mode 和 Denote 规则约束。

## 测试

运行 `npm test` 验证 hskill CLI 行为（安装、交互、JSON 输出）及所有 `SKILL.md` 的格式。添加测试前先读 [测试指南](docs/reference/testing-guide.md)。

## Git 与工作区

完整规则见 [Git 工作流规范](docs/reference/git-workflow.md)。每个功能或迭代使用一条 `feature/`、`fix/`、`chore/`、`doc/` 或 `release/` 分支，累积所有相关改动，不为每次提交单独建分支。`core.hooksPath=.githooks` 与 `merge.ff=false` 是仓库级设置，存在共享的 `.git/config` 里，对所有 worktree 生效，只在新 clone 时设置一次：

```bash
git config core.hooksPath .githooks
git config merge.ff false
```

新建或复用 worktree 一律调用 `manage-worktree`（「准备」建或复用并进入，「进入」进入已有路径），不要手写 `git worktree add`。它替你守住两条约束：

1. **基线分支 `staging` 必须显式给出。** 不给就从主工作树当前 HEAD 拉分支，而主工作树可能正停在别的会话的分支上；新分支会静默夹带别人未合并的提交，合并时等于替对方发布没写完的东西，而且不报错。
2. **建完立刻进入。** 不进入的话，后面每条 git 命令都作用在主工作树上。进入方式按宿主而定，以 `manage-worktree` 为准；宿主无法绑定时，每条 git 命令用 `git -C <worktree-path>`，文件读写用绝对路径。单独执行的 `cd` 不会影响后续命令。

worktree 路径约定为 `.worktrees/<分支名，/ 换成 +>`（例如 `feature/foo` → `.worktrees/feature+foo`），`.worktrees/` 已被 `.gitignore` 忽略。`.claude/worktrees/` 下已有的目录是历史遗留，不动。

合并只在用户明确说“合并”或“完成”后进行：从工作分支的 worktree 运行 `scripts/merge-to-staging.sh`。合并前先运行 `git rev-parse --abbrev-ref HEAD`，结果要与预期分支对上，打印出来不算核对。脚本以本地原子更新和重试方式合并到 `staging`，并同步 checkout 着 `staging` 的工作树，不会推送 `origin`；当前在 `staging`、`main` 或 detached HEAD 时脚本拒绝执行。不要手动合并到 `main` 或 `staging`，也不要直接向这两个分支提交。

## 跨会话交接

`handoff` 是通用技能，不依赖 Claude。宿主支持技能调用时调用 `handoff`，否则按技能文档执行；仓库配置见 `.hskill/handoff/config.md`。保留 `author`、`verify`、`self-test`、`accept` 四个阶段。斜杠命令只是部分宿主的调用方式，并非流程要求。

一条分支不能被两个 worktree 同时 checkout，下面的规则都由此推出：**一次交接自始至终只用一个工作区，由交出方建、交出方留、交出方收**，交出方、接手方、验收方轮流进入，谁都不另建。若接手方另建，验收方回到的是自己建的那个，看不到接手方的改动，交接链就断了。

1. 交出方在 worktree 里写交接文档（落 `docs/commute/`），连同相关产物提交到该分支。提交后保留工作区，不要 `git worktree remove`：它是接手方的落脚点，也是验收要回来的地方。
2. 交接期间不合并到 `staging`。分支保持未合并状态，最后一次性合并。
3. 交接文档 frontmatter 的 `branch` 与 `worktree` 成对出现，都由交出方填写。分支名是权威依据，worktree 路径是它当前的落脚点，必须写明，不能让接手方去猜；路径失效时用 `git worktree list` 查这条分支挂在哪。
4. 接手方不建 worktree、不建分支，按 `manage-worktree` 的「进入」进入文档里的路径，核对当前分支与 `branch` 一致后再开工。`git worktree add` 失败说明该分支已被这个工作区 checkout，这是提示，不是障碍。离开时只保留工作区，绝不 `remove`。
5. 验收也在这个工作区里进行，不在主工作树或 `staging`/`main` 上进行：那里没有接手方的改动，跑出来的通过是别的代码的结果，看起来像验过了，比不跑更有害。验收方进入后先重读交接文档，接手方的自测记录与 `status` 只在这一份里。
6. 只有交出方能合并，接手方与验收方都不合。验收通过后，交出方按上文方式合并到 `staging`，再 `git worktree remove` 收掉交接工作区。
7. 同一时刻只有一方在这个工作区里操作：交出方写完停手，接手方做完停手，再轮到验收方。两个会话同时在一个工作区里跑 git 会互相破坏暂存区。

### 计划后交接给执行模型

1. develop-plan 的计划经用户确认后，先询问用户“本会话执行，还是交接给其他执行方”。
2. 选择本会话执行：按计划开头的 `REQUIRED SUB-SKILL` 执行。选择交接：不调用执行技能；交出方按 develop-plan 第 5 步的条件（执行方为全新会话）选定执行技能，填入计划开头的 `REQUIRED SUB-SKILL` 并提交计划，再走 `handoff` 的 `author` 阶段；交接文档写明所选技能及理由。一份计划对应一次交接；交接文档把 Spec 与计划列为权威依据；最小验收锚点写成“各 Task 的测试与计划写定的断言一致，并全部通过”，再加上 Spec 的验收标准。
3. 接手方按计划执行，可自行决定函数内部实现；不得修改接口签名、测试名称与断言、`Global Constraints`；计划与代码库现状冲突或无法照做时，停止并打回交出方。执行技能要求的自行裁决只适用于上述不可修改项以外的问题；涉及不可修改项的冲突，包括任务审查者提出的，一律停止并打回。

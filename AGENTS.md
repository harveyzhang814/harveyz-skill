# 仓库 Agent 指南

## 仓库与技能来源

本仓库维护 Harvey 的 Agent 技能。技能在 `skills/` 下编写，再安装或发布到不同宿主。`skills/` 是唯一的内容源；只在这里读取和修改技能，不要编辑已安装的副本或宿主的技能目录，因为它们可能落后于仓库。

## 部署与发布

部署时始终从已集成的 `staging` 分支提取技能，不要从当前工作树复制。当前工作树可能处于尚未完成的分支。

```bash
git archive staging skills/<category>/<skill> | tar -x -C <temporary-directory>
rsync -a --exclude '.DS_Store' <temporary-directory>/skills/<category>/<skill>/ <target-skill-root>/<skill>/
```

按安装目标确定 `<target-skill-root>`，不要假定宿主配置目录。部署后核对已安装 `SKILL.md` 的版本是否为目标版本。

技能位于 `skills/<category>/<skill-name>/`，每个目录包含 `SKILL.md`，也可包含 `references/`、脚本、资源和测试。`SKILL.md` 以 YAML frontmatter 开头，包含 `name`、`description`、`user_invocable`、`version` 等字段。

发布技能时，在 `skills-index.json` 中登记 `path` 和 `bundle`；新增 bundle 时补充 `bundleMeta`；技能内容变化时更新 `contentHash` 和 `contentVersion`。`skills-index.json` 是打包依据，未登记的技能不会进入 npm 包。

## 输出格式

- org-mode：粗体用单个星号；标题以 `*` 开头且不跳级。Denote 文件名格式为 `{YYYYMMDDTHHMMSS}--{title}__{type}.org`，保存到 `~/Documents/notes/`。ASCII 图只能使用 ASCII 字符。
- Markdown 报告：可使用 YAML frontmatter 和用户配置的 `skillDir`，不受上述 org-mode 和 Denote 规则约束。

## 测试

运行 `npm test` 验证 hskill CLI 行为及所有 `SKILL.md`。添加测试前先读 [测试指南](docs/reference/testing-guide.md)。

## Git 与工作区

完整规则见 [Git 工作流规范](docs/reference/git-workflow.md)。每组相关改动使用一条 `feature/`、`fix/`、`chore/`、`doc/` 或 `release/` 分支，并从明确的 `staging` 基线创建分支和 worktree；不要隐式使用当前 checkout 作为基线。每个 worktree 都设置 `core.hooksPath=.githooks` 和 `merge.ff=false`。

```bash
git worktree add <worktree-path> -b <type>/<slug> staging
git -C <worktree-path> config core.hooksPath .githooks
git -C <worktree-path> config merge.ff false
```

合并前运行 `git rev-parse --abbrev-ref HEAD` 确认分支。只有用户明确要求“合并”或“完成”时，才从符合条件的工作分支 worktree 运行 `scripts/merge-to-staging.sh`。脚本以本地原子更新和重试方式合并到 `staging`，不会推送 `origin`。不要手动合并到 `main` 或 `staging`，也不要直接向这两个分支提交。

优先使用宿主提供的 worktree 绑定方式；若无法绑定，每条 Git 命令都使用 `git -C <worktree-path>`，文件读写使用绝对路径。单独执行的 `cd` 不会影响后续命令。`.claude/worktrees/` 是本仓库现有的路径约定，包含历史目录，不是必需的宿主 API，也不是通用 worktree 路径。

## 跨会话交接

`handoff` 是通用技能，不依赖 Claude。宿主支持技能调用时调用 `handoff`，否则按技能文档执行；仓库配置见 `.hskill/handoff/config.md`。保留 `author`、`verify`、`self-test`、`accept` 四个阶段。斜杠命令只是部分宿主的调用方式，并非流程要求。

交接使用独立分支和 worktree 时：

1. 交出方创建分支和 worktree，在交接文档中记录绝对路径与分支名，并保留该工作区。
2. 接手方先验证交接，再在同一个 worktree 工作；不另建或删除分支与工作区。
3. 交出方回到同一个 worktree 验收，不在主工作树或集成分支验收。
4. 验收通过后，仅交出方负责合并并移除交接 worktree。

共享的交接 worktree 同一时间只允许一方操作。宿主无法直接进入时，使用上文的显式路径方式。

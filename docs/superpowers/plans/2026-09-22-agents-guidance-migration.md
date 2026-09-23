# AGENTS.md 通用迁移实施计划

**目标：** 在保留 `CLAUDE.md` 的前提下，新增平台中立的根目录 `AGENTS.md`。

**架构：** `AGENTS.md` 独立表达共享仓库规则，使用能力导向的语言描述宿主差异；`CLAUDE.md` 不修改，避免破坏现有 Claude Code 兼容性。`handoff` 保留为通用 skill，其过程与调用界面分离。

**技术栈：** Markdown、Git。

---

### Task 1: 编写平台中立的仓库指南

**文件：**
- 创建: `AGENTS.md`
- 不修改: `CLAUDE.md`

- [ ] **Step 1: 写明权威源与部署边界**

在 `AGENTS.md` 的概述中规定：本仓库 `skills/` 是唯一权威源；安装副本不用于查阅或编辑；部署从 `staging` 的 `git archive` 内容进行；安装器按 target 选择目标目录，不假设 Claude 路径。

- [ ] **Step 2: 写明 skill、索引、输出和测试规则**

加入现有 skill 结构、`SKILL.md` frontmatter、`skills-index.json`、org-mode/Markdown 输出约定、`npm test` 与测试指南的规则，不引入 host 专属术语。

- [ ] **Step 3: 写明通用 Git 和工作区规则**

规定从显式 `staging` 基线创建 worktree 和分支、设置 Git hooks/merge 配置、合并前核验分支、仅在用户要求时合并。将“进入 worktree”描述为 host 能力或 `git -C <worktree>` 和绝对路径回退，明确 `.claude/worktrees/` 仅为仓库路径惯例。

- [ ] **Step 4: 写明通用 handoff 规则**

规定 `handoff` 是通用 skill，读取 `.hskill/handoff/config.md`，保留 author、verify、self-test、accept 的流程。用“调用/执行 skill”代替 slash-command；保留交出方创建并保留工作区、接手和验收共用该工作区的约束。

### Task 2: 静态验证迁移边界

**文件：**
- 验证: `AGENTS.md`
- 验证: `CLAUDE.md`

- [ ] **Step 1: 检查原文档未改动**

运行：`git diff -- CLAUDE.md`

预期：无输出。

- [ ] **Step 2: 检查新文档没有把 Claude API 设为通用前提**

运行：`rg -n 'EnterWorktree|ExitWorktree|(^|[^[:alnum:].-])/handoff([[:space:]]|$)|\.claude/settings\.json' AGENTS.md`

预期：没有匹配；对 `handoff` 的文件路径引用不算 slash-command。若提到 `.claude/worktrees/`，只描述其为路径惯例。

- [ ] **Step 3: 检查 Markdown 和暂存差异**

运行：`git diff --cached --check && git diff -- CLAUDE.md`

预期：没有空白错误，且 `CLAUDE.md` 没有差异。本次变更仅修改指导文档，因此不运行完整项目测试。

- [ ] **Step 4: 审阅最终差异**

运行：`git diff --check && git diff -- AGENTS.md CLAUDE.md`

预期：无空白错误；新增 `AGENTS.md` 及本次规格/计划文档，`CLAUDE.md` 无差异。

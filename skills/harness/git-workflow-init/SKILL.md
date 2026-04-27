---
name: git-workflow-init
description: 初始化 git 分支管理规范：安装分支保护 hooks、生成工作流文档、可选写入 AI 配置文件引用。触发时机：初始化新 git 仓库（git init）、新项目首次配置 git、用户要求设置分支保护或分支规范、安装 git hooks、或问到分支命名规范。只要新项目需要配置 git 工作流，就应使用此 skill。
user_invocable: true
version: "1.0.0"
---

# Git 工作流初始化

为项目自动配置 git 分支治理：安装分支保护钩子，生成工作流规范文档。

## 此 Skill 做的三件事

1. **安装 git hooks** — 通过 `pre-commit` 钩子强制执行分支规则
2. **生成工作流文档** — 将模板写入 `docs/reference/git-workflow.md`
3. **更新 AI 配置文件（可选）** — 在 `CLAUDE.md`、`AGENTS.md`、`GEMINI.md` 中添加对工作流文档的索引引用

## 分支保护规则（安装后生效）

| 分支 | 直接提交 | 允许的合并来源 |
|------|---------|-------------|
| `main` | 禁止 | `staging`、`release/*` |
| `staging` | 禁止 | `feature/*`、`fix/*`、`chore/*`、`doc/*` |
| 其他分支 | 允许 | — |

---

## 执行步骤

### Step 1 — 确认 git 仓库

```bash
git rev-parse --show-toplevel
```

若不在 git 仓库中，询问用户是否先执行 `git init`。

### Step 2 — 安装 git hooks

从此 skill 的 `references/` 目录找到安装脚本并执行：

```bash
SCRIPT=$(find ~/.claude -path "*/git-workflow-init/references/install-git-hooks.sh" 2>/dev/null | head -1)
bash "$SCRIPT"
```

脚本会在 `.githooks/pre-commit` 安装钩子，并设置 `core.hooksPath = .githooks`。

> 若找不到脚本，直接读取此 skill 的 `references/install-git-hooks.sh` 并写入临时文件再运行。

### Step 3 — 写入工作流文档

1. 若 `docs/reference/` 目录不存在，逐层创建
2. 读取此 skill 的 `references/git-workflow-template.md`
3. 将内容写入项目根目录的 `docs/reference/git-workflow.md`
4. 若 `docs/INDEX.md` 已存在，在对应分类中追加一行索引

### Step 4 — 更新 AI 配置文件（可选）

询问用户："是否在项目的 AI 配置文件（CLAUDE.md、AGENTS.md、GEMINI.md）中添加对 git 工作流文档的引用？"

若用户同意，对**已存在**的配置文件追加以下内容（不存在的文件不主动创建）：

```markdown
## Git 工作流

分支命名规范、保护规则与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。
```

注意：只写索引引用，不把完整规范内容写入配置文件。

### Step 5 — 汇报结果

简要列出完成项：
- Git hooks 已安装（`.githooks/pre-commit`，`core.hooksPath = .githooks`）
- 工作流文档已生成（`docs/reference/git-workflow.md`）
- 已更新的 AI 配置文件（若有）

---

## 参考文件

| 文件 | 说明 |
|------|------|
| `references/install-git-hooks.sh` | 分支保护 hook 安装脚本 |
| `references/git-workflow-template.md` | 写入目标项目的工作流文档模板 |

---
name: harvey-superpowers-using-git-worktrees
description: "当需要创建隔离工作区（新分支）进行特性开发时使用。在执行实施计划或开始任何需要与当前工作隔离的任务前，必须先创建 worktree、运行项目设置、验证干净的测试基线。适用于：开始新功能开发、修复 bug、需要隔离环境的任何代码工作。"
user_invocable: true
version: "1.0.0"
---

# Using Git Worktrees - 隔离工作区

## 概述

Git worktree 创建共享同一仓库的隔离工作空间，允许同时在多个分支上工作而无需切换。

**核心原则：** 系统化的目录选择 + 安全验证 = 可靠的隔离。

**开始时宣布：** "正在使用 using-git-worktrees 技能设置隔离工作区。"

## 目录选择优先级

### 1. 检查现有目录

```bash
# 按优先级检查
ls -d .worktrees 2>/dev/null     # 首选（隐藏目录）
ls -d worktrees 2>/dev/null      # 备选
```

**如果存在：** 使用该目录（两个都存在时 `.worktrees` 优先）

### 2. 检查 CLAUDE.md

```bash
grep -i "worktree.*director" CLAUDE.md 2>/dev/null
```

**如果指定了偏好：** 直接使用，不询问

### 3. 询问用户

如果无目录且无 CLAUDE.md 偏好：

```
未找到 worktree 目录。应该在哪里创建？

1. .worktrees/ (项目本地，隐藏)
2. ~/worktrees/<项目名>/ (全局位置)

选择哪个？
```

## 安全验证

### 本地目录（.worktrees 或 worktrees）

**创建前必须验证目录被忽略：**

```bash
# 检查目录是否被忽略（遵守本地、全局和系统 .gitignore）
git check-ignore -q .worktrees 2>/dev/null || git check-ignore -q worktrees 2>/dev/null
```

**如果不未忽略：** Jesse 规则"立即修复损坏的东西"：
1. 添加适当的行到 .gitignore
2. 提交更改
3. 继续创建 worktree

### 全局目录（~/.config/openclaw/worktrees/）

无需 .gitignore 验证 — 完全在项目外。

## 创建步骤

### 1. 检测项目名称

```bash
project=$(basename "$(git rev-parse --show-toplevel)")
```

### 2. 创建 Worktree

```bash
# 确定完整路径
case $LOCATION in
  .worktrees|worktrees)
    path="$LOCATION/$BRANCH_NAME"
    ;;
  ~/.config/openclaw/worktrees/*)
    path="$HOME/.config/openclaw/worktrees/$project/$BRANCH_NAME"
    ;;
esac

# 创建 worktree（带新分支）
git worktree add "$path" -b "$BRANCH_NAME"
cd "$path"
```

### 3. 运行项目设置

自动检测并运行适当的设置：

```bash
# Node.js
if [ -f package.json ]; then npm install; fi

# Python
if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
if [ -f pyproject.toml ]; then poetry install; fi

# Rust
if [ -f Cargo.toml ]; then cargo build; fi

# Go
if [ -f go.mod ]; then go mod download; fi
```

### 4. 验证干净基线

运行测试确保 worktree 起始干净：

```bash
# 示例（使用项目适当的命令）
npm test
cargo test
pytest
go test ./...
```

**如果测试失败：** 报告失败，询问是否继续或调查。

**如果测试通过：** 报告就绪。

### 5. 报告位置

```
Worktree 就绪于 <full-path>
测试通过 (<N> 测试，0 失败)
准备好实现 <feature-name>
```

## 快速参考

| 情况 | 操作 |
|------|------|
| `.worktrees/` 存在 | 使用它（验证被忽略） |
| `worktrees/` 存在 | 使用它（验证被忽略） |
| 两者都存在 | 使用 `.worktrees/` |
| 都不存在 | 检查 CLAUDE.md → 询问用户 |
| 目录未忽略 | 添加到 .gitignore + 提交 |
| 基线测试失败 | 报告失败 + 询问 |
| 无 package.json 等 | 跳过依赖安装 |

## 常见错误

### 跳过忽略验证

- **问题：** Worktree 内容被跟踪，污染 git status
- **修复：** 创建本地 worktree 前始终使用 `git check-ignore`

### 假设目录位置

- **问题：** 创建不一致，违反项目约定
- **修复：** 遵循优先级：现有 > CLAUDE.md > 询问

### 测试失败继续

- **问题：** 无法区分新 bug 和已存在问题
- **修复：** 报告失败，获得明确许可后再继续

### 硬编码设置命令

- **问题：** 在使用不同工具的项目上失败
- **修复：** 从项目文件自动检测（package.json 等）

## 与其他技能配合

**被调用方：**
- **brainstorming**（第4阶段）— 设计批准后实施前必需
- **executing-plans** — 执行任何任务前必需
- 任何需要隔离工作区的技能

**配合技能：**
- **finishing-a-development-branch** — 工作完成后清理
- **writing-plans** — 创建实施计划
- **brainstorming** — 设计阶段

## OpenClaw 环境适配

在 OpenClaw 环境中：
- 工作区路径：`~/.openclaw/agents/coding-master/workspace/`
- 计划保存到：`docs/superpowers/plans/`
- 规格保存到：`docs/superpowers/specs/`
- Worktree 创建后，在新目录中继续执行 writing-plans 和 executing-plans

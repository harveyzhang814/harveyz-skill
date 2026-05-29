---
migrated: 2026-05-29
docs:
  - explanation/hskill-architecture.md
  - reference/agent-cli-guide.md
---

# Skill Installer CLI 设计文档

## 概述

将本仓库发布为 npm 包，提供 `npx harveyz-skill` 命令，让用户通过交互式 bundle 选择一键安装 skill 到 Claude Code / Cursor / Codex。

## 背景

本仓库的 skill 需要分发给他人使用。目标用户以开发者为主，但也有非技术用户。需要低门槛、跨平台的安装方式。选定 npm 包方案：零额外依赖（Node 已是开发者标配），`npx` 无需全局安装，bundle 更新只需 `npm publish`。

## 用户故事

1. 开发者运行 `npx harveyz-skill`，通过 checkbox UI 选择 bundle 和目标工具，skill 被复制到对应目录。
2. 开发者运行 `npx harveyz-skill --bundle writing --target claude` 完成无交互自动化安装（CI / dotfiles 场景）。
3. 用户运行 `npx harveyz-skill list` 查看所有可用 bundle 及包含的 skill。

## 架构设计

### 包结构

```
harveyz-skill/
├── bin/
│   └── cli.js          # npx 入口，解析参数，调用 installer
├── lib/
│   ├── installer.js    # 核心安装逻辑（复制目录、冲突处理）
│   ├── bundles.js      # 读取 bundles.json，解析 skill 路径
│   └── targets.js      # target → 绝对路径映射
├── bundles.json        # bundle 定义
├── skills/             # 所有 skill 目录（直接打包）
└── package.json
```

### 命令接口

```bash
npx harveyz-skill                              # 交互模式
npx harveyz-skill --bundle <name> --target <tool>  # 无交互模式
npx harveyz-skill list                         # 列出所有 bundle
npx harveyz-skill --force                      # 覆盖已存在的 skill（跳过询问）
```

### bundles.json 格式

```json
[
  {
    "name": "writing",
    "description": "写作 & 文档工具",
    "skills": ["superpowers-fork/brainstorming", "superpowers-fork/writing-plans"]
  },
  {
    "name": "dev",
    "description": "开发工作流",
    "skills": ["superpowers-fork/executing-plans", "superpowers-fork/systematic-debugging"]
  }
]
```

`skills` 数组中每项为相对于 `skills/` 目录的路径。

### Target 路径映射

| Target | 安装路径 |
|--------|---------|
| `claude` | `~/.claude/skills/` |
| `cursor` | `~/.cursor/skills/` |
| `codex` | `~/.codex/skills/` |
| `all` | 以上全部 |

目录不存在时跳过并提示（不报错退出）。

## 数据流

```
用户运行 npx harveyz-skill
  → cli.js 解析参数
  → 无参数：inquirer 展示 bundle checkbox + target checkbox
  → 有参数：直接读取 --bundle / --target
  → bundles.js 解析选中 bundle → skill 路径列表
  → targets.js 解析选中 target → 绝对安装路径列表
  → installer.js 遍历 (skill × target)：
      - 目标已存在且无 --force → inquirer 询问是否覆盖
      - 复制 skills/<skill_path>/ → <target_path>/<skill_name>/
  → chalk 输出安装摘要
```

## 交互 UI 流程

```
$ npx harveyz-skill

? 选择要安装的 bundle（空格多选）:
  ◯ writing   — 写作 & 文档工具
  ◯ dev       — 开发工作流
❯ ◯ all       — 全部 skill

? 安装到哪些工具（空格多选）:
  ◯ claude    (~/.claude/skills/)
❯ ◯ cursor    (~/.cursor/skills/)
  ◯ codex     (~/.codex/skills/)

✔ 安装完成：
  claude  ← brainstorming, writing-plans
  cursor  ← brainstorming, writing-plans
  已跳过（目录不存在）: codex
```

## 依赖

| 包 | 用途 |
|----|------|
| `inquirer` | checkbox 交互 UI |
| `chalk` | 彩色终端输出 |
| `fs-extra` | 递归目录复制 |

## package.json 关键配置

```json
{
  "name": "harveyz-skill",
  "version": "1.0.0",
  "bin": { "harveyz-skill": "./bin/cli.js" },
  "files": ["bin/", "lib/", "skills/", "bundles.json"],
  "engines": { "node": ">=18" }
}
```

`files` 字段排除 `docs/`、`.worktrees/`、`scripts/` 等开发目录。

## 错误处理

- 用户未选择任何 bundle → 提示并退出（exit code 1）
- 用户未选择任何 target → 提示并退出（exit code 1）
- target 目录不存在 → 跳过，输出警告，继续其他 target
- skill 源目录不存在（bundles.json 配置错误）→ 报错并跳过该 skill

## 发布流程

```bash
npm version patch   # skill 内容变更
npm version minor   # 新增 bundle
npm version major   # CLI 接口变更
npm publish
```

## 测试策略

- 单元测试：`bundles.js` 路径解析、`targets.js` 路径展开
- 集成测试：指定临时目录为 target，验证文件是否正确复制
- 手动验证：`npx harveyz-skill list` 输出正确；交互流程可走通

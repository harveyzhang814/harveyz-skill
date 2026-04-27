# Harvey Skills

Harvey 的个人 Claude Code 技能仓库。

## 技能清单

| 技能 | 说明 | 外部依赖 |
|------|------|---------|
| **harvey-plain** | 白话引擎 — 把任何内容改写到聪明的十二岁小孩也能懂 | 无 |
| **skill-analyzer** | 系统化分析 Skill 仓库的框架，基于洋葱模型四层结构 | 无 |

> 更多技能陆续添加中。

## 安装

### 推荐：npx 一键安装

```bash
npx harveyz-skill
```

交互式选择 bundle 和目标工具（Claude Code / Cursor / Codex）。

**无交互模式：**
```bash
npx harveyz-skill --bundle brainstorming --target claude
npx harveyz-skill --bundle brainstorming,dev --target all
```

**查看可用 bundle：**
```bash
npx harveyz-skill list
```

### 手动安装（从源码）

```bash
mkdir -p ~/.claude/skills
cp -r skills/* ~/.claude/skills/
```

## 工作流

```
harvey-plain: 内容 → org-mode 文件（~/Documents/notes/）
```

## Skill 开发指南

### 命名规范

- 前缀：`harvey-`（例：`harvey-plain`、`harvey-card`）
- 每个 skill 独立目录，`SKILL.md` 是唯一入口

### SKILL.md 格式

```yaml
---
name: skill-name
description: "做什么。触发词..."
user_invocable: true
version: "x.x.x"
---
```

### 共享规范

**Org-mode 输出：**
- 加粗：`*text*`（单星号）
- 文件名：`{时间戳}--{标题}__{type}.org`
- 输出目录：`~/Documents/notes/`
- 时间戳：`date +%Y%m%dT%H%M%S`

**ASCII Art：**
- 允许：`+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "`
- 禁止：Unicode 绘图符号

## 许可证

Private — 仅供个人使用。

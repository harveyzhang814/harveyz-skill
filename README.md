# Harvey Skills

Harvey 的个人 Claude Code 技能仓库。

## 技能清单

按 bundle 分组，`npx harveyz-skill --bundle <bundle>` 安装对应分组。

### analysis — 分析工具

| 技能 | 说明 |
|------|------|
| **skill-analyzer** | 系统化分析 Skill 仓库的框架，基于洋葱模型四层结构 |

### brainstorming — 设计与规划工具

| 技能 | 说明 |
|------|------|
| **brainstorming** | 设计前强制探索阶段 — 在实现任何功能前，先理解意图、需求和设计方案（HARD-GATE） |
| **writing-plans** | 将设计拆解为可执行的小任务（2–5 分钟/任务），含精确文件路径和验证步骤 |

### dev — 开发工作流

| 技能 | 说明 |
|------|------|
| **git-workflow-init** | 初始化或更新 git 分支管理规范，差量部署 git hooks，生成工作流文档 |
| **executing-plans** | 执行书面实施计划，含两阶段 review（规格合规性 → 代码质量） |
| **systematic-debugging** | 系统化 debug — 必须先找到根本原因，再提修复方案 |
| **using-git-worktrees** | 创建隔离 worktree 进行特性开发，验证干净的测试基线后再开始 |

### document — 文档工具

| 技能 | 说明 |
|------|------|
| **diataxis-docs** | 管理 `docs/` 目录 — 遵循 Diátaxis 方法论，写新文档、更新或删除时触发 |

### harness — 测试工具

| 技能 | 说明 |
|------|------|
| **full-stack-debug-env** | 多组件应用全栈日志监控环境搭建 — 为前端、后端、worker 等各层建立独立日志文件 |

### task — 任务管理

| 技能 | 说明 |
|------|------|
| **pm-task-dispatch** | PM 任务派发 — 需求澄清 → 分析细化 → 创建任务文档 → 派发给 Agent → 追踪反馈 |
| **task-close** | 任务收尾 — Agent 完成任务后执行验收、总结、文档归档和问题记录 |

### web-fetch — 网页抓取

| 技能 | 说明 |
|------|------|
| **article-fetcher** | 抓取 URL → 翻译为中文 → 存入 Obsidian；支持 X.com / Twitter（Playwright + Chrome Profile） |

### writing — 写作工具

| 技能 | 说明 |
|------|------|
| **mermaid-diagram** | Mermaid 专业作图 — 图类型选择、Roland Berger 配色、语法禁区、渲染前 12 项检查清单 |

---

## 工具清单

Shell 工具，通过 `npx harveyz-skill --bundle shell-tools` 安装。

| 工具 | 说明 |
|------|------|
| **p-launch** | 交互式项目启动器 — 从多个目录中快速选择并跳转到项目 |

---


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

## Skill 开发指南

### 命名规范

- Flat skill：直接放 `skills/<category>/<skill-name>/SKILL.md`
- Skill group：`skills/<group>/` 下多个子目录，每个含 `SKILL.md`

### SKILL.md 格式

```yaml
---
name: skill-name
description: "做什么。触发词..."
user_invocable: true
version: "x.x.x"
---
```

### 发布流程

1. 在 `skills/<category>/<skill-name>/` 下创建 `SKILL.md`
2. 在 `skills-index.json` 的 `skills[]` 中添加条目，指定 `path` 和 `bundle`
3. 运行 `node scripts/generate-npmignore.js`（`prepack` 钩子会自动执行）

### 共享输出规范

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

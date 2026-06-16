# harveyz-skill

Harvey 的个人 Claude Code / Cursor / Codex 技能管理器，当前版本 **v0.6.2**。

通过 `hskill` 命令将技能安装到 `~/.claude/skills/`，按 bundle 分组管理。

---

## 技能清单

按 bundle 分组，用 `hskill install --bundle <bundle>` 安装对应分组，或用 `hskill install --skill <name>` 安装单个技能。

### analysis — 分析工具

| 技能 | 说明 |
|------|------|
| **skill-analyzer** | 对 Skill 仓库进行系统性分析，基于洋葱模型四层结构输出分析报告 |

### brainstorming — 设计与规划工具

| 技能 | 说明 |
|------|------|
| **brainstorming** | 实现前强制探索阶段（HARD-GATE）— 在创建功能、修改代码前，先理解意图、需求和设计方案 |
| **writing-plans** | 将设计拆解为可执行的小任务（2–5 分钟/任务），含精确文件路径、完整代码和验证步骤 |

### dev — 开发工作流

| 技能 | 说明 |
|------|------|
| **git-workflow-init** | 初始化或更新 git 分支管理规范：读取 `workflow-config.yml`，差量部署 git hooks，生成工作流文档 |
| **executing-plans** | 执行书面实施计划，含两阶段 review（规格合规性 → 代码质量），需先通过 `using-git-worktrees` 建立隔离工作区 |
| **systematic-debugging** | 系统化 debug — 禁止在未完成根本原因调查前提出修复方案 |
| **using-git-worktrees** | 创建隔离 worktree 进行特性开发，验证干净测试基线后再开始 |

### document — 文档工具

| 技能 | 说明 |
|------|------|
| **diataxis-docs** | 管理 `docs/` 目录 — 遵循 Diátaxis 方法论，写新文档、更新或删除时触发，可防止内容重复 |

### harness — 测试工具

| 技能 | 说明 |
|------|------|
| **full-stack-debug-env** | 多组件应用全栈日志监控环境 — 为前端、后端、worker 等各层建立独立日志文件，供 Agent 精确查询 |

### task — 任务管理

| 技能 | 说明 |
|------|------|
| **pm-task-dispatch** | PM 任务派发 — 需求澄清 → 分析细化 → 创建任务文档 → 派发给 Agent → 追踪反馈 |
| **task-close** | 任务收尾 — Agent 完成任务后执行验收、总结、文档归档和问题记录 |

### web-fetch — 网页抓取

| 技能 | 说明 |
|------|------|
| **article-fetcher** | 抓取 URL → 翻译为中文 → 存入 Obsidian；支持 X.com / Twitter（Playwright + Chrome Profile），支持批量列表 |

### writing — 写作工具

| 技能 | 说明 |
|------|------|
| **mermaid-diagram** | Mermaid 专业作图 — 图类型选择、Roland Berger 配色、语法禁区、渲染前 12 项检查清单 |

---

## 工具清单

Shell 工具，安装到 `~/.local/bin/`。

| 工具 | Bundle | 说明 |
|------|--------|------|
| **hub** | tools | 开发者 OS — 项目管理 + git 状态 + 任务跟踪 |

```bash
hskill install --tool hub
```

---

## 安装

**推荐：全局安装**

```bash
npm install -g harveyz-skill
hskill                          # 交互式选择安装
```

**常用命令**

```bash
hskill                                          # 交互式选择
hskill install --bundle dev                     # 安装整个 bundle
hskill install --skill git-workflow-init        # 安装单个 skill
hskill install --tool hub                       # 安装 shell 工具
hskill list                                     # 查看可用 skill
hskill update                                   # 更新到最新版
hskill --help                                   # 查看帮助
```

Skills 安装到 `~/.claude/skills/`，shell 工具安装到 `~/.local/bin/`。

**本地源码开发**

```bash
node bin/cli.js install --skill mermaid-diagram --target claude
node bin/cli.js install --bundle dev --target claude
node bin/cli.js install --skill mermaid-diagram --target claude --force   # 覆盖已有安装
```

**Git 保护钩子（可选）**

```bash
bash scripts/git/install-git-hooks.sh
```

钩子会阻止直接向 `main` 和 `staging` 提交 — 使用 feature/fix/chore/doc 分支，通过 staging 合并。

---

## Hook 管理

hskill 支持通过 `hooks` 命令管理 Claude Code hooks。查看可用 hooks、在全局或项目作用域安装/卸载：

```bash
hskill hooks list                                              # 查看可用 hooks 及安装状态
hskill hooks install --name check-similar-branch               # 安装到全局（user scope）
hskill hooks install --name check-similar-branch --scope project  # 安装到当前项目
hskill hooks uninstall check-similar-branch                    # 从全局卸载
hskill hooks uninstall check-similar-branch --scope project    # 从当前项目卸载
```

---

## Skill 开发指南

### 目录结构

```
skills/
  <category>/
    <skill-name>/
      SKILL.md          # 技能定义（必须）
      references/       # 参考资料（可选）
```

两种模式：
- **Flat skill** — 单个 `SKILL.md`，如 `skills/writing/mermaid-diagram/`
- **Skill group** — 同一分类下多个子目录，每个含 `SKILL.md`

### SKILL.md 格式

```yaml
---
name: skill-name
description: "做什么。触发词：..."
user_invocable: true
version: "x.x.x"
---
```

### 发布新技能

1. 在 `skills/<category>/<skill-name>/` 下创建 `SKILL.md`
2. 在 `skills-index.json` 的 `skills[]` 中添加条目，指定 `path` 和 `bundle`
3. 若 bundle 是新的，在 `bundleMeta` 中添加描述
4. 运行 `node scripts/generate-npmignore.js`（`prepack` 钩子会自动执行）

`skills-index.json` 是唯一数据源，不在其中的技能不会被打包发布。

### 共享输出规范

**Org-mode 输出：**
- 加粗：`*text*`（单星号）
- 文件名：`{YYYYMMDDTHHMMSS}--{标题}__{type}.org`
- 输出目录：`~/Documents/notes/`

**ASCII Art：**
- 允许：`+ - | / \ > < v ^ * = ~ . : # [ ] ( ) _ , ; ! ' "`
- 禁止：Unicode 绘图符号

### Git 工作流

分支命名规范与合并流程详见 [docs/reference/git-workflow.md](docs/reference/git-workflow.md)。

一个功能或迭代使用一个分支，积累所有相关改动，只在明确"合并"或"完成"时才合并到 staging。

---

## 许可证

MIT

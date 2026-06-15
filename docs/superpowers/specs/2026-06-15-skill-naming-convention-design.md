---
title: Skill 命名规范设计
date: 2026-06-15
status: approved
migrated: false
---

# Skill 命名规范设计

## 背景

仓库现有 25 个 skill，命名风格混乱：动词/名词顺序不一致、工具平台名直接入名、单词数差距悬殊（1～4 词）。本规范统一命名风格，并通过 `hskill update` 自动迁移已安装的旧名称。

---

## Section 1 — 命名规则

### 基本格式

```
<动词>-<名词>
```

- 固定 2 词，全小写，连字符分隔
- **必须以动词开头**
- **名词不得使用工具/平台专有名**（youtube、npm、diataxis 等）

### 规范动词词表

新 skill 命名时**优先复用已有动词**；确有必要时可扩展，但需更新此表。

| 动词 | 含义 |
|---|---|
| `extract` | 从来源提取结构化数据 |
| `learn` | 处理教学/视频内容 |
| `forge` | 生成文档产物 |
| `draw` | 创建可视化图表 |
| `manage` | 在目录/系统内组织文件 |
| `migrate` | 跨格式/位置转换数据 |
| `scout` | 调查外部来源获取信息 |
| `build` | 构建配置或制品 |
| `sync` | 保持两端同步 |
| `publish` | 推送到外部注册表 |
| `archive` | 移至归档/退役状态 |
| `contribute` | 将外部内容引入本仓库 |
| `analyze` | 深度检查/分析 |
| `clean` | 清理废弃项 |
| `release` | 创建版本发布 |
| `validate` | 验证/校验 |
| `init` | 初始化新配置 |
| `dispatch` | 派发任务给其他 agent |
| `close` | 收尾/完成任务 |
| `setup` | 准备环境 |
| `capture` | 记录想法/洞察 |
| `runby` | 委托给指定外部工具执行（特殊前缀，后接工具名） |

### 特殊模式：`runby-<tool>`

当 skill 的核心功能是"委托某个特定外部工具执行某件事"时，允许使用 `runby-<tool>` 格式（`tool` 为外部工具名）。这是唯一允许工具名入名的模式。

示例：`runby-opencode`（通过 opencode 验证 skill 逻辑）

---

## Section 2 — 现有 Skill 重命名映射

完整映射表，供 `hskill update` 迁移脚本使用。

| 现名 | 新名 | bundle | 变化说明 |
|---|---|---|---|
| `url-extract` | `extract-url` | research | 动词前移 |
| `vision-extract` | `extract-vision` | research | 动词前移 |
| `youtube-learner` | `learn-video` | research | 去工具名 + 动词前移 |
| `add-todo` | `capture-todo` | creative | 统一用 `capture` 动词 |
| `insight` | `capture-insight` | creative | 从单词扩展为 2 词 |
| `git-workflow-init` | `init-workflow` | coding | 动词前移，去领域前缀 |
| `full-stack-debug-env` | `setup-debug` | coding | 缩短 + 动词前移 |
| `pm-task-dispatch` | `dispatch-task` | coding | 动词前移，去 PM 前缀 |
| `task-close` | `close-task` | coding | 动词前移 |
| `doc-forge` | `forge-doc` | writing | 动词前移 |
| `diagram` | `draw-diagram` | writing | 从单词扩展为 2 词 |
| `diataxis-docs` | `manage-docs` | writing | 去方法论名 + 动词前移 |
| `dir-manage` | `manage-dir` | writing | 动词前移 |
| `migrate-specs` | `migrate-spec` | writing | 名词改单数 |
| `brand-scout` | `scout-brand` | design | 动词前移 |
| `style-build` | `build-style` | design | 动词前移 |
| `sync-design-html` | `sync-design` | design | 去工具后缀 |
| `archive-skill` | `archive-skill` | meta | ✓ 不变（已符合规范） |
| `contribute-skill` | `contribute-skill` | meta | ✓ 不变（已符合规范） |
| `git-cleanup` | `clean-git` | meta | 动词前移 |
| `skill-analyzer` | `analyze-skill` | meta | 动词前移 |
| `skill-publish` | `publish-skill` | meta | 动词前移 |
| `opencode-runner` | `runby-opencode` | meta | 使用 `runby-` 特殊模式 |
| `npm-release` | `npm-release` | meta | ✓ 不变（将在未来归档） |
| `project-release` | `release-project` | meta | 动词前移 |

**说明：**
- `npm-release` 专属本仓库 npm 发布流程，计划未来归档，暂保留原名。
- `archive-skill`、`contribute-skill` 已符合动词-名词格式，无需改动。

---

## Section 3 — 迁移机制

### 触发方式

**`hskill update`** — 更新 npm 包后运行此命令，自动迁移所有已安装的旧名称 skill。

### 配置

在 `skills-index.json` 顶层增加 `renames` 字段：

```json
{
  "renames": [
    { "from": "url-extract",          "to": "extract-url" },
    { "from": "vision-extract",       "to": "extract-vision" },
    { "from": "youtube-learner",      "to": "learn-video" },
    { "from": "add-todo",             "to": "capture-todo" },
    { "from": "insight",              "to": "capture-insight" },
    { "from": "git-workflow-init",    "to": "init-workflow" },
    { "from": "full-stack-debug-env", "to": "setup-debug" },
    { "from": "pm-task-dispatch",     "to": "dispatch-task" },
    { "from": "task-close",           "to": "close-task" },
    { "from": "doc-forge",            "to": "forge-doc" },
    { "from": "diagram",              "to": "draw-diagram" },
    { "from": "diataxis-docs",        "to": "manage-docs" },
    { "from": "dir-manage",           "to": "manage-dir" },
    { "from": "migrate-specs",        "to": "migrate-spec" },
    { "from": "brand-scout",          "to": "scout-brand" },
    { "from": "style-build",          "to": "build-style" },
    { "from": "sync-design-html",     "to": "sync-design" },
    { "from": "git-cleanup",          "to": "clean-git" },
    { "from": "skill-analyzer",       "to": "analyze-skill" },
    { "from": "skill-publish",        "to": "publish-skill" },
    { "from": "opencode-runner",      "to": "runby-opencode" },
    { "from": "project-release",      "to": "release-project" }
  ]
}
```

### 扫描范围

迁移脚本复用 `lib/targets.js` 中的 `SKILL_TARGETS` + `userSkillDir()` 逻辑，覆盖所有用户级目标平台：

| 平台 | 路径 |
|---|---|
| claude | `~/.claude/skills/` |
| cursor | `~/.cursor/skills/` |
| codex | `~/.codex/skills/` |
| openclaw | `~/.openclaw/skills/` |
| hermes | `~/.hermes/skills/` |
| opencode | `~/.config/opencode/skills/` |

### 执行逻辑

```
读取 skills-index.json 中的 renames[]
→ 遍历 SKILL_TARGETS，对每个 target：
   → 若 userSkillDir(target) 存在：
      → 对每个 { from, to }：
         → 若 <from>/ 存在 → 删除旧目录，安装 <to>/
→ 打印迁移报告
```

### 输出示例

```
harveyz-skill v2.x.x
Migrating renamed skills...
  claude:   ✓ url-extract → extract-url  ✓ youtube-learner → learn-video  ... (22 total)
  codex:    ✓ url-extract → extract-url  ... (5 total)
  cursor:   (not installed, skipped)
Migration complete.
```

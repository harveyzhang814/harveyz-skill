---
migrated: 2026-05-29
docs:
  - reference/agent-cli-guide.md       # info 子命令：TTY 输出格式（skill/tool/hook）、--json 输出格式、类型自动识别顺序、错误消息
implemented_in:
  - bin/cli.js      # info 子命令分支（subcommand === 'info'）
  - lib/bundles.js  # getAllSkillItems / getAllToolItems / checkInstalled / checkToolInstalled
---

# hskill info 子命令设计

**日期:** 2026-05-29
**状态:** 已批准

## 背景

`hskill status` 展示所有已安装 item 的全局视图，但用户经常只想查某一个 skill 或 tool 的详情：版本、安装路径、user/project 各端的状态。目前没有单独查询单个 item 的命令。

## 目标

新增 `hskill info <name>` 子命令，支持查询单个 skill / tool / hook 的详细安装信息。

## 命令接口

```bash
hskill info <name>             # 自动识别类型（skill / tool / hook）
hskill info <name> --json      # 机器可读输出
```

## 输出格式

### 人读格式（TTY）

**Skill 示例：**

```
skill-analyzer  v1.0.0  [analysis bundle]

  USER SCOPE
    claude    ✓  v1.0.0  ~/.claude/skills/skill-analyzer/
    cursor    —
    codex     —

  PROJECT SCOPE
    claude    ✓  v0.9.0  (outdated)  ./.claude/skills/skill-analyzer/
```

**Tool 示例：**

```
p-launch  v3.0.0

  INSTALLED    ~/.local/bin/p-launch
  STATUS       up-to-date
```

**Hook 示例：**

```
check-similar-branch  v1.0.0

  USER      ✓  installed  ~/.claude/hooks/check-similar-branch.sh
  PROJECT   —  none
```

### JSON 格式（--json）

```json
{
  "name": "skill-analyzer",
  "type": "skill",
  "version": "1.0.0",
  "user": {
    "claude":   { "status": "up-to-date", "version": "1.0.0", "path": "~/.claude/skills/skill-analyzer/" },
    "cursor":   { "status": "none" },
    "codex":    { "status": "none" }
  },
  "project": {
    "claude":   { "status": "outdated", "version": "0.9.0", "path": "./.claude/skills/skill-analyzer/" }
  }
}
```

Tool 的 `type` 为 `"tool"`，无 scope 分层，直接返回 `installed`、`status`、`path`。

Hook 的 `type` 为 `"hook"`，结构与 skill 相同但只有 `user` 和 `project` 两个 scope，无 target 维度。

## 类型自动识别

`hskill info <name>` 按以下顺序查找：

1. `skills-index.json` 的 `skills[]` 中是否有匹配的 `path` 末尾或 `name`
2. `skills-index.json` 的 `tools[]` 中是否有匹配的 `name`
3. `skills-index.json` 的 `hooks[]` 中是否有匹配的 `name`

找不到则报错：`Unknown item: "<name>". Run 'hskill list' to see available items.`

## 代码变动范围

| 文件 | 变动 |
|------|------|
| `bin/cli.js` | 新增 `info` 子命令分支 |
| `lib/bundles.js` | 新增 `getItemInfo(name)` 导出函数 |

`getItemInfo(name)` 内部：
1. 在 skills-index.json 中定位 item 类型
2. 对每个 scope × target 组合调用现有的 `checkSkillInstalled` / `checkToolInstalled` / `checkHookInstalled`
3. 聚合返回统一结构

## 不在范围内

- `hskill info --all`（已有 `hskill status`）
- 展示 changelog 或 diff（独立功能）

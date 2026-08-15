# hskill Agent CLI Guide

Reference for AI agents and CI scripts calling `hskill` non-interactively.

---

## Quick rules

| Rule | Detail |
|------|--------|
| Always pass `--json` | Machine-readable output; errors route to stderr as JSON |
| Never omit `--skill`/`--tool`/`--bundle` | No-flag mode launches an interactive fzf picker and blocks forever in non-TTY |
| Always pass `--target` | Avoids a fzf target-selector that also blocks in non-TTY |
| `--skill` and `--tool` are mutually exclusive | Use `--bundle` if a bundle contains both |
| Set `NO_COLOR=1` if you parse stderr | Strips ANSI codes from status messages |
| stdout = data, stderr = logs | Only parse stdout; stderr is human-readable progress (or JSON errors in `--json` mode) |

---

## Self-discovery

Before hard-coding flags, fetch the live schema:

```bash
hskill --help --json
```

Returns a single JSON object:

```json
{
  "name": "hskill",
  "version": "0.6.2",
  "description": "...",
  "agent_notes": "Interactive mode requires TTY. Use --json for machine-readable output...",
  "commands": [
    {
      "name": "install",
      "note": "--skill and --tool are mutually exclusive; use --bundle to install both",
      "flags": [
        { "name": "--skill",  "arg": "<name>",   "description": "..." },
        { "name": "--target", "arg": "<target>",  "enum": ["claude","cursor","codex","openclaw","hermes","all"] },
        { "name": "--scope",  "arg": "<scope>",   "enum": ["user","project"], "default": "user" },
        ...
      ]
    },
    ...
  ]
}
```

---

## Read-only queries

These commands never prompt and always exit 0 (unless the tool itself is broken).

### `status --json`

```bash
hskill status --json
```

```json
{
  "skills": [
    { "name": "skill-analyzer", "version": "1.0.0", "user": "none", "project": "none" }
  ],
  "tools": [
    { "name": "p-launch", "version": "1.2.0", "status": "up-to-date" }
  ],
  "hooks": [
    { "name": "check-similar-branch", "version": "1.0.0", "user": "up-to-date", "project": "none" }
  ]
}
```

`user` / `project` values: `"none"` | `"up-to-date"` | `"update"` | `"partial"`

### `outdated --json`

```bash
hskill outdated --json
```

Same shape as `status --json` but only includes entries with `"update"` status. Returns `{ "skills": [], "tools": [] }` when everything is current.

### `list --json`

```bash
hskill list --json
```

```json
{
  "bundles": {
    "analysis": {
      "description": "分析工具（skill-analyzer）",
      "skills": ["analysis/skill-analyzer"]
    }
  },
  "tools": ["p-launch"],
  "hooks": ["check-similar-branch"]
}
```

---

## Bundle management

### `bundle list`

```bash
hskill bundle list [--json]
```

列出所有 bundle 及其包含的 skill。

**TTY 输出：**

```
BUNDLE        SKILLS  DESCRIPTION
────────────────────────────────────────────────────────
analysis      2       分析工具（skill-analyzer + git-cleanup）
brainstorming 2       设计与规划工具
meta          2       元操作工具（对 harveyz-skill 仓库本身的管理）
```

**`--json` 输出：**

```json
{
  "bundles": {
    "analysis": {
      "description": "分析工具（skill-analyzer + git-cleanup）",
      "skills": ["analysis/skill-analyzer", "analysis/git-cleanup"]
    },
    "meta": {
      "description": "元操作工具（对 harveyz-skill 仓库本身的管理）",
      "skills": ["meta/contribute-skill", "meta/migrate-specs"]
    }
  }
}
```

### `bundle info <name>`

```bash
hskill bundle info <name> [--json]
```

查询单个 bundle 详情。

**`--json` 输出：**

```json
{
  "name": "analysis",
  "description": "分析工具（skill-analyzer + git-cleanup）",
  "skills": [
    { "path": "analysis/skill-analyzer", "name": "skill-analyzer" },
    { "path": "analysis/git-cleanup",    "name": "git-cleanup" }
  ]
}
```

### `bundle add`

```bash
hskill bundle add <name> --desc <description>
```

新建 bundle（写入 `skills-index.json` 的 `bundleMeta`）。若 bundle 已存在则报错退出，不覆盖。

### `bundle rename`

```bash
hskill bundle rename <old> <new>
```

重命名 bundle（更新 `bundleMeta` 键名及所有 skill 的 `bundle` 字段）。

**不在范围内：** `bundle delete`（需先处理其下所有 skill，交互复杂，独立设计）；bundle 级别的 install/uninstall（已有 `--bundle` flag）。

### `info <name>`

查询单个 item（skill / tool / hook）的详细安装状态。`hskill info` 按 skill → tool → hook 顺序自动识别类型；找不到时 exit 1 并输出：

```json
{ "error": true, "message": "Unknown item: \"<name>\". Run 'hskill list' to see available items." }
```

#### TTY 输出（人读格式）

**Skill：**

```
skill-analyzer  v1.0.0  [analysis bundle]

  USER SCOPE
    claude    ✓  v1.0.0  ~/.claude/skills/skill-analyzer/
    cursor    —
    codex     —

  PROJECT SCOPE
    claude    ✓  v0.9.0  (outdated)  ./.claude/skills/skill-analyzer/
```

**Tool：**

```
p-launch  v3.0.0

  INSTALLED    ~/.local/bin/p-launch
  STATUS       up-to-date
```

**Hook：**

```
check-similar-branch  v1.0.0

  USER      ✓  installed  ~/.claude/hooks/check-similar-branch.sh
  PROJECT   —  none
```

#### `info <name> --json`

```bash
hskill info skill-analyzer --json
```

**Skill 输出：**

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

**Tool 输出：**

```json
{
  "name": "p-launch",
  "type": "tool",
  "version": "3.0.0",
  "installed": "~/.local/bin/p-launch",
  "status": "up-to-date"
}
```

**Hook 输出：**

```json
{
  "name": "check-similar-branch",
  "type": "hook",
  "version": "1.0.0",
  "user":    { "status": "installed", "path": "~/.claude/hooks/check-similar-branch.sh" },
  "project": { "status": "none" }
}
```

`status` 取值：skill / hook scope → `"up-to-date"` | `"outdated"` | `"none"`；tool → `"up-to-date"` | `"outdated"` | `"not-installed"`。

---

## Hooks

### `hooks list --json`

```bash
hskill hooks list --json
```

```json
[
  {
    "name": "check-similar-branch",
    "version": "1.0.0",
    "description": "用 LLM 语义分析检测相似分支",
    "user":    { "status": "installed", "version": "1.0.0" },
    "project": { "status": "none",      "version": "—" }
  }
]
```

`status` values: `"installed"` | `"partial"` | `"none"`.  
`"partial"` = 脚本文件与 settings.json 注册只有其一存在。

### `hooks install --json`

```bash
hskill hooks install --name check-similar-branch --scope user --json
```

输出格式与 skill install 一致：

```json
{
  "hooks": {
    "installed": ["check-similar-branch"],
    "skipped":   [],
    "failed":    []
  }
}
```

`skipped` 条目格式与 skill/tool 对齐：

```json
{ "name": "check-similar-branch", "reason": "up-to-date", "version": "1.0.0" }
{ "name": "check-similar-branch", "reason": "outdated", "installed": "0.9.0", "available": "1.0.0" }
```

可用 flags：

| Flag | 说明 |
|------|------|
| `--name <name>` | 指定 hook 名称（非 TTY 下必须） |
| `--scope user\|project` | 安装 scope（默认 `user`） |
| `--project <path>` | project scope 时指定目标项目路径 |
| `--force` | 覆盖已有版本 |
| `--json` | 机器可读输出 |

### `hooks uninstall`

```bash
hskill hooks uninstall check-similar-branch --scope user --json
```

卸载同时删除脚本文件并从 `settings.json` 移除注册条目。event 数组为空时移除该 event 键。

---

## Uninstall

### `uninstall <name>`

```bash
hskill uninstall p-launch --json
```

卸载 tool（skills 和 hooks 通过 `hooks uninstall` 处理）。标准清理路径：

- `~/.local/bin/<name>`
- `~/.local/share/hskill/tools/<name>.py`（若存在）
- `~/.local/share/hskill/tools/<name>.json`
- `tool.json` 中 `uninstallPaths[]` 声明的路径（始终删除）
- `~/.zshrc` 中的 `# >>> <name>` snippet 区块

`configPaths[]` 在非 TTY 下默认保留；加 `--yes` 强制删除。

| Flag | 说明 |
|------|------|
| `--yes` | 跳过所有确认，含 configPaths |
| `--json` | 机器可读输出 |

---

## Upgrade

### `upgrade`

```bash
hskill upgrade [--skill <name>] [--target <target>] [--scope user|project] [--json]
```

只升级**已经安装**的 skill 到最新版本，不会安装未装过的 skill。`--skill` 和 `--target` 均可省略，省略即代表"全部"；两者独立可组合。

| Flag | 说明 |
|------|------|
| `--skill <name>` | 只升级指定 skill（省略则升级所有已装 skill） |
| `--target <target>` | 只升级指定 target（省略则遍历所有 target） |
| `--scope user\|project` | 安装 scope（默认 `user`） |
| `--json` | 机器可读输出 |

### 版本比较

对每个 `{skill, target}` 组合读取已装 SKILL.md 的 `version:` 字段与源版本比较：只有状态为 `update`（版本不同）的才会被升级；`none`（未安装）跳过，`up-to-date` 静默跳过。

### 输出

**TTY，有升级：** 与 `install` 相同格式的摘要（`printSummary`）。

**TTY，无需升级：**

```
  ✓ All installed skills are up to date
```

**`--json`，有升级：**

```json
{
  "skills": {
    "claude": { "installed": ["learn-skill"], "skipped": [], "failed": [] }
  }
}
```

**`--json`，无需升级：**

```json
{ "skills": {}, "upToDate": true }
```

### 错误处理

`--skill <name>` 传入未知 skill 名：直接 exit 1，stderr 输出：

```json
{ "error": true, "message": "Unknown skill: \"<name>\"" }
```

（TTY 模式下为 `chalk.red` 文本，不是 JSON）

`--target <name>` 无效：`resolveTargets` 抛出 `Unknown target: "<name>"`，同样 exit 1。

**不在范围内：** `--tool`（tool 升级用 `install --force`）、hooks 升级、交互模式（`upgrade` 恒为非交互）、`--force` flag（状态为 `update` 即升级，无需强制）。

---

## Install

### Minimal invocation

```bash
hskill install --skill skill-analyzer --target claude --scope user --json
```

### Output shape

A single JSON object is written to stdout only on success. Nothing is written to stdout on failure (error goes to stderr).

```json
{
  "skills": {
    "claude": {
      "installed": ["skill-analyzer"],
      "skipped":   [],
      "failed":    []
    }
  }
}
```

When installing tools, the top-level key is `tools` instead of `skills`:

```json
{
  "tools": {
    "installed": ["p-launch"],
    "skipped":   [],
    "failed":    []
  }
}
```

### `skipped` entries

```json
{ "name": "skill-analyzer", "reason": "up-to-date", "version": "1.0.0" }
{ "name": "skill-analyzer", "reason": "outdated",   "installed": "0.9.0", "available": "1.0.0" }
```

`"up-to-date"` — installed version matches available; no action needed.  
`"outdated"` — newer version exists but `--force` was not passed (non-TTY never prompts).

### `failed` entries

```json
{ "name": "skill-analyzer", "reason": "source_not_found" }
{ "name": "skill-analyzer", "reason": "error", "detail": "EACCES: permission denied" }
```

### Force-overwrite

```bash
hskill install --skill skill-analyzer --target claude --scope user --force --json
```

### Install multiple skills

```bash
hskill install --skill skill-analyzer,diataxis-docs --target claude --scope user --json
```

### Install a bundle

```bash
hskill install --bundle analysis --target claude --scope user --json
```

---

## Config

### `config set / get / unset / list`

```bash
hskill config set <key> <value>   # 写入配置
hskill config get <key>           # 读取单个值
hskill config unset <key>         # 删除配置项
hskill config list [--json]       # 列出所有配置
```

#### 配置文件格式

```json
{
  "default": {
    "target": "claude",
    "scope": "user"
  }
}
```

存储路径：

| 层级 | 路径 |
|------|------|
| User-level | `~/.config/hskill/config.json` |
| Project-level | `<cwd>/.hskillrc`（JSON 格式） |

Project-level 同名字段覆盖 user-level。

#### `config list --json` 输出

```json
{
  "default.target": "claude",
  "default.scope": "user",
  "source": "user"
}
```

`source` 字段说明当前生效的配置来自哪个层级：`"user"` 或 `"project"`。

#### 不在范围内

- 配置迁移工具
- 配置加密（配置文件只含偏好，无敏感信息）

---

## Error handling

In `--json` mode all errors go to stderr as a JSON object and exit code is 1:

```json
{ "error": true, "message": "Unknown skill: \"typo-skill\"" }
```

stdout is empty on error — safe to parse stdout unconditionally.

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (unknown skill/tool, mutual exclusion violation, unexpected exception) |

---

## `hskill sync` — Syncthing daemon management

Manages the sync-agent Syncthing daemon. Requires `sync-agent` tool installed (`hskill install --tool sync-agent`).

### `hskill sync setup`

```bash
hskill sync setup
```

Idempotent initialization: starts Syncthing if not running, reads `~/.hskill/sync-agent/config.json`, registers folders and devices via REST API, installs launchd plist for auto-start. Safe to re-run.

### `hskill sync start`

```bash
hskill sync start
```

Starts the Syncthing daemon (skips if already running).

### `hskill sync stop`

```bash
hskill sync stop
```

Stops the Syncthing daemon.

### `hskill sync status`

```bash
hskill sync status
```

Prints daemon running state and local device ID. API key is redacted (first 4 chars only).

---

## Non-TTY behavior reference

| Situation | Behavior |
|-----------|----------|
| No `--skill`/`--tool`/`--bundle` flag | Exits 1 with error; never launches fzf |
| Skill already installed, same version | Skipped with `reason: "up-to-date"`; no prompt |
| Skill already installed, older version | Skipped with `reason: "outdated"`; use `--force` to update |
| Tool already installed, same version | Skipped with `reason: "up-to-date"`; no prompt |
| Tool already installed, older version | Skipped with `reason: "outdated"`; use `--force` to update |
| Skill/tool has `vars.json` | Default values applied automatically; no prompt |
| Tool has `zshrc.snippet` | Patch skipped with a stderr note; apply manually |

---

## Recommended agent workflow

```
1. hskill status --json          → check what's already installed
2. hskill outdated --json        → check for updates
3. hskill install --skill <s>    → install / update as needed
4. parse stdout JSON             → confirm installed/skipped/failed
5. check exit code               → 0 = ok, 1 = error (read stderr JSON)
```

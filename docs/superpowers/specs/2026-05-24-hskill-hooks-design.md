---
migrated: 2026-05-29
docs:
  - reference/agent-cli-guide.md       # Hooks — CLI 命令参考
  - explanation/hskill-architecture.md  # scope 模型、settings.json patch 格式
superseded_by:
  - 2026-05-24-hook-version-tracking-design.md  # hooks list 输出格式（VER 列）、install 版本感知逻辑
---

# hskill hooks 子命令设计

**日期:** 2026-05-24  
**状态:** 已实现

## 背景

`check-similar-branch.sh` 是一个 Claude Code PreToolUse hook，用 LLM 语义分析检测相似分支，目前只存在于 `harveyz-skill` 项目自身的 `.claude/hooks/`。目标是将其打包进 npm 发布，让 `hskill` 能像管理 skills/tools 一样，将 hook 安装到任意项目或全局。

## 目标

- `hskill hooks list` — 列出所有可用 hook 及其在 user/project 的安装状态
- `hskill hooks install` — 安装 hook（交互式或命令行参数）
- `hskill hooks uninstall` — 卸载 hook
- `hskill status` — 顺带展示 hooks 区块

## 方案：复用现有基础设施（方案 B）

与 skills/tools 保持一致的架构，hook 作为第三类 item 集成进 skills-index.json 和安装管道。

## 数据层

### skills-index.json 新增 `hooks` 字段

```json
{
  "hooks": [
    {
      "name": "check-similar-branch",
      "description": "用 LLM 语义分析检测相似分支",
      "path": "scripts/hooks/check-similar-branch.sh",
      "event": "PreToolUse",
      "matcher": "Bash",
      "timeout": 60,
      "statusMessage": "检查相似分支..."
    }
  ]
}
```

每个 hook 条目包含：
- `name`: 唯一标识符，也是脚本文件名（不含 `.sh`）
- `description`: 人读描述
- `path`: 相对 repo 根目录的脚本路径
- `event`: Claude hook 事件名（PreToolUse / PostToolUse / SessionStart 等）
- `matcher`: 工具匹配器（空字符串 = 匹配所有）
- `timeout`: 超时秒数（可选）
- `statusMessage`: Claude UI 展示的状态消息（可选）

### 脚本位置

```
scripts/
  hooks/
    check-similar-branch.sh    ← 从 .claude/hooks/ 移过来
```

`package.json` 的 `files` 字段加入 `"scripts/hooks/"` 以随 npm 发布。

## 安装目标（Scope）

与 skills 保持一致，分 user / project 两个 scope：

| scope | 脚本安装位置 | settings 注册位置 |
|---|---|---|
| user（全局） | `~/.claude/hooks/<name>.sh` | `~/.claude/settings.json` |
| project | `<cwd>/.claude/hooks/<name>.sh` | `<cwd>/.claude/settings.json` |

## 安装机制（installHooks）

1. 确保目标 hooks 目录存在（`fs.ensureDir`）
2. 复制脚本文件，设 mode `0o755`
3. 读取目标 `settings.json`（不存在则创建空对象）
4. 检查 `hooks.<event>` 数组中是否已有相同 command 的条目
   - 若已存在且非 `--force`：跳过注册（避免重复）
   - 若 `--force`：先删除旧条目再插入
5. 写回 `settings.json`（格式化 JSON）

### settings.json patch 格式

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash ~/.claude/hooks/check-similar-branch.sh",
            "timeout": 60,
            "statusMessage": "检查相似分支..."
          }
        ]
      }
    ]
  }
}
```

command 路径规则：
- user scope → `~/.claude/hooks/<name>.sh`
- project scope → `bash \"$(git rev-parse --show-toplevel 2>/dev/null || echo .)/.claude/hooks/<name>.sh\"`

## 卸载机制（uninstallHook）

1. 删除脚本文件（若存在）
2. 从 `settings.json` 的对应 event 数组中移除匹配条目
3. 若 event 数组变为空，移除该 event 键

## 状态检测（checkHookInstalled）

```js
// 返回
{
  user:    { status: 'installed' | 'partial' | 'none' },
  project: { status: 'installed' | 'partial' | 'none' },
}
```

- `installed`: 脚本文件存在 **且** settings.json 中已注册
- `partial`: 二者之一存在（文件存在但未注册，或已注册但文件丢失）
- `none`: 都不存在

## CLI 接口

```bash
# 列出所有可用 hook + 当前项目的 user/project 安装状态
hskill hooks list [--json]

# 安装（TTY 下交互式选 hook + scope；非 TTY 下必须传参）
hskill hooks install
hskill hooks install --name check-similar-branch
hskill hooks install --name check-similar-branch --scope user    # 全局
hskill hooks install --name check-similar-branch --scope project # 项目级
hskill hooks install --project /path/to/other-project           # 指定项目路径
hskill hooks install --force                                     # 覆盖已有

# 卸载
hskill hooks uninstall check-similar-branch
hskill hooks uninstall check-similar-branch --scope user
```

### hskill hooks list 输出格式

```
NAME                         U   P   DESCRIPTION
check-similar-branch         ✓   —   用 LLM 语义分析检测相似分支
```

U = user scope，P = project scope  
✓ = installed，~ = partial，— = none

### hskill status hooks 区块

在现有 skills / tools 展示之后追加：

```
hooks:
  check-similar-branch   U:✓  P:—   用 LLM 语义分析检测相似分支
```

## 代码变动范围

| 文件 | 变动类型 | 说明 |
|---|---|---|
| `skills-index.json` | 新增字段 | 加入 `hooks[]` 数组 |
| `scripts/hooks/check-similar-branch.sh` | 新文件（移动） | 从 `.claude/hooks/` 移过来 |
| `package.json` | 修改 | `files` 加入 `"scripts/hooks/"` |
| `lib/bundles.js` | 新增导出 | `getAllHookItems()`、`checkHookInstalled()` |
| `lib/installer.js` | 新增导出 | `installHooks()`、`uninstallHook()` |
| `bin/cli.js` | 新增分支 | `hooks` 子命令（list/install/uninstall） |
| `.claude/hooks/check-similar-branch.sh` | 删除 | 移到 `scripts/hooks/` 后删除原文件 |
| `.claude/settings.json` | 修改 | command 路径从项目相对路径改为 npm 包绝对路径（用 `npm root -g` 解析） |

## 边界情况

- **非 git 仓库**：project scope 安装时，若 `cwd` 不是 git 仓库，正常安装到 `cwd/.claude/`（不强制要求 git）
- **settings.json 已有同名 event**：追加到现有数组，不覆盖其他条目
- **重复安装**：默认跳过，`--force` 才覆盖
- **脚本路径**：user scope 用 `~` 硬路径；project scope 用 `git rev-parse --show-toplevel` 动态路径，保证可移植
- **npm 包路径解析**：安装时用 `npm root -g` 找到包路径，写入 settings.json 的 command 用绝对路径

## 不在范围内

- hook 版本管理（暂不支持 hook 升级检测）
- 非 Claude 工具的 hooks（Cursor、Codex 无类似机制）
- 交互式 fzf 选择（hooks 数量少，inquirer 足够）

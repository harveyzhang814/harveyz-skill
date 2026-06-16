# hub CLI 参考

hub 是个人开发者 OS，管理项目和任务。所有子命令支持 `--json` 输出，适合 agent 和脚本调用。

## 数据存储

| 路径 | 内容 |
|------|------|
| `~/.hskill/hub/hub.db` | SQLite 主数据库（projects + tasks 表） |
| `~/.hskill/public/PROJECTS.md` | 项目列表 Markdown 镜像（只读参考） |

环境变量 `HUB_MD_PATH` 可覆盖 `PROJECTS.md` 路径。

---

## hub projects

### list

```
hub projects list [--json]
```

列出所有已注册项目。

**JSON 输出：**
```json
{
  "ok": true,
  "data": [
    { "name": "my-repo", "path": "/Users/x/Projects/my-repo", "description": "..." }
  ]
}
```

---

### add

```
hub projects add <name> [--path <path>] [--desc <description>] [--json]
```

注册或更新项目。`name` 通常与 GitHub 仓库名一致。

| 参数 | 必填 | 说明 |
|------|------|------|
| `name` | ✓ | 项目名 |
| `--path` | | 本地目录路径 |
| `--desc` | | 简短描述 |

**JSON 输出：**
```json
{ "ok": true, "data": { "name": "my-repo", "path": "...", "description": "..." } }
```

---

### path

```
hub projects path <name> [--json]
```

输出项目的本地路径，适合 agent 用于 `cd` 或定位工作目录。

**JSON 输出：**
```json
{ "ok": true, "data": "/Users/x/Projects/my-repo" }
```

项目不存在时：
```json
{ "ok": false, "error": "Project 'x' not found" }
```

---

### scan

```
hub projects scan <dir> [<dir2> ...] [--json]
```

扫描目录（深度 2 层：`<dir>/*/.git`），将找到的 git 仓库批量注册为项目。项目名从 `origin` remote URL 解析，无 remote 时兜底用目录名。已存在的同名项目跳过不覆盖。

**参数：**
- `<dir>...` — 要扫描的目录（一个或多个），支持 `~` 展开
- `--json` — JSON 输出

**JSON 输出：**
```json
{
  "ok": true,
  "data": {
    "added":   [{"name": "my-repo", "path": "/Users/x/Projects/my-repo"}],
    "skipped": ["hub"],
    "failed":  [{"path": "/bad/path", "reason": "directory not found"}]
  }
}
```

---

### sync

```
hub projects sync [--json]
```

从 p-launch 配置自动扫描本地目录并更新 `PROJECTS.md`。需要已安装 p-launch。

**JSON 输出：**
```json
{ "ok": true, "data": { "scanned": 42 } }
```

---

## hub tasks

### list

```
hub tasks list [--project <name>] [--status <status>] [--priority <priority>] [--json]
```

列出任务，支持多维过滤（可组合）。

| 过滤参数 | 可选值 |
|---------|--------|
| `--project` / `-p` | 项目名 |
| `--status` / `-s` | `todo` \| `done` |
| `--priority` / `-P` | `P1` \| `P2` \| `P3` |

**JSON 输出：**
```json
{
  "ok": true,
  "data": [
    { "id": 1, "title": "修复 bug", "project": "my-repo", "status": "todo", "priority": "P1" }
  ]
}
```

---

### add

```
hub tasks add <title> --project <name> [--priority <priority>] [--json]
```

新增任务。`--project` 必填，`--priority` 默认 `P2`。

**JSON 输出：**
```json
{ "ok": true, "data": { "id": 7, "title": "...", "project": "...", "status": "todo", "priority": "P2" } }
```

---

### done

```
hub tasks done <id> [--json]
```

将任务标记为 `done`。

**JSON 输出：**
```json
{ "ok": true, "data": { "id": 7, "title": "...", "status": "done" } }
```

---

### update

```
hub tasks update <id> [--title <title>] [--priority <priority>] [--status <status>] [--json]
```

更新任务字段，所有字段可选，只传需要修改的。

| 参数 | 可选值 |
|------|--------|
| `--status` | `todo` \| `done` |
| `--priority` | `P1` \| `P2` \| `P3` |

**JSON 输出：**
```json
{ "ok": true, "data": { "id": 7, ... } }
```

---

### rm

```
hub tasks rm <id> [--json]
```

删除任务。

**JSON 输出：**
```json
{ "ok": true, "data": { "deleted": true } }
```

---

## 错误格式

所有命令在 `--json` 模式下，错误统一返回：

```json
{ "ok": false, "error": "<错误描述>" }
```

退出码为 `1`。

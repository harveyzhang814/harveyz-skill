# hub 架构与设计原理

解释 hub 的整体架构、数据层设计决策，以及它如何从 p-launch 和 todo-tool 演进而来。

---

## 为什么是 hub

p-launch 管项目列表 + TUI 切换，todo-tool 管任务 —— 两个工具数据孤立，索引格式不同，无法在 TUI 里直接看到任务。hub 把两者合并为一个产物，共享同一个数据层，提供统一的入口：无参数启动 TUI，带参数走 CLI。

---

## 架构：共享 core/ + 双入口

```
hub (TUI, no args)          hub <cmd> --json (CLI)
        ↘                       ↙
         core/  (纯 Python，无 UI 依赖)
     projects · tasks · db
              ↓
           SQLite
```

`core/` 不依赖 Textual 或 Typer。TUI 和 CLI 各自从 `core/` 导入，互不感知对方。

**原因：** 如果 core/ 依赖 Textual，CLI 测试就必须 mock Textual 的屏幕环境；反之则 TUI 无法独立测试数据逻辑。解耦后，`core/` 可以在无头环境中运行完整单元测试，TUI 和 CLI 只负责展示层。

### 目录结构

```
tools/hub/
├── hub/
│   ├── core/
│   │   ├── projects.py     # 项目注册：scan、add、list、path lookup
│   │   ├── tasks.py        # 任务 CRUD
│   │   └── db.py           # SQLite 连接、schema、迁移
│   ├── cli/
│   │   ├── __init__.py     # Typer app，全局 --json flag
│   │   ├── projects.py
│   │   ├── tasks.py
│   │   └── git.py
│   ├── tui/
│   │   ├── app.py          # Textual App 入口
│   │   └── panels/         # ProjectsPanel、GitPanel、TasksPanel
│   └── __main__.py         # 无参数 → TUI；有参数 → CLI
└── pyproject.toml
```

---

## 数据层设计

### SQLite + PROJECTS.md 双存储

```
~/.hskill/
├── public/
│   └── PROJECTS.md     # 项目列表 Markdown 镜像
└── hub/
    └── hub.db          # SQLite 主数据库（projects + tasks）
```

**设计原则：** SQLite 是写入唯一来源；`PROJECTS.md` 是只读导出，每次 add/scan/sync 后自动重写。Agent 需要项目列表时直接 `Read ~/.hskill/public/PROJECTS.md`，无需 CLI 已安装。这让 hub 与依赖项目信息的其他工具解耦。

**PROJECTS.md 格式：**

```markdown
# Project Index

- **repo-name** `/local/path`
  optional description
```

`name` 字段使用 GitHub repo 名（从 `git remote get-url origin` 末段提取，去掉 `.git` 后缀）。无 remote 时兜底用目录名。

### Schema

```sql
projects (id, name, path, description, github_url, last_opened_at)
tasks    (id, title, project_id, priority, status, created_at)
```

---

## 从 p-launch + todo-tool 演进

### 为什么需要迁移

p-launch 独立维护本地目录扫描结果，todo-tool 独立维护项目索引 `~/.hskill/todo-tool/PROJECTS.md`，两者使用不同的 name 格式（目录名 vs GitHub repo 名）。在 TUI 中创建任务时无法关联项目，agent 切换项目路径也需要读两个不同来源。

### 迁移策略

- **共享索引路径**：`~/.hskill/public/PROJECTS.md`，替代 `~/.hskill/todo-tool/PROJECTS.md`
- **一次性 merge 迁移**：todo-tool 首次读取时检查 `~/.hskill/public/.migrated` flag；未存在则将旧索引 merge 入新路径（保留 description 字段），写入 flag，后续不重复执行
- **数据迁移**：`~/.local/share/todo/tasks.db` → `~/.hskill/hub/hub.db`，首次启动自动执行
- **旧文件保留**：`~/.hskill/todo-tool/PROJECTS.md` 迁移后不删除

p-launch 已归档（`tools/archived/p-launch`），hub 通过 `hub projects scan` 承接其核心功能（目录扫描 + 项目注册）。

### hub projects scan 的名称解析

```python
def _resolve_name(repo_path):
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=repo_path, capture_output=True, text=True, timeout=5
    )
    if result.returncode == 0:
        url = result.stdout.strip()
        return url.rstrip("/").rstrip(".git").split("/")[-1]
    return repo_path.name  # 兜底
```

名称来自 remote URL 而非目录名，使项目名与 GitHub repo 名保持一致，方便 agent 跨工具引用。

---

## TUI 布局

三栏布局，Textual 框架：

```
Col 1 (Projects)  │ Col 2 (Git)             │ Col 3 (Tasks)
──────────────────│─────────────────────────│───────────────
项目列表           │ 分支列表（ListView）    │ 当前项目任务
任务数 badge       │ WITH REMOTE / LOCAL 分组│ TODO / DONE 分组
sync 状态          │ push/pull 状态          │ 搜索过滤
```

**Git 面板** 以 `ListView` 展示所有分支，按"有远程跟踪"和"仅本地"分组。不再展示 working tree dirty 状态或最近 commit —— 面板聚焦于分支状态。

**任务面板** 绑定到当前选中项目，`n` 新建任务，`Space` 切换状态，`/` 实时过滤。

---

## Agent 访问模式

| 目标 | 方法 |
|------|------|
| 获取项目列表 | `Read ~/.hskill/public/PROJECTS.md`（无需 CLI） |
| 获取项目路径 | `hub projects path <name> --json` |
| 列出待办任务 | `hub tasks list --project <name> --status todo --json` |
| 新建任务 | `hub tasks add "title" --project <name>` |
| 标记完成 | `hub tasks done <id>` |

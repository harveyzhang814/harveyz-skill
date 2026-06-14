# todo-tool 参考文档

## 数据模型

```sql
CREATE TABLE tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title      TEXT NOT NULL,
    project    TEXT NOT NULL,
    priority   TEXT DEFAULT 'P2',   -- P0 / P1 / P2 / P3
    status     TEXT DEFAULT 'todo', -- todo / done
    created_at TEXT NOT NULL        -- ISO 8601
);

CREATE INDEX idx_project ON tasks(project);
CREATE INDEX idx_status  ON tasks(status);
```

预留扩展字段（后续迭代）：`module_id`、`type_tag`、`module_tag`、`criteria`、`completed_at`、`source`、`archived`。

## CLI 接口

```bash
# 同步 TODO.md → SQLite（主要写入路径）
todo sync <project>
todo sync --path <path>       # 无 local_path 时直接指定路径

# 添加任务（直接写 SQLite，绕过 TODO.md，程序化用）
todo add "标题" --project "video-learner" [--priority P1]

# 列出任务
todo list
todo list --project "video-learner"
todo list --priority P1
todo list --json              # agent 解析用

# 标记完成
todo done <id>

# 查看单条
todo show <id>

# 启动 web 服务
todo serve [--port 8080]

# 配置
todo config set db-path ~/Syncthing/todo/tasks.db
todo config show
```

`add-todo` skill 集成调用：
```bash
# 写入 TODO.md 后调用
todo sync "$(basename $PWD)"
```

`--json` 输出格式：
```json
[
  { "id": 1, "title": "...", "project": "video-learner", "priority": "P1", "status": "todo", "created_at": "2026-06-12T10:00:00" }
]
```

## API 端点

```
GET    /api/tasks              列出任务（?project=&status=&priority=）
POST   /api/tasks              创建任务
PATCH  /api/tasks/{id}         更新任务（title / priority / status）
DELETE /api/tasks/{id}         删除任务

GET    /api/projects           所有项目名列表（从 tasks 表聚合）
```

POST body：
```json
{ "title": "...", "project": "video-learner", "priority": "P2" }
```

PATCH body（部分更新）：
```json
{ "status": "done" }
```

CLI 直接操作 SQLite，不走 API。

# TODO.md 作为主数据源：架构设计原理

## 为什么这样设计

当前架构中 `todo add` 直接写 SQLite，描述字段仅存在于 TODO.md，两者各管一半。Agent 在项目目录下工作时自然读取本地文件，读 TODO.md 比查 SQLite 更直接。让 TODO.md 成为完整、可信的数据源，SQLite 作派生索引，职责更清晰。

## 架构概述

```
TODO.md (主) ──sync──▶ SQLite (索引)
    ▲                       │
    │                       │ ID 写回
    └───────────────────────┘
```

TODO.md 是唯一的写入源。SQLite 是跨项目的只读索引，由 `todo sync` 派生生成。

## 组件变化

| 组件 | 变化 |
|------|------|
| `todo_format.yaml` | 新增，定义 TODO.md 格式规范 |
| `todo/parser.py` | 新增，解析 TODO.md 为结构化任务列表 |
| `todo/db.py` | 新增 `sync_from_file()` 方法 |
| `todo/cli.py` | 新增 `todo sync` 命令 |
| `add-todo` skill | 改写阶段二/三：写 TODO.md → 调 sync |

## 数据流

### `todo sync <project>` 执行步骤

1. 从 SQLite 查出项目 `local_path`（或接受 `--path` 直接指定）
2. 读取 `{local_path}/TODO.md`，用 `todo_format.yaml` 中的 pattern 解析所有任务块
3. 判断每条任务所在分区，确定 status
4. 对每条任务：
   - **有 ID** → `UPDATE tasks SET title=?, priority=?, status=? WHERE id=?`
   - **无 ID** → `INSERT INTO tasks ...`，拿到 `lastrowid`，将 `| **ID**: {id}` 写回 TODO.md 对应行
5. 输出：`✓ 同步完成：N 条新增，M 条更新`

### add-todo skill 新写入流程

```
写入 TODO.md（无 ID）
    ↓
todo sync [项目名]
    ↓
ID 写回 TODO.md
    ↓
确认消息：✅ 已将 [标题] 写入 TODO.md（SQLite ID: [id]）
```

### 删除处理

sync 只做 upsert，不删除。TODO.md 中删掉的任务在 SQLite 里保留（历史可查）。

## CLI 变化

| 命令 | 变化 |
|------|------|
| `todo sync <project>` | 新增 |
| `todo sync --path <path>` | 新增（无 local_path 时用） |
| `todo add` | 保留，用于程序化直接写 SQLite |
| `todo done <id>` | 保留，但建议同步修改 TODO.md 分区后再 sync |

## 错误处理

| 情况 | 处理 |
|------|------|
| TODO.md 不存在 | 报错：`TODO.md not found at {path}` |
| 项目无 local_path 且未传 --path | 报错提示用 `todo project set-path` |
| metadata 行格式错误 | 跳过该条任务，输出警告行 |
| ID 写回失败（文件权限等） | 报错，已插入的 SQLite 记录不回滚（可重新 sync） |

## 测试策略

- `test_parser.py`：解析各种任务块格式（有/无 ID、有/无描述、pending/done 分区）
- `test_sync.py`：新增任务 ID 写回、已有 ID 任务更新、格式错误跳过
- `test_cli_sync.py`：CLI 调用、`--path` 参数、项目不存在报错

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| TODO.md 手动编辑破坏格式，parser 无法解析 | 格式错误跳过并输出警告，不中断整体 sync |
| sync 后 ID 写回与人工编辑冲突 | sync 只修改 metadata 行，不动标题和描述 |
| `todo add` 和 TODO.md 产生重复任务 | 两条路径独立，`todo add` 绕过 TODO.md 是有意设计，使用者自行管理 |

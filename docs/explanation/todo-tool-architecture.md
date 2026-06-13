# todo-tool 架构设计原理

## 为什么需要这个工具

`add-todo` skill 目前将需求写入项目本地 markdown 文件。todo-tool 作为中央持久化层，跨项目聚合所有任务，支持本机全局访问，未来通过 Syncthing 同步多端设备。

## 存放位置

```
harveyz-skill/
├── skills/creative/add-todo/SKILL.md   ← 更新 Phase 5，追加调用 CLI
└── tools/todo-tool/
    ├── todo/
    │   ├── cli.py        # Typer CLI
    │   ├── server.py     # FastAPI（API + 静态文件托管）
    │   ├── db.py         # SQLite 访问层
    │   └── models.py     # Pydantic 数据模型
    ├── frontend/         # React + Vite + Tailwind + shadcn/ui
    └── pyproject.toml
```

## 架构概览

```
add-todo skill
    ├── 写 TODO.md（项目本地，主数据源）
    └── 调用 `todo sync`
              ↓
        ~/.local/share/todo/tasks.db   （路径可配置，Syncthing 友好）
              ↓
    ┌─────────┴──────────┐
  CLI (todo list/done)   FastAPI (:8080)
  （agent/bash 调用）         ↓
                       React SPA（人工操作）
```

**安装：**
```bash
cd tools/todo-tool
pipx install -e .
```

**兼容性保障：** `add-todo` skill 调用 `todo sync` 前检查命令是否存在，不存在则 warn 但不中断 TODO.md 写入。

## 前端页面设计

单页应用，任务列表视图：

```
┌─────────────────────────────────────────────────┐
│  Todo  [All Projects ▼]  [All Priorities ▼]  [+ Add] │
├─────────────────────────────────────────────────┤
│ video-learner                                   │
│  ○ P1  重构视频解析模块          2026-06-10  [✓] │
│  ○ P2  添加字幕导出功能          2026-06-11  [✓] │
│                                                 │
│ harveyz-skill                                   │
│  ○ P0  修复 add-todo skill 路径问题  2026-06-12  [✓] │
└─────────────────────────────────────────────────┘
```

交互：
- Filter Bar：按 project、priority 筛选
- `[✓]` 一键标记完成（乐观更新）
- `[+ Add]` 弹出 shadcn `<Dialog>` 创建任务
- 完成任务默认折叠，可展开

详情页、看板视图留作后续迭代。

## 风险

- Syncthing 同步期间若两端同时写入 SQLite 可能冲突——当前版本不处理，单机使用不受影响
- `add-todo` skill 更新需同步测试，确保 TODO.md 写入不受 `todo sync` 失败影响

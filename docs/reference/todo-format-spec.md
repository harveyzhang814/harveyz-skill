# TODO.md 格式规范

格式由 `tools/todo-tool/todo_format.yaml` 定义，作为 parser 和 skill 的单一来源。

## 文件结构

```markdown
# TODO / Backlog

## 🚧 待开发

### [任务标题（≤20 字）]
**优先级**: P? | **日期**: YYYY-MM-DD | **ID**: 42

描述：做什么、为什么。不写怎么做。

---

## ✅ 已完成

### [已完成任务标题]
**优先级**: P2 | **日期**: 2026-06-10 | **ID**: 38

---
```

## 字段规范

| 字段 | 类型 | 合法值 | 说明 |
|------|------|--------|------|
| 标题 | string | ≤20 字 | `###` 三级标题，祈使句 |
| 优先级 | enum | P0/P1/P2/P3 | 默认 P2 |
| 日期 | string | YYYY-MM-DD | 创建日期 |
| ID | integer | 正整数 | sync 前无此字段，sync 后写回 |
| 描述 | string | 任意 | 可选，多段文字均可 |

## 状态由分区决定

- `## 🚧 待开发` 分区内 → `status = "todo"`
- `## ✅ 已完成` 分区内 → `status = "done"`

状态不写在任务块内，由 parser 根据所在分区推断。

## `todo_format.yaml` 完整内容

```yaml
version: "1.0"

file_structure:
  sections:
    pending: "## 🚧 待开发"
    done: "## ✅ 已完成"
  task_separator: "---"

task_block:
  heading:
    level: 3
    max_length: 20
  metadata_line:
    template: "**优先级**: {priority} | **日期**: {date} | **ID**: {id}"
    pattern: '^\*\*优先级\*\*:\s*(?P<priority>P[0-3])\s*\|\s*\*\*日期\*\*:\s*(?P<date>\d{4}-\d{2}-\d{2})(?:\s*\|\s*\*\*ID\*\*:\s*(?P<id>\d+))?'
    fields:
      priority:
        type: enum
        values: [P0, P1, P2, P3]
        default: P2
      date:
        type: string
        format: "YYYY-MM-DD"
      id:
        type: integer
        optional: true
  description:
    type: string
    required: false
```

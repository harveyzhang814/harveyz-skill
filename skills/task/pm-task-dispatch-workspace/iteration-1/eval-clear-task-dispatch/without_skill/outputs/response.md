# Task Dispatch Response

## Steps Taken

1. Checked the existing tasks directory at `~/Projects/project-management/tasks/` to understand the task file format by reading an existing task (T001/task.md).
2. Created the task directory `/Users/harveyzhang96/Projects/project-management/tasks/T110/`.
3. Created the task file `task.md` inside T110 following the established format (YAML frontmatter + markdown sections).
4. Created this output directory and response file.

No actual API calls were made. The task was dispatched by writing a task file to the shared tasks directory where coding-master can pick it up.

## Task File Created

**Path:** `/Users/harveyzhang96/Projects/project-management/tasks/T110/task.md`

**Full content:**

```markdown
---
id: T110
project: data-tools
assignee: coding-master
assigner: harvey
priority: medium
status: todo
created: 2026-04-26
---

## 主要目标

用 Python 写一个命令行工具，读取 CSV 文件并输出统计摘要，包括行数、列名、每列的均值/最大/最小。

## 关键约束

1. 使用 Python 实现，作为命令行工具运行
2. 接受 CSV 文件路径作为命令行参数
3. 输出内容包括：
   - 总行数
   - 所有列名
   - 每列的均值（mean）、最大值（max）、最小值（min）（仅针对数值列）
4. 代码应结构清晰，包含必要的错误处理

## 工作流

1. 设计命令行接口（推荐使用 `argparse`）
2. 实现 CSV 读取逻辑（推荐使用 `csv` 标准库或 `pandas`）
3. 计算各列统计数据
4. 格式化并输出统计摘要
5. 添加基本错误处理（文件不存在、非数值列跳过等）

## 使用工具

- Python 标准库（`argparse`, `csv`, `statistics`）或第三方库（`pandas`）

## 评估标准

- [ ] 命令行工具可通过 `python csv_summary.py <file.csv>` 运行
- [ ] 正确输出总行数
- [ ] 正确输出所有列名
- [ ] 对每个数值列输出均值、最大值、最小值
- [ ] 非数值列能优雅跳过（不报错）
- [ ] 包含文件不存在等基本错误处理

## 资料管理

- 任务目录：`~/Projects/project-management/tasks/T110/`
- 交付物：Python 脚本 `csv_summary.py`，直接作为任务交付物报告给 assigner
```

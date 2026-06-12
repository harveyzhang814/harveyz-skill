import pytest
from pathlib import Path
from todo.parser import ParsedTask, parse_todo_file


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "TODO.md"
    p.write_text(content)
    return p


def test_parse_pending_task_without_id(tmp_path):
    p = _write(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 修复字幕导出乱码\n"
        "**优先级**: P1 | **日期**: 2026-06-12\n\n"
        "字幕导出时出现 UTF-8 编码问题。\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    tasks = parse_todo_file(p)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.title == "修复字幕导出乱码"
    assert t.priority == "P1"
    assert t.date == "2026-06-12"
    assert t.id is None
    assert t.status == "todo"
    assert "UTF-8" in t.description


def test_parse_task_with_id(tmp_path):
    p = _write(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 添加分页功能\n"
        "**优先级**: P2 | **日期**: 2026-06-12 | **ID**: 7\n\n"
        "支持列表分页。\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    tasks = parse_todo_file(p)
    assert len(tasks) == 1
    assert tasks[0].id == 7


def test_parse_done_task(tmp_path):
    p = _write(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "## ✅ 已完成\n\n"
        "### 初始化项目\n"
        "**优先级**: P0 | **日期**: 2026-06-01 | **ID**: 1\n\n"
        "---\n"
    ))
    tasks = parse_todo_file(p)
    assert len(tasks) == 1
    assert tasks[0].status == "done"


def test_parse_multiple_tasks(tmp_path):
    p = _write(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 任务一\n"
        "**优先级**: P1 | **日期**: 2026-06-12\n\n"
        "---\n\n"
        "### 任务二\n"
        "**优先级**: P2 | **日期**: 2026-06-12 | **ID**: 5\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    tasks = parse_todo_file(p)
    assert len(tasks) == 2
    assert tasks[0].title == "任务一"
    assert tasks[0].id is None
    assert tasks[1].title == "任务二"
    assert tasks[1].id == 5


def test_skip_task_with_malformed_metadata(tmp_path):
    p = _write(tmp_path, (
        "# TODO / Backlog\n\n"
        "## 🚧 待开发\n\n"
        "### 格式错误的任务\n"
        "这不是元数据行\n\n"
        "---\n\n"
        "### 正常任务\n"
        "**优先级**: P2 | **日期**: 2026-06-12\n\n"
        "---\n\n"
        "## ✅ 已完成\n"
    ))
    tasks = parse_todo_file(p)
    assert len(tasks) == 1
    assert tasks[0].title == "正常任务"


def test_parse_empty_file(tmp_path):
    p = _write(tmp_path, "# TODO / Backlog\n\n## 🚧 待开发\n\n## ✅ 已完成\n")
    assert parse_todo_file(p) == []


def test_metadata_line_num_is_correct(tmp_path):
    content = (
        "# TODO / Backlog\n"     # line 0
        "\n"                      # line 1
        "## 🚧 待开发\n"         # line 2
        "\n"                      # line 3
        "### 测试任务\n"          # line 4
        "**优先级**: P2 | **日期**: 2026-06-12\n"  # line 5
        "\n"                      # line 6
        "---\n"                   # line 7
        "\n"                      # line 8
        "## ✅ 已完成\n"         # line 9
    )
    p = _write(tmp_path, content)
    tasks = parse_todo_file(p)
    assert len(tasks) == 1
    assert tasks[0].metadata_line_num == 5

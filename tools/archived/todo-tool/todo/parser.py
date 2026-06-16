import functools
import re
import sys
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_FORMAT_PATH = Path(__file__).parent / "todo_format.yaml"


@functools.lru_cache(maxsize=None)
def _load_format() -> dict:
    return yaml.safe_load(_FORMAT_PATH.read_text(encoding="utf-8"))


@dataclass
class ParsedTask:
    title: str
    priority: str
    date: str
    id: Optional[int]
    status: str
    description: str
    metadata_line_num: int


def parse_todo_file(path: Path) -> list[ParsedTask]:
    fmt = _load_format()
    sections = fmt["file_structure"]["sections"]
    separator = fmt["file_structure"]["task_separator"]
    pattern = re.compile(fmt["task_block"]["metadata_line"]["pattern"])

    lines = path.read_text(encoding="utf-8").splitlines()
    tasks: list[ParsedTask] = []

    current_section: Optional[str] = None
    current_title: Optional[str] = None
    metadata_line_num: Optional[int] = None
    current_priority: Optional[str] = None
    current_date: Optional[str] = None
    current_id: Optional[int] = None
    desc_lines: list[str] = []
    in_task = False

    def _flush():
        if current_title and metadata_line_num is not None:
            tasks.append(ParsedTask(
                title=current_title,
                priority=current_priority,
                date=current_date,
                id=current_id,
                status=current_section,
                description="\n".join(desc_lines).strip(),
                metadata_line_num=metadata_line_num,
            ))
        elif current_title:
            print(
                f"Warning: skipping '{current_title}' — missing or malformed metadata",
                file=sys.stderr,
            )

    for i, line in enumerate(lines):
        stripped = line.strip()

        if stripped == sections["pending"]:
            if in_task:
                _flush()
                in_task = False
                current_title = None
                metadata_line_num = None
                desc_lines = []
            current_section = "todo"
            continue

        if stripped == sections["done"]:
            if in_task:
                _flush()
                in_task = False
                current_title = None
                metadata_line_num = None
                desc_lines = []
            current_section = "done"
            continue

        if stripped.startswith("### ") and current_section is not None:
            if in_task:
                _flush()
            current_title = stripped[4:].strip()
            metadata_line_num = None
            current_priority = None
            current_date = None
            current_id = None
            desc_lines = []
            in_task = True
            continue

        if in_task and metadata_line_num is None:
            m = pattern.match(stripped)
            if m:
                current_priority = m.group("priority")
                current_date = m.group("date")
                id_str = m.group("id")
                current_id = int(id_str) if id_str else None
                metadata_line_num = i
            continue

        if in_task and stripped == separator:
            _flush()
            in_task = False
            current_title = None
            metadata_line_num = None
            desc_lines = []
            continue

        if in_task and metadata_line_num is not None and stripped:
            desc_lines.append(line)

    if in_task:
        _flush()

    return tasks

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Task:
    id: str
    title: str
    due_at: datetime
    completed: bool = False
    notified: bool = False


def due_notifications(tasks: list[Task], now: datetime) -> list[str]:
    sent = []
    for task in tasks:
        if not task.completed and not task.notified and task.due_at <= now:
            task.notified = True
            sent.append(task.id)
    return sent


def sorted_open_tasks(tasks: list[Task]) -> list[Task]:
    return sorted((task for task in tasks if not task.completed), key=lambda task: task.due_at)

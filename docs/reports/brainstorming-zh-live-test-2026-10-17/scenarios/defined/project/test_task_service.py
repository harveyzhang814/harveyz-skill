from datetime import datetime

from task_service import Task, due_notifications, sorted_open_tasks


def test_due_notifications_once():
    task = Task("1", "Pay bill", datetime(2026, 10, 1, 12))
    assert due_notifications([task], datetime(2026, 10, 1, 12)) == ["1"]
    assert due_notifications([task], datetime(2026, 10, 1, 13)) == []


def test_open_tasks_sort_by_due_at():
    later = Task("2", "Later", datetime(2026, 10, 2))
    earlier = Task("1", "Earlier", datetime(2026, 10, 1))
    assert sorted_open_tasks([later, earlier]) == [earlier, later]

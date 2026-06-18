import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, ListItem

from hub.core.db import HubDB
from hub.core.projects import add_project
from hub.core.tasks import add_task, list_tasks
from hub.tui.panels.tasks import TasksPanel


def _make_app(db: HubDB) -> App:
    class _App(App):
        def compose(self) -> ComposeResult:
            yield TasksPanel(db)
    return _App()


async def test_tasks_panel_mounts(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    async with _make_app(db).run_test() as pilot:
        assert pilot.app.query_one(TasksPanel) is not None


async def test_tasks_panel_shows_tasks(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Task A", project="proj")
    add_task(db, title="Task B", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        items = panel.query(ListItem)
        assert len(items) == 2


async def test_tasks_panel_toggle_done(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Finish me", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.query_one("ListView").focus()
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()

    tasks = list_tasks(db, project="proj")
    assert tasks[0]["status"] == "done"


async def test_tasks_panel_new_task_input_appears(tmp_path):
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.focus()
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert len(panel.query(Input)) == 1


async def test_tasks_panel_new_task_saves(tmp_path):
    """Submitting the new-task input actually creates a task in the DB."""
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.focus()
        await pilot.press("ctrl+n")
        await pilot.pause()
        await pilot.press("M", "y", "space", "t", "a", "s", "k")
        await pilot.press("enter")
        await pilot.pause()

    tasks = list_tasks(db, project="proj")
    assert any(t["title"] == "My task" for t in tasks)


async def test_tasks_panel_toggle_done_to_todo(tmp_path):
    """Toggling a done task marks it back as todo."""
    from hub.core.tasks import mark_done
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    t = add_task(db, title="Already done", project="proj")
    mark_done(db, t["id"])

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        # done tasks appear after the "── DONE ──" separator
        lst = panel.query_one("ListView")
        lst.focus()
        # navigate past separator to the done task
        await pilot.press("down")  # separator
        await pilot.press("down")  # done task
        await pilot.press("space")
        await pilot.pause()

    tasks = list_tasks(db, project="proj")
    assert tasks[0]["status"] == "todo"


async def test_tasks_panel_delete_two_press(tmp_path):
    """First D sets confirm, second D actually deletes."""
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path="/tmp/proj")
    add_task(db, title="Delete me", project="proj")

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        lst = panel.query_one("ListView")
        lst.focus()
        await pilot.press("down")
        # first D — should NOT delete yet
        await pilot.press("ctrl+d")
        await pilot.pause()
        assert len(list_tasks(db, project="proj")) == 1
        # second ctrl+d — should delete
        await pilot.press("ctrl+d")
        await pilot.pause()

    assert len(list_tasks(db, project="proj")) == 0


async def test_ctrl_r_syncs_from_todo_md(tmp_path):
    """ctrl+r reads TODO.md and imports tasks into the panel."""
    from hub.core.todo_sync import sync_project as _real_sync  # noqa: F401

    db = HubDB(tmp_path / "hub.db")
    proj_path = tmp_path / "myproj"
    proj_path.mkdir()
    add_project(db, "myproj", path=str(proj_path))

    todo_md = proj_path / "TODO.md"
    todo_md.write_text(
        "## 🚧 待开发\n\n### Synced task\n**优先级**: P2 | **日期**: 2026-01-01\n\n---\n"
    )

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("myproj")
        await pilot.pause()
        panel.focus()
        await pilot.press("ctrl+r")
        await pilot.pause()

    tasks = list_tasks(db, project="myproj")
    assert any(t["title"] == "Synced task" for t in tasks)


async def test_ctrl_r_no_path_shows_warning(tmp_path):
    """ctrl+r on a project with no path shows a warning and does not crash."""
    db = HubDB(tmp_path / "hub.db")
    add_project(db, "nopath", path="")

    notifications = []

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("nopath")
        await pilot.pause()
        panel.focus()

        original_notify = pilot.app.notify
        pilot.app.notify = lambda msg, **kw: notifications.append(msg)

        await pilot.press("ctrl+r")
        await pilot.pause()

    assert any("path" in n.lower() or "no" in n.lower() for n in notifications)


async def test_ctrl_r_sync_error_shows_error_notification(tmp_path, monkeypatch):
    """ctrl+r shows an error notification and does not crash when sync_project raises."""
    import hub.tui.panels.tasks as tasks_mod

    db = HubDB(tmp_path / "hub.db")
    add_project(db, "proj", path=str(tmp_path / "proj"))
    (tmp_path / "proj").mkdir()

    monkeypatch.setattr(tasks_mod, "sync_project", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("disk full")))

    errors = []

    async with _make_app(db).run_test() as pilot:
        panel = pilot.app.query_one(TasksPanel)
        panel.refresh_project("proj")
        await pilot.pause()
        panel.focus()

        pilot.app.notify = lambda msg, **kw: errors.append((msg, kw.get("severity")))

        await pilot.press("ctrl+r")
        await pilot.pause()

    assert any("disk full" in msg for msg, _ in errors)
    assert any(sev == "error" for _, sev in errors)

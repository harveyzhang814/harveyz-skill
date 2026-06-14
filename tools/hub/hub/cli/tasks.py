import json
import sys
from typing import Optional

import typer

from hub.core.db import HubDB
from hub.core import tasks as task

app = typer.Typer(no_args_is_help=True)


def _out(data, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": True, "data": data}))


def _err(msg: str, json_out: bool) -> None:
    if json_out:
        print(json.dumps({"ok": False, "error": msg}))
    else:
        typer.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


@app.command("list")
def tasks_list(
    project:  Optional[str] = typer.Option(None, "--project",  "-p"),
    status:   Optional[str] = typer.Option(None, "--status",   "-s"),
    priority: Optional[str] = typer.Option(None, "--priority", "-P"),
    json_out: bool           = typer.Option(False, "--json"),
):
    """List tasks, optionally filtered."""
    db = HubDB()
    tasks = task.list_tasks(db, project=project, status=status, priority=priority)
    if json_out:
        _out(tasks, json_out)
    else:
        if not tasks:
            typer.echo("No tasks.")
            return
        for t in tasks:
            check = "✓" if t["status"] == "done" else "○"
            typer.echo(f"  [{t['id']:>4}] {check} [{t['priority']}] {t['title']}  ({t['project']})")


@app.command("add")
def tasks_add(
    title:    str           = typer.Argument(...),
    project:  str           = typer.Option(..., "--project", "-p"),
    priority: str           = typer.Option("P2", "--priority", "-P"),
    json_out: bool          = typer.Option(False, "--json"),
):
    """Add a new task."""
    db = HubDB()
    try:
        t = task.add_task(db, title=title, project=project, priority=priority)
    except ValueError as e:
        _err(str(e), json_out)
    if json_out:
        _out(t, json_out)
    else:
        typer.echo(f"✓ [{t['id']}] {t['title']}")


@app.command("done")
def tasks_done(
    task_id:  int  = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Mark a task as done."""
    db = HubDB()
    result = task.mark_done(db, task_id)
    if result is None:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ done: {result['title']}")


@app.command("update")
def tasks_update(
    task_id:  int            = typer.Argument(...),
    title:    Optional[str]  = typer.Option(None, "--title"),
    priority: Optional[str]  = typer.Option(None, "--priority"),
    status:   Optional[str]  = typer.Option(None, "--status"),
    json_out: bool           = typer.Option(False, "--json"),
):
    """Update task fields."""
    db = HubDB()
    result = task.update_task(db, task_id, title=title, priority=priority, status=status)
    if result is None:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ updated [{task_id}]")


@app.command("rm")
def tasks_rm(
    task_id:  int  = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Delete a task."""
    db = HubDB()
    deleted = task.delete_task(db, task_id)
    if not deleted:
        _err(f"Task {task_id} not found", json_out)
    if json_out:
        _out({"deleted": True}, json_out)
    else:
        typer.echo(f"✓ deleted [{task_id}]")

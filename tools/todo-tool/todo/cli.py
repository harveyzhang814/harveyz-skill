import json
import typer
from pathlib import Path

from .db import TodoDB, get_db_path
from .models import TaskCreate, TaskUpdate

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
app.add_typer(config_app, name="config")


def get_db() -> TodoDB:
    return TodoDB(db_path=get_db_path())


@app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    project: str = typer.Option(..., "--project", "-p", help="Project name"),
    priority: str = typer.Option("P2", "--priority", help="P0/P1/P2/P3"),
):
    """Add a new task."""
    db = get_db()
    task = db.create(TaskCreate(title=title, project=project, priority=priority))
    typer.echo(f"✓ [{task.id}] {task.title} added to {task.project}")


@app.command(name="list")
def list_tasks(
    project: str = typer.Option(None, "--project", "-p"),
    priority: str = typer.Option(None, "--priority"),
    as_json: bool = typer.Option(False, "--json"),
    show_done: bool = typer.Option(False, "--done"),
):
    """List tasks."""
    db = get_db()
    status = None if show_done else "todo"
    tasks = db.list_tasks(project=project, status=status, priority=priority)
    if as_json:
        typer.echo(json.dumps([t.model_dump() for t in tasks], indent=2))
        return
    if not tasks:
        typer.echo("No tasks found.")
        return
    current_project = None
    for t in tasks:
        if t.project != current_project:
            current_project = t.project
            typer.echo(f"\n{current_project}")
        typer.echo(f"  [{t.id}] {t.priority}  {t.title}")


@app.command()
def done(task_id: int = typer.Argument(..., help="Task ID")):
    """Mark a task as done."""
    db = get_db()
    task = db.update(task_id, TaskUpdate(status="done"))
    if task:
        typer.echo(f"✓ [{task.id}] {task.title} marked done")
    else:
        typer.echo(f"Task {task_id} not found", err=True)
        raise typer.Exit(1)


@app.command()
def show(task_id: int = typer.Argument(..., help="Task ID")):
    """Show a single task."""
    db = get_db()
    task = db.get(task_id)
    if task:
        typer.echo(f"[{task.id}] {task.title}")
        typer.echo(f"  Project:  {task.project}")
        typer.echo(f"  Priority: {task.priority}")
        typer.echo(f"  Status:   {task.status}")
        typer.echo(f"  Created:  {task.created_at}")
    else:
        typer.echo(f"Task {task_id} not found", err=True)
        raise typer.Exit(1)


@app.command()
def serve(port: int = typer.Option(8080, "--port", help="Port to listen on")):
    """Start the web UI server."""
    import uvicorn
    from .server import create_app
    typer.echo(f"Starting todo server on http://127.0.0.1:{port}")
    uvicorn.run(create_app(), host="127.0.0.1", port=port)


@config_app.command(name="set")
def config_set(key: str = typer.Argument(...), value: str = typer.Argument(...)):
    """Set a config value (e.g. db-path ~/Syncthing/todo/tasks.db)."""
    if key != "db-path":
        typer.echo(f"Unknown key: {key}. Available: db-path", err=True)
        raise typer.Exit(1)
    config_path = Path.home() / ".local" / "share" / "todo" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = json.loads(config_path.read_text()) if config_path.exists() else {}
    config["db_path"] = value
    config_path.write_text(json.dumps(config, indent=2))
    typer.echo(f"✓ db-path set to {value}")


@config_app.command(name="show")
def config_show():
    """Show current config."""
    config_path = Path.home() / ".local" / "share" / "todo" / "config.json"
    if config_path.exists():
        typer.echo(config_path.read_text())
    else:
        typer.echo('{"db_path": "~/.local/share/todo/tasks.db"}')


def main():
    app()

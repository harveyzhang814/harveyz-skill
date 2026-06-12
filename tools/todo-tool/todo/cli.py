import json
import typer
from pathlib import Path

from .db import TodoDB, get_db_path
from .models import ProjectCreate, ProjectUpdate, TaskCreate, TaskUpdate

app = typer.Typer(no_args_is_help=True)
config_app = typer.Typer(no_args_is_help=True)
project_app = typer.Typer(no_args_is_help=True)
app.add_typer(config_app, name="config")
app.add_typer(project_app, name="project")


def get_db() -> TodoDB:
    return TodoDB(db_path=get_db_path())


# ── project commands ──────────────────────────────────────────────────────────

@project_app.command(name="add")
def project_add(
    repo_name: str = typer.Argument(..., help="GitHub repo name (e.g. video-learner)"),
    path: str = typer.Option(None, "--path", help="Local directory path"),
):
    """Register a new project."""
    db = get_db()
    p = db.create_project(ProjectCreate(repo_name=repo_name, local_path=path))
    typer.echo(f"✓ Project '{p.repo_name}' added (id={p.id})")


@project_app.command(name="list")
def project_list():
    """List all projects."""
    db = get_db()
    projects = db.list_projects()
    if not projects:
        typer.echo("No projects found.")
        return
    for p in projects:
        path_str = f"  {p.local_path}" if p.local_path else ""
        typer.echo(f"  [{p.id}] {p.repo_name}{path_str}")


@project_app.command(name="set-path")
def project_set_path(
    repo_name: str = typer.Argument(..., help="Project repo name"),
    local_path: str = typer.Argument(..., help="Local directory path"),
):
    """Set the local path for a project."""
    db = get_db()
    project = db.get_project_by_name(repo_name)
    if not project:
        typer.echo(f"Project '{repo_name}' not found", err=True)
        raise typer.Exit(1)
    updated = db.update_project(project.id, ProjectUpdate(local_path=local_path))
    typer.echo(f"✓ '{updated.repo_name}' local path set to {updated.local_path}")


# ── task commands ─────────────────────────────────────────────────────────────

@app.command()
def add(
    title: str = typer.Argument(..., help="Task title"),
    project: str = typer.Option(..., "--project", "-p", help="Project repo name"),
    priority: str = typer.Option("P2", "--priority", help="P0/P1/P2/P3"),
):
    """Add a new task."""
    db = get_db()
    try:
        task = db.create(TaskCreate(title=title, project=project, priority=priority))
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)
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
def sync(
    project: str = typer.Argument(..., help="Project repo name"),
    path: str = typer.Option(None, "--path", help="Override local_path for this sync"),
):
    """Sync TODO.md into SQLite. Writes IDs back to TODO.md."""
    db = get_db()
    proj = db.get_project_by_name(project)
    if not proj:
        typer.echo(f"Project '{project}' not found", err=True)
        raise typer.Exit(1)

    project_path = Path(path) if path else (Path(proj.local_path) if proj.local_path else None)
    if not project_path:
        typer.echo(
            f"No path for '{project}'. Use --path or: todo project set-path {project} <path>",
            err=True,
        )
        raise typer.Exit(1)

    todo_md = project_path / "TODO.md"
    if not todo_md.exists():
        typer.echo(f"TODO.md not found at {todo_md}", err=True)
        raise typer.Exit(1)

    inserted, updated = db.sync_from_file(todo_md, proj.id)
    typer.echo(f"✓ 同步完成：{inserted} 条新增，{updated} 条更新")


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


if __name__ == "__main__":
    main()

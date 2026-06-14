import json
import os
import sys
from pathlib import Path
from typing import Optional

import typer

from hub.core.db import HubDB
from hub.core import projects as proj

app = typer.Typer(no_args_is_help=True)

_DEFAULT_MD = Path.home() / ".hskill" / "public" / "PROJECTS.md"


def _md_path() -> Path:
    if env := os.environ.get("HUB_MD_PATH"):
        return Path(env)
    return _DEFAULT_MD


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
def projects_list(json_out: bool = typer.Option(False, "--json")):
    """List all registered projects."""
    db = HubDB()
    projects = proj.list_projects(db)
    if json_out:
        _out(projects, json_out)
    else:
        if not projects:
            typer.echo("No projects. Use: hub projects add <name> --path <path>")
            return
        for p in projects:
            typer.echo(f"  {p['name']:<24} {p['path'] or ''}")
            if p.get("description"):
                typer.echo(f"    {p['description']}")


@app.command("add")
def projects_add(
    name: str = typer.Argument(..., help="Project name (GitHub repo name)"),
    path: str = typer.Option("", "--path", help="Local directory path"),
    description: str = typer.Option("", "--desc", help="Short description"),
    json_out: bool = typer.Option(False, "--json"),
):
    """Register or update a project."""
    db = HubDB()
    result = proj.add_project(db, name, path=path, description=description, md_path=_md_path())
    if json_out:
        _out(result, json_out)
    else:
        typer.echo(f"✓ {name}")


@app.command("path")
def projects_path(
    name: str = typer.Argument(...),
    json_out: bool = typer.Option(False, "--json"),
):
    """Print the local path for a project (for shell cd / agent use)."""
    db = HubDB()
    p = proj.get_project_path(db, name)
    if p is None:
        _err(f"Project '{name}' not found", json_out)
    if json_out:
        _out(p, json_out)
    else:
        print(p)


@app.command("sync")
def projects_sync(json_out: bool = typer.Option(False, "--json")):
    """Re-scan configured dirs and update PROJECTS.md. (Requires p-launch config.)"""
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).parents[4] / "p-launch"))
        from p_launch import read_project_dirs, collect_repos, sync_to_index
        dirs = read_project_dirs()
        repos = collect_repos(dirs)
        sync_to_index(repos, _md_path())
        if json_out:
            _out({"scanned": len(repos)}, json_out)
        else:
            typer.echo(f"✓ Scanned {len(repos)} repos")
    except ImportError:
        _err("p-launch not installed; cannot auto-scan", json_out)

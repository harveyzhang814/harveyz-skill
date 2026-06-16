import sys
from pathlib import Path
from typing import Optional

import typer

from hub.core.db import HubDB
from hub.core.projects import get_project_path
from hub.tui.git import (
    fetch_repo,
    get_branches,
    get_recent_commits,
    get_working_tree,
    is_git_with_remote,
    pull_branch,
    push_branch,
)

app = typer.Typer(no_args_is_help=True)


def _resolve_path(project: Optional[str]) -> Path:
    if project:
        db = HubDB()
        p = get_project_path(db, project)
        if not p:
            typer.echo(f"Error: project '{project}' not found", err=True)
            raise SystemExit(1)
        return Path(p)
    return Path.cwd()


@app.command("status")
def git_status(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    commits: int = typer.Option(5, "--commits", "-n", help="Number of recent commits to show"),
):
    """Show branch, working tree, and recent commits."""
    path = _resolve_path(project)

    branches = get_branches(path)
    current = next((b for b in branches if b["is_current"]), None)
    wt = get_working_tree(path)
    recent = get_recent_commits(path, n=commits)

    typer.echo(f"\n{path.name}")

    typer.echo("\nBRANCH")
    if current:
        typer.echo(f"  local    {current['name']}")
        if current["upstream"]:
            typer.echo(f"  tracking {current['upstream']}")
            parts = []
            if current["ahead"]:
                parts.append(f"↑{current['ahead']}")
            if current["behind"]:
                parts.append(f"↓{current['behind']}")
            typer.echo(f"  sync     {' '.join(parts) if parts else 'up to date'}")
        else:
            typer.echo("  tracking none (local only)")
    else:
        typer.echo("  not a git repository")

    typer.echo("\nWORKING TREE")
    total = wt["modified"] + wt["new"] + wt["deleted"]
    if total == 0:
        typer.echo("  clean")
    else:
        parts = []
        if wt["modified"]:
            parts.append(f"{wt['modified']} modified")
        if wt["new"]:
            parts.append(f"{wt['new']} new")
        if wt["deleted"]:
            parts.append(f"{wt['deleted']} deleted")
        typer.echo(f"  {', '.join(parts)}")

    if recent:
        typer.echo("\nRECENT COMMITS")
        for c in recent:
            msg = c["msg"][:50] + "…" if len(c["msg"]) > 50 else c["msg"]
            typer.echo(f"  {c['sha']}  {msg}  ({c['date']})")

    typer.echo("")


@app.command("fetch")
def git_fetch(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """Fetch all remotes."""
    path = _resolve_path(project)
    if not is_git_with_remote(path):
        typer.echo("No remote configured — nothing to fetch.", err=True)
        raise SystemExit(1)
    typer.echo(f"Fetching {path.name}…")
    fetch_repo(path)
    typer.echo("Done.")


@app.command("branches")
def git_branches(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
):
    """List branches with upstream sync status."""
    path = _resolve_path(project)
    branches = get_branches(path)
    if not branches:
        typer.echo("No branches found (not a git repository?).")
        return
    for b in branches:
        marker = "*" if b["is_current"] else " "
        if b["is_local_only"]:
            sync = "(local only)"
        else:
            parts = []
            if b["ahead"]:
                parts.append(f"↑{b['ahead']}")
            if b["behind"]:
                parts.append(f"↓{b['behind']}")
            sync = " ".join(parts) if parts else "up to date"
        typer.echo(f"  {marker} {b['name']:<32} {sync}")


@app.command("pull")
def git_pull(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to pull (default: current branch)"),
):
    """Pull a branch from its remote upstream."""
    path = _resolve_path(project)
    branches = get_branches(path)
    if not branches:
        typer.echo("Error: not a git repository", err=True)
        raise SystemExit(1)

    if branch is None:
        b = next((x for x in branches if x["is_current"]), None)
        if b is None:
            typer.echo("Error: no current branch found", err=True)
            raise SystemExit(1)
    else:
        b = next((x for x in branches if x["name"] == branch), None)
        if b is None:
            typer.echo(f"Error: branch '{branch}' not found", err=True)
            raise SystemExit(1)

    if b["is_local_only"]:
        typer.echo(f"Error: branch '{b['name']}' has no upstream", err=True)
        raise SystemExit(1)
    if b["ahead"] > 0 and b["behind"] > 0:
        typer.echo(f"Error: branch '{b['name']}' is diverged — rebase or merge first", err=True)
        raise SystemExit(1)
    if b["behind"] == 0:
        typer.echo(f"branch '{b['name']}' is already up to date")
        return

    msg = pull_branch(path, b["name"])
    if msg.startswith("⚠") or "failed" in msg:
        typer.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    typer.echo(msg)


@app.command("push")
def git_push(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Project name"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b", help="Branch to push (default: current branch)"),
):
    """Push a branch to its remote upstream."""
    path = _resolve_path(project)
    branches = get_branches(path)
    if not branches:
        typer.echo("Error: not a git repository", err=True)
        raise SystemExit(1)

    if branch is None:
        b = next((x for x in branches if x["is_current"]), None)
        if b is None:
            typer.echo("Error: no current branch found", err=True)
            raise SystemExit(1)
    else:
        b = next((x for x in branches if x["name"] == branch), None)
        if b is None:
            typer.echo(f"Error: branch '{branch}' not found", err=True)
            raise SystemExit(1)

    if b["is_local_only"]:
        typer.echo(f"Error: branch '{b['name']}' has no upstream", err=True)
        raise SystemExit(1)
    if b["ahead"] > 0 and b["behind"] > 0:
        typer.echo(f"Error: branch '{b['name']}' is diverged — rebase or merge first", err=True)
        raise SystemExit(1)
    if b["ahead"] == 0:
        typer.echo(f"branch '{b['name']}' is already up to date")
        return

    msg = push_branch(path, b["name"])
    if msg.startswith("⚠") or "failed" in msg:
        typer.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    typer.echo(msg)

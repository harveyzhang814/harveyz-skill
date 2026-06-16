import json
import sys
import typer

from hub.cli import git as git_cmd
from hub.cli import projects as proj_cmd
from hub.cli import tasks as task_cmd

app = typer.Typer(
    name="hub",
    no_args_is_help=False,
    add_completion=False,
)
app.add_typer(proj_cmd.app, name="projects")
app.add_typer(task_cmd.app, name="tasks")
app.add_typer(git_cmd.app, name="git")

import sys


def _get_db():
    from hub.core.db import HubDB
    return HubDB()


def main():
    from hub.core.migrate import needs_migration, run_migration
    from hub.core.todo_sync import sync_all_projects

    db = _get_db()

    if needs_migration():
        n = run_migration(db)
        if n:
            import typer
            typer.echo(f"hub: migrated {n} tasks from todo-tool ✓")

    if len(sys.argv) == 1:
        from hub.core.todo_sync import sync_all_projects
        from hub.tui.app import HubApp
        try:
            sync_all_projects(db)
        except Exception:
            pass
        HubApp().run()
        return
    from hub.cli import app
    app()


if __name__ == "__main__":
    main()

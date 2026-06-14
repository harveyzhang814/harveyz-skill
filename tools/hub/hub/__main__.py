import sys


def main():
    from hub.core.db import HubDB
    from hub.core.migrate import needs_migration, run_migration

    db = HubDB()
    if needs_migration():
        n = run_migration(db)
        if n:
            import typer
            typer.echo(f"hub: migrated {n} tasks from todo-tool ✓")

    if len(sys.argv) == 1:
        from hub.tui.app import HubApp
        HubApp().run()
        return
    from hub.cli import app
    app()


if __name__ == "__main__":
    main()

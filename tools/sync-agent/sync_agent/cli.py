import typer

app = typer.Typer()


@app.command()
def hello(name: str = "world"):
    """Say hello."""
    typer.echo(f"Hello {name}")


if __name__ == "__main__":
    app()

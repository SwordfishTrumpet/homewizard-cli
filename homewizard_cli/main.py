"""CLI entry point for homewizard-cli."""

import sys

import typer
from rich.console import Console

from . import __version__
from .commands import data, power, info, identify, system
from .errors import P1Error

app = typer.Typer(
    name="homewizard-cli",
    help="HomeWizard P1 Meter CLI",
)

# Register subcommands
app.add_typer(data.app, name="data")
app.add_typer(power.app, name="power")
app.add_typer(info.app, name="info")
app.add_typer(identify.app, name="identify")
app.add_typer(system.app, name="system")


def _version_callback(value: bool):
    if value:
        typer.echo(f"homewizard-cli version: {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version",
        is_eager=True,
        callback=_version_callback,
    ),
):
    """HomeWizard P1 Meter CLI."""
    pass


def main():
    """Main entry point with error handling."""
    try:
        app()
    except P1Error as e:
        console = Console(stderr=True)
        console.print(str(e), style="red")
        sys.exit(e.code)
    except Exception as e:
        console = Console(stderr=True)
        console.print(f"Error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()

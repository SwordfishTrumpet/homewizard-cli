"""CLI entry point for homewizard-cli."""

import asyncio
import signal
import sys
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .client import P1Client
from .commands import data, power, info, identify, system
from .errors import P1Error
from .format import Format, write_data, get_format
from .models import DataResponse

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


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        help="Show version",
        is_eager=True,
        callback=_version_callback,
    ),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
):
    """HomeWizard P1 Meter CLI."""
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_default_async(host, timeout, format))


async def _default_async(host, timeout, format):
    console = Console()
    output_format = get_format(format, console.is_terminal)
    async with P1Client(host, timeout) as client:
        data = await client.get_json("/api/v1/data", DataResponse)
        write_data(data, output_format, console)


def _signal_handler(signum, frame):
    """Handle SIGINT for clean Ctrl+C exit."""
    sys.exit(0)


def _setup_signal_handlers():
    """Register signal handlers."""
    signal.signal(signal.SIGINT, _signal_handler)


def main():
    """Main entry point with error handling."""
    _setup_signal_handlers()
    try:
        app()
    except P1Error as e:
        console = Console(stderr=True)
        console.print(str(e), style="red")
        sys.exit(e.code)
    except SystemExit:
        raise
    except Exception as e:
        console = Console(stderr=True)
        console.print(f"Error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()

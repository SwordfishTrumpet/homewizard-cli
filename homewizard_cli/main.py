"""CLI entry point for homewizard-cli."""

import asyncio
import os
import signal
import sys
from typing import Optional

import typer
from rich.console import Console

from . import __version__
from .client import P1Client
from .config import load_config
from .commands import (
    data,
    power,
    info,
    identify,
    system,
    ping as ping_cmd,
    energy,
    gas,
    quality,
    telegram,
    discover,
)
from .errors import P1Error
from .format import write_data, get_format
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
app.add_typer(ping_cmd.app, name="ping")
app.add_typer(energy.app, name="energy")
app.add_typer(gas.app, name="gas")
app.add_typer(quality.app, name="quality")
app.add_typer(telegram.app, name="telegram")
app.add_typer(discover.app, name="discover")


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
    host: Optional[str] = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: Optional[float] = typer.Option(
        None, "--timeout", "-t", help="HTTP timeout"
    ),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Output format"),
    proxy: Optional[str] = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI colors"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-error output"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show HTTP request details"
    ),
    cache: bool = typer.Option(True, "--cache", "-c", help="Use metadata cache"),
):
    """HomeWizard P1 Meter CLI."""
    # Priority: CLI arg > config file > hardcoded default
    cfg = load_config()
    if host is None:
        host = cfg.host or "192.168.68.109"
    if timeout is None:
        timeout = cfg.timeout or 3.0
    if format is None:
        format = cfg.format or "auto"

    if no_color:
        os.environ["NO_COLOR"] = "1"
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(_default_async(host, timeout, format, proxy))


async def _default_async(host, timeout, format, proxy=None):
    console = Console()
    output_format = get_format(format, console.is_terminal)
    async with P1Client(host, timeout, proxy=proxy) as client:
        data = await client.get_json("/api/v1/data", DataResponse)
        write_data(data, output_format, console)


def _signal_handler(signum, frame):
    """Handle SIGINT for clean Ctrl+C exit."""
    sys.stderr.write("\n")
    sys.stderr.flush()
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
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        console = Console(stderr=True)
        console.print(f"Error: {e}", style="red")
        sys.exit(1)


if __name__ == "__main__":
    main()

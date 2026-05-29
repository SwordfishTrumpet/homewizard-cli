"""CLI entry point for homewizard-cli."""

import asyncio
import os
import sys

import typer
from rich.console import Console

from . import __version__
from .client_factory import resolve_client, convert_v2_measurement
from .config import load_config, DEFAULT_HOST, DEFAULT_TIMEOUT, DEFAULT_FORMAT
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
    export,
    config as config_cmd,
    dashboard,
    serve,
    reboot as reboot_cmd,
    pair as pair_cmd,
    users as users_cmd,
    batteries as batteries_cmd,
)
from .errors import P1Error
from .format import write_data, get_format
from .models import DataResponse

app = typer.Typer(
    name="homewizard-cli",
    help="HomeWizard P1 Meter CLI",
    add_completion=True,
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
app.add_typer(export.app, name="export")
app.add_typer(config_cmd.app, name="config")
app.add_typer(dashboard.app, name="dashboard")
app.add_typer(serve.app, name="serve")
app.add_typer(reboot_cmd.app, name="reboot")
app.add_typer(pair_cmd.app, name="pair")
app.add_typer(users_cmd.app, name="users")
app.add_typer(batteries_cmd.app, name="batteries")


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
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float | None = typer.Option(None, "--timeout", "-t", help="HTTP timeout"),
    format: str | None = typer.Option(None, "--format", "-f", help="Output format"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable ANSI colors"),
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Suppress non-error output"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show HTTP request details"
    ),
    api_version: str = typer.Option(
        "v2",
        "--api-version",
        help="API version (v1|v2)",
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """HomeWizard P1 Meter CLI."""
    # Priority: CLI arg > config file > hardcoded default
    cfg = load_config()
    if host is None:
        host = cfg.host or DEFAULT_HOST
    if timeout is None:
        timeout = cfg.timeout or DEFAULT_TIMEOUT
    if format is None:
        format = cfg.format or DEFAULT_FORMAT

    if no_color:
        os.environ["NO_COLOR"] = "1"
    if ctx.invoked_subcommand is not None:
        return
    asyncio.run(
        _default_async(
            host=host,
            timeout=timeout,
            format=format,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _default_async(
    host: str,
    timeout: float,
    format: str,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
) -> None:
    console = Console()
    output_format = get_format(format, console.is_terminal)
    client = resolve_client(
        api_version, host, timeout, token=token, verify_cert=not no_verify, proxy=proxy
    )
    async with client as c:
        if api_version == "v2":
            from .models.v2 import MeasurementV2

            m = await c.get_json_v2("/api/measurement", MeasurementV2)
            data = convert_v2_measurement(m)
        else:
            data = await c.get_json("/api/v1/data", DataResponse)
        write_data(data, output_format, console)


def _signal_handler(signum, frame):
    """Handle SIGINT and SIGTERM for graceful shutdown."""
    sys.exit(0)


def _setup_signal_handlers():
    """Register signal handlers for graceful shutdown."""
    import signal

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


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

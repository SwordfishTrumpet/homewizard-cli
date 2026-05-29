"""homewizard-cli power command."""

import asyncio
from collections import deque

import typer
from rich.console import Console

from ..client_factory import resolve_client, convert_v2_measurement, API_VERSIONS
from ..models import DataResponse
from ..models.v2 import MeasurementV2
from ..format import get_format, write_data
from ..expr import evaluate_until
from ..config import resolve_host

_CHARS = ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█"]


def _sparkline(values: list[float], width: int = 20) -> str:
    if not values:
        return ""
    recent = values[-width:]
    mn, mx = min(recent), max(recent)
    rng = mx - mn or 1
    return "".join(_CHARS[min(7, int(8 * (v - mn) / rng))] for v in recent)


app = typer.Typer()


@app.callback(invoke_without_command=True)
def power(
    watch: float | None = typer.Option(
        None, "--watch", "-w", help="Poll interval in seconds"
    ),
    full: bool = typer.Option(False, "--full", help="Show all power details"),
    color: bool = typer.Option(False, "--color", help="Color output by import/export"),
    sparkline: bool = typer.Option(
        False, "--sparkline", help="Show sparkline of recent power readings"
    ),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    until: str | None = typer.Option(
        None, "--until", help="Exit when expression is true"
    ),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Display real-time power information."""
    asyncio.run(
        _power_async(
            watch,
            full,
            color,
            sparkline,
            format,
            until,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _power_async(
    watch: float | None,
    full: bool,
    color: bool,
    sparkline: bool,
    format_str: str,
    until: str | None,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    if watch is not None and watch < 1.0:
        console.print(
            f"Warning: Polling interval {watch}s is below recommended minimum (1.0s).\n"
            "         Device may become unresponsive.",
            style="yellow",
        )
    output_format = get_format(format_str, console.is_terminal)
    values: deque[float] = deque(maxlen=20)

    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )

    async with client as c:
        while True:
            if api_version == "v2":
                m = await c.get_json_v2("/api/measurement", MeasurementV2)
                data = convert_v2_measurement(m)
            else:
                data = await c.get_json("/api/v1/data", DataResponse)

            if sparkline:
                values.append(data.active_power_w)

            if until and evaluate_until(data.model_dump(), until):
                console.print(f"Condition met: {until}", style="green")
                raise typer.Exit(code=10)

            if full:
                imported = max(data.active_power_w, 0)
                exported = abs(min(data.active_power_w, 0))
                style = "green" if data.active_power_w < 0 else "red" if color else None
                console.print(f"Net:      {data.active_power_w} W", style=style)
                console.print(f"Import:     {imported} W")
                console.print(f"Export:    {exported} W")
                if data.active_voltage_l1_v:
                    console.print(f"Voltage:  {data.active_voltage_l1_v} V")
                if data.active_current_l1_a:
                    console.print(f"Current:  {data.active_current_l1_a} A")
                if sparkline:
                    console.print(f"Trend:    {_sparkline(list(values))}")
            elif format_str != "auto" or not console.is_terminal:
                write_data(data, output_format, console)
            else:
                direction = "exporting" if data.active_power_w < 0 else "importing"
                style = "green" if data.active_power_w < 0 else "red" if color else None
                console.print(f"{data.active_power_w} W  ({direction})", style=style)
                if sparkline:
                    console.print(f"          {_sparkline(list(values))}")

            if watch is None:
                break

            await asyncio.sleep(watch)
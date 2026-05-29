"""homewizard-cli gas command."""

import asyncio

import typer
from rich.console import Console

from ..client_factory import resolve_client, convert_v2_measurement, API_VERSIONS
from ..config import resolve_host, load_config
from ..models import DataResponse
from ..models.v2 import MeasurementV2
from ..util import format_p1_timestamp

app = typer.Typer()


@app.callback(invoke_without_command=True)
def gas(
    full: bool = typer.Option(False, "--full", help="Show all gas details"),
    watch: float | None = typer.Option(None, "--watch", "-w", help="Poll interval"),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Display gas consumption."""
    asyncio.run(
        _gas_async(
            full,
            watch,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _gas_async(
    full: bool,
    watch: float | None,
    host: str | None,
    request_timeout: float,
    proxy: str | None,
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

            if full:
                if data.total_gas_m3 is not None:
                    console.print(f"Total:     {data.total_gas_m3:,.2f} m\u00b3")
                else:
                    console.print("Total:     \u2014")
                if data.gas_timestamp is not None:
                    ts_fmt = load_config().timestamp_format
                    console.print(
                        f"Last read: {format_p1_timestamp(data.gas_timestamp, ts_fmt)}"
                    )
                if data.gas_unique_id:
                    console.print(f"Meter ID:  {data.gas_unique_id}")
            else:
                if data.total_gas_m3 is not None:
                    console.print(f"{data.total_gas_m3:,.2f} m\u00b3")
                else:
                    console.print("\u2014")
            if watch is None:
                break
            await asyncio.sleep(watch)

"""homewizard-cli water command."""

import asyncio

import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import load_config, resolve_host
from ..models import Measurement
from ..storage import _setup_store
from ..util import format_p1_timestamp

app = typer.Typer()


def _find_water_device(data: Measurement) -> dict | None:
    for dev in data.external:
        if dev.type == "water_meter":
            return {
                "value": dev.value,
                "timestamp": dev.timestamp,
                "unique_id": dev.unique_id,
            }
    return None


@app.callback(invoke_without_command=True)
def water(
    full: bool = typer.Option(False, "--full", help="Show all water details"),
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
    db: str | None = typer.Option(
        None, "--db", help="SQLite database path for historical storage"
    ),
):
    """Display water meter readings."""
    asyncio.run(
        _water_async(
            full,
            watch,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            db=db,
        )
    )


async def _water_async(
    full: bool,
    watch: float | None,
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    db: str | None = None,
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
        store, serial = await _setup_store(db, api_version, c)
        while True:
            if api_version == "v2":
                data = await c.get_json_v2("/api/measurement", Measurement)
            else:
                data = await c.get_json("/api/v1/data", Measurement)
            if store and serial:
                store.append(data.model_dump(), serial)

            water = _find_water_device(data)
            if water is None:
                console.print("No water meter found.", style="yellow")
            elif full:
                console.print(f"Total:     {water['value']:,.2f} m\u00b3")
                if water["timestamp"]:
                    ts_fmt = load_config().timestamp_format
                    console.print(
                        f"Last read: {format_p1_timestamp(water['timestamp'], ts_fmt)}"
                    )
                if water["unique_id"]:
                    console.print(f"Meter ID:  {water['unique_id']}")
            else:
                console.print(f"{water['value']:,.2f} m\u00b3")

            if watch is None:
                break
            await asyncio.sleep(watch)

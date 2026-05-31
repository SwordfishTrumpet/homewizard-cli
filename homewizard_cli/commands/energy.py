"""homewizard-cli energy command."""

import asyncio

import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import Measurement
from ..storage import _setup_store

app = typer.Typer()


@app.callback(invoke_without_command=True)
def energy(
    tariffs: bool = typer.Option(False, "--tariffs", help="Show tariff breakdown"),
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
    """Display cumulative energy readings."""
    asyncio.run(
        _energy_async(
            tariffs,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            db=db,
        )
    )


async def _energy_async(
    tariffs: bool,
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
        if api_version == "v2":
            data = await c.get_json_v2("/api/measurement", Measurement)
        else:
            data = await c.get_json("/api/v1/data", Measurement)
        if store and serial:
            store.append(data.model_dump(), serial)

        net = data.total_power_import_kwh - data.total_power_export_kwh
        direction = "consumed" if net >= 0 else "produced"

        console.print(f"Import:  {data.total_power_import_kwh:,.2f} kWh")
        console.print(f"Export:  {data.total_power_export_kwh:,.2f} kWh")
        console.print(f"Net:     {abs(net):,.2f} kWh {direction}")

        if tariffs:
            console.print("")
            console.print(
                f"T1 (peak):     Import: {data.total_power_import_t1_kwh:,.2f}  "
                f"Export: {data.total_power_export_t1_kwh:,.2f}"
            )
            console.print(
                f"T2 (off-peak): Import: {data.total_power_import_t2_kwh:,.2f}  "
                f"Export: {data.total_power_export_t2_kwh:,.2f}"
            )
            if data.total_power_import_t3_kwh is not None:
                console.print(
                    f"T3:            Import: {data.total_power_import_t3_kwh:,.2f}  "
                    f"Export: {data.total_power_export_t3_kwh:,.2f}"
                )
            if data.total_power_import_t4_kwh is not None:
                console.print(
                    f"T4:            Import: {data.total_power_import_t4_kwh:,.2f}  "
                    f"Export: {data.total_power_export_t4_kwh:,.2f}"
                )

"""homewizard-cli info command."""

import asyncio

import typer

from ..util import _loads_json
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import Measurement
from ..models.v2 import DeviceInfoV2, SystemV2

app = typer.Typer()


@app.callback(invoke_without_command=True)
def info(
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
    """Display device information."""
    asyncio.run(
        _info_async(
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _info_async(
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
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
        if api_version == "v2":
            device = await c.get_json_v2("/api", DeviceInfoV2)
            system = await c.get_json_v2("/api/system", SystemV2)
            console.print(f"Product:     {device.product_name or 'N/A'}")
            console.print(f"Type:        {device.product_type or 'N/A'}")
            console.print(f"Serial:      {device.serial or 'N/A'}")
            console.print(f"Firmware:    {device.firmware_version or 'N/A'}")
            console.print(f"API:         {device.api_version or 'N/A'}")
            console.print(
                f"WiFi:        {system.wifi_ssid or 'N/A'} "
                f"({system.wifi_rssi_db or '?'} dBm)"
            )
            console.print(
                f"Cloud:       {'enabled' if system.cloud_enabled else 'disabled'}"
            )
        else:
            raw = await c.get("/api/")
            device = _loads_json(raw)
            system_raw = await c.get("/api/v1/system")
            system = _loads_json(system_raw)
            data = await c.get_json("/api/v1/data", Measurement)
            console.print(f"Product:     {device.get('product_name', 'N/A')}")
            console.print(f"Type:        {device.get('product_type', 'N/A')}")
            console.print(f"Serial:      {device.get('serial', 'N/A')}")
            console.print(f"Firmware:    {device.get('firmware_version', 'N/A')}")
            console.print(f"API:         {device.get('api_version', 'N/A')}")
            console.print(f"WiFi:        {data.wifi_ssid} ({data.wifi_strength}%)")
            console.print(f"Meter:       {data.meter_model}")
            console.print(f"DSMR:        {data.smr_version / 10}")
            console.print(
                f"Cloud:       "
                f"{'enabled' if system.get('cloud_enabled') else 'disabled'}"
            )

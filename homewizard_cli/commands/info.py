"""homewizard-cli info command."""

import asyncio
import json

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse

app = typer.Typer()


@app.command()
def info(
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Display device information."""
    asyncio.run(_info_async(host, timeout))


async def _info_async(host, timeout):
    console = Console()

    async with P1Client(host, timeout) as client:
        # Get device info from /api/
        api_info = await client.get("/api/")
        device = json.loads(api_info)

        # Get system info
        system_info = await client.get("/api/v1/system")
        system = json.loads(system_info)

        # Get data for meter model
        data = await client.get_json("/api/v1/data", DataResponse)

        console.print(f"Product:     {device.get('product_name', 'N/A')}")
        console.print(f"Type:        {device.get('product_type', 'N/A')}")
        console.print(f"Serial:      {device.get('serial', 'N/A')}")
        console.print(f"Firmware:    {device.get('firmware_version', 'N/A')}")
        console.print(f"API:         {device.get('api_version', 'N/A')}")
        console.print(f"WiFi:        {data.wifi_ssid} ({data.wifi_strength}%)")
        console.print(f"Meter:       {data.meter_model}")
        console.print(f"DSMR:        {data.smr_version / 10}")
        console.print(
            f"Cloud:       {'enabled' if system.get('cloud_enabled') else 'disabled'}"
        )

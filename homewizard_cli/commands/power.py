"""homewizard-cli power command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse

app = typer.Typer()


@app.callback(invoke_without_command=True)
def power(
    watch: Optional[float] = typer.Option(
        None, "--watch", "-w", help="Poll interval in seconds"
    ),
    full: bool = typer.Option(False, "--full", help="Show all power details"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Display real-time power information."""
    asyncio.run(_power_async(watch, full, host, timeout))


async def _power_async(watch, full, host, timeout):
    console = Console()

    async with P1Client(host, timeout) as client:
        while True:
            data = await client.get_json("/api/v1/data", DataResponse)

            if full:
                console.print(f"Net:      {data.active_power_w} W")
                if data.active_voltage_l1_v:
                    console.print(f"Voltage:  {data.active_voltage_l1_v} V")
                if data.active_current_l1_a:
                    console.print(f"Current:  {data.active_current_l1_a} A")
            else:
                direction = "exporting" if data.active_power_w < 0 else "importing"
                console.print(f"{data.active_power_w} W  ({direction})")

            if watch is None:
                break

            await asyncio.sleep(watch)

"""homewizard-cli quality command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse

app = typer.Typer()


@app.command()
def quality(
    watch: Optional[float] = typer.Option(None, "--watch", "-w", help="Poll interval"),
    alert: bool = typer.Option(False, "--alert", help="Only print when counts change"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL"),
):
    """Display power quality information."""
    asyncio.run(_quality_async(watch, alert, host, timeout, proxy))


async def _quality_async(watch, alert, host, timeout, proxy):
    console = Console()
    previous = None
    async with P1Client(host, timeout, proxy=proxy) as client:
        while True:
            data = await client.get_json("/api/v1/data", DataResponse)
            current = (
                data.voltage_sag_l1_count,
                data.voltage_swell_l1_count,
                data.any_power_fail_count,
                data.long_power_fail_count,
            )
            if alert and previous == current:
                if watch is None:
                    break
                await asyncio.sleep(watch)
                continue

            console.print(f"Voltage Sags:    {data.voltage_sag_l1_count or 0}")
            console.print(f"Voltage Swells:  {data.voltage_swell_l1_count or 0}")
            console.print(f"Short Failures:  {data.any_power_fail_count or 0}")
            console.print(f"Long Failures:   {data.long_power_fail_count or 0}")
            previous = current

            if watch is None:
                break
            await asyncio.sleep(watch)

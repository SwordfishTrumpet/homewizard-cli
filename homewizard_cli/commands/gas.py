"""homewizard-cli gas command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse
from ..util import format_p1_timestamp

app = typer.Typer()


@app.callback(invoke_without_command=True)
def gas(
    full: bool = typer.Option(False, "--full", help="Show all gas details"),
    watch: Optional[float] = typer.Option(None, "--watch", "-w", help="Poll interval"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL"),
):
    """Display gas consumption."""
    asyncio.run(_gas_async(full, watch, host, timeout, proxy))


async def _gas_async(full, watch, host, timeout, proxy):
    console = Console()
    async with P1Client(host, timeout, proxy=proxy) as client:
        while True:
            data = await client.get_json("/api/v1/data", DataResponse)
            if full:
                if data.total_gas_m3 is not None:
                    console.print(f"Total:     {data.total_gas_m3:,.2f} m³")
                else:
                    console.print("Total:     —")
                if data.gas_timestamp is not None:
                    console.print(
                        f"Last read: {format_p1_timestamp(data.gas_timestamp)}"
                    )
                if data.gas_unique_id:
                    console.print(f"Meter ID:  {data.gas_unique_id}")
            else:
                if data.total_gas_m3 is not None:
                    console.print(f"{data.total_gas_m3:,.2f} m³")
                else:
                    console.print("—")
            if watch is None:
                break
            await asyncio.sleep(watch)

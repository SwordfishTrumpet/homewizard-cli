"""homewizard-cli data command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse
from ..format import Format, write_data, get_format

app = typer.Typer()


@app.command()
def data(
    watch: Optional[float] = typer.Option(
        None, "--watch", "-w", help="Poll interval in seconds"
    ),
    fields: Optional[str] = typer.Option(
        None, "--fields", help="Comma-separated field list"
    ),
    format: str = typer.Option("auto", "--format", "-f", help="Output format"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Fetch and display full energy data."""
    asyncio.run(_data_async(watch, fields, format, host, timeout))


async def _data_async(watch, fields, format, host, timeout):
    console = Console()
    output_format = get_format(format, console.is_terminal)

    async with P1Client(host, timeout) as client:
        while True:
            data = await client.get_json("/api/v1/data", DataResponse)
            write_data(data, output_format, console)

            if watch is None:
                break

            await asyncio.sleep(watch)

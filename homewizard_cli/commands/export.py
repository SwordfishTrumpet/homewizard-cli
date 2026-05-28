"""homewizard-cli export command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse
from ..format import Format, get_format, write_data

app = typer.Typer()


@app.callback(invoke_without_command=True)
def export(
    format: str = typer.Option("influx", "--format", "-f", help="Output format"),
    watch: Optional[float] = typer.Option(None, "--watch", "-w", help="Poll interval"),
    file: Optional[str] = typer.Option(None, "--file", help="Output file path"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Export data in machine-readable formats."""
    asyncio.run(_export_async(format, watch, file, host, timeout))


async def _export_async(format, watch, file, host, timeout):
    console = Console()
    output_format = get_format(format, console.is_terminal)

    file_handle = None
    if file:
        file_handle = open(file, "a")

    try:
        async with P1Client(host, timeout) as client:
            while True:
                data = await client.get_json("/api/v1/data", DataResponse)
                if file_handle:
                    from io import StringIO

                    buf = StringIO()
                    file_console = Console(file=buf, force_terminal=False)
                    write_data(data, output_format, file_console)
                    file_handle.write(buf.getvalue() + "\n")
                    file_handle.flush()
                if not file:
                    write_data(data, output_format, console)

                if watch is None:
                    break
                await asyncio.sleep(watch)
    finally:
        if file_handle:
            file_handle.close()

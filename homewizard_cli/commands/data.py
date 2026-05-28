"""homewizard-cli data command."""

import asyncio
import json
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import DataResponse
from ..format import Format, write_data, get_format
from ..expr import evaluate_until


def _filter_fields(data: DataResponse, fields_str: str) -> dict:
    """Return only the requested fields from data."""
    if not fields_str:
        return None
    wanted = set(f.strip() for f in fields_str.split(","))
    return {k: v for k, v in data.model_dump().items() if k in wanted}


app = typer.Typer()


@app.callback(invoke_without_command=True)
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
    until: Optional[str] = typer.Option(
        None, "--until", help="Exit when expression is true"
    ),
):
    """Fetch and display full energy data."""
    asyncio.run(_data_async(watch, fields, format, host, timeout, until))


async def _data_async(watch, fields, format, host, timeout, until=None):
    console = Console()
    if watch is not None and watch < 1.0:
        console.print(
            f"Warning: Polling interval {watch}s is below recommended minimum (1.0s).\n"
            "         Device may become unresponsive.",
            style="yellow",
        )
    output_format = get_format(format, console.is_terminal)

    async with P1Client(host, timeout) as client:
        while True:
            data = await client.get_json("/api/v1/data", DataResponse)
            if until and evaluate_until(data.model_dump(), until):
                console.print(f"Condition met: {until}", style="green")
                raise typer.Exit(code=10)
            filtered = _filter_fields(data, fields)
            if filtered:
                console.print(json.dumps(filtered, indent=2, default=str))
                if watch is not None:
                    await asyncio.sleep(watch)
                    continue
                return

            write_data(data, output_format, console)

            if watch is None:
                break

            await asyncio.sleep(watch)

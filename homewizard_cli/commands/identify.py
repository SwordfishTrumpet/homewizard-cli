"""homewizard-cli identify command."""

import asyncio

import typer
from rich.console import Console

from ..client import P1Client

app = typer.Typer()


@app.callback(invoke_without_command=True)
def identify(
    count: int = typer.Option(1, "--count", "-c", help="Number of blinks"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Blink the LED on the P1 meter."""
    asyncio.run(_identify_async(count, host, timeout))


async def _identify_async(count, host, timeout):
    console = Console()

    async with P1Client(host, timeout) as client:
        for i in range(count):
            await client.put_json("/api/v1/identify", {})

        console.print(f"LED blink triggered on P1 Meter ({count}x)")

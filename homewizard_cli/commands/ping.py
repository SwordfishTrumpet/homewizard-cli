"""homewizard-cli ping command."""

import asyncio
import time

import typer
from rich.console import Console

from ..client import P1Client

app = typer.Typer()


@app.command()
def ping(
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only exit code, no output"
    ),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str = typer.Option(None, "--proxy", help="HTTP proxy URL"),
):
    """Check if the P1 meter is reachable."""
    asyncio.run(_ping_async(quiet, host, timeout, proxy))


async def _ping_async(quiet, host, timeout, proxy):
    console = Console()
    start = time.monotonic()
    try:
        async with P1Client(host, timeout, proxy=proxy) as client:
            await client.get("/api/")
        elapsed = (time.monotonic() - start) * 1000
        if not quiet:
            console.print(f"P1 Meter at {host} — OK ({elapsed:.0f}ms)")
    except Exception:
        if not quiet:
            console.print(f"P1 Meter at {host} — FAIL", style="red")
        raise typer.Exit(code=2)

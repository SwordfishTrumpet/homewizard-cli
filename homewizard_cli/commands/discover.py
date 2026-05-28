"""homewizard-cli discover command."""

import asyncio

import typer
from rich.console import Console

from ..discovery import discover_host, _get_cache

app = typer.Typer()


@app.callback(invoke_without_command=True)
def discover(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show discovery steps"),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP hint"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Discovery timeout"),
):
    """Discover P1 meter on the local network."""
    asyncio.run(_discover_async(verbose, host, timeout))


async def _discover_async(verbose, host, timeout):
    console = Console()
    effective_host = host if host != "192.168.68.109" else None

    if verbose:
        console.print(f"Discovering P1 meter (timeout={timeout}s) ...")

    found = await discover_host(
        explicit_host=effective_host,
        use_cache=True,
        timeout=timeout,
    )

    if verbose and _get_cache():
        console.print("  (cached from previous discovery)")

    console.print(f"Found device at {found}")

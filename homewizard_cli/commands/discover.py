"""homewizard-cli discover command."""

import asyncio

import typer
from rich.console import Console
from rich.table import Table

from ..discovery import _save_cache, discover_all_hosts, discover_host

app = typer.Typer()


@app.callback(invoke_without_command=True)
def discover(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show discovery steps"),
    save: bool = typer.Option(False, "--save", help="Save discovered host to config"),
    all_devices: bool = typer.Option(
        False, "--all", "-a", help="List all HomeWizard devices"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP hint"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="Discovery timeout"),
):
    """Discover P1 meter on the local network."""
    asyncio.run(
        _discover_async(verbose, save, all_devices, host, request_timeout=timeout)
    )


async def _discover_async(
    verbose: bool,
    save: bool,
    all_devices: bool,
    host: str | None,
    request_timeout: float,
):
    console = Console()

    if all_devices:
        if save:
            console.print("Warning: --save is ignored with --all", style="yellow")
        results = await discover_all_hosts(timeout=request_timeout)
        if not results:
            console.print("No HomeWizard devices found")
            return
        t = Table(show_header=True, header_style="bold magenta")
        t.add_column("IP", style="cyan")
        t.add_column("Product", style="green")
        t.add_column("Serial", style="yellow")
        t.add_column("Name", style="white")
        for r in results:
            t.add_row(r["host"], r["product_type"], r["serial"], r["product_name"])
        console.print(t)
        return

    effective_host = host

    if verbose:
        console.print(f"Discovering P1 meter (timeout={request_timeout}s) ...")

    found, from_cache = await discover_host(
        explicit_host=effective_host,
        use_cache=True,
        timeout=request_timeout,
    )

    if verbose and from_cache:
        console.print("  (cached from previous discovery)")

    console.print(f"Found device at {found}")

    if save:
        _save_cache(found)
        from ..discovery import CACHE_FILE

        console.print(f"Host saved to {CACHE_FILE}")

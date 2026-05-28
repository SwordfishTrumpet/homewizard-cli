"""homewizard-cli discover command."""

import asyncio

import typer
from rich.console import Console

from ..discovery import discover_host, discover_mdns, discover_arp, _get_cache

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

    if verbose:
        console.print("Trying explicit host ...")
        if host:
            from ..client import P1Client

            try:
                async with P1Client(host, timeout) as client:
                    info = await client.get("/api/")
                    import json

                    data = json.loads(info)
                    console.print(
                        f"  {host} — {data.get('product_type', 'Unknown')} — {data.get('serial', 'N/A')}"
                    )
                    return
            except Exception:
                console.print(f"  {host} — not reachable")

        console.print("Trying mDNS _hwenergy._tcp.local ...")
        mdns_host = await discover_mdns(timeout=2.0)
        if mdns_host:
            console.print(f"  found! {mdns_host}")
        else:
            console.print("  not found")

        console.print("Trying ARP scan ...")
        arp_host = await discover_arp(timeout=timeout)
        if arp_host:
            console.print(f"  found {arp_host}")
        else:
            console.print("  not found")
    else:
        found = await discover_host(
            explicit_host=host if host != "192.168.68.109" else None, timeout=timeout
        )
        console.print(f"Found device at {found}")

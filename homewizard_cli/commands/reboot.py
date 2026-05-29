"""homewizard-cli reboot command (API v2 only)."""

import asyncio
import json

import typer
from rich.console import Console

from ..client_v2 import P1ClientV2
from ..config import resolve_host
from ..errors import P1Error

app = typer.Typer()


@app.callback(invoke_without_command=True)
def reboot(
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
):
    """Reboot the device (API v2 only)."""
    asyncio.run(_reboot_async(host, timeout, token, no_verify))


async def _reboot_async(host: str | None, timeout, token, no_verify):
    console = Console()
    host = resolve_host(host)
    try:
        async with P1ClientV2(
            host, timeout, token=token, verify_cert=not no_verify
        ) as c:
            result = await c.put_json("/api/system/reboot", {})
            console.print(f"Reboot result: {json.dumps(result)}")
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code)

"""homewizard-cli batteries command (API v2 only)."""

import asyncio
import json

import typer
from rich.console import Console

from ..client_v2 import P1ClientV2
from ..models.v2 import BatteryState
from ..config import resolve_host
from ..errors import P1Error

app = typer.Typer()


@app.callback(invoke_without_command=True)
def batteries(
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
    mode: str | None = typer.Option(
        None, "--mode", help="Set battery mode: zero, to_full, standby, predictive"
    ),
):
    """Get/set Plug-In Battery state."""
    asyncio.run(_batteries_async(host, timeout, token, no_verify, mode))


async def _batteries_async(host: str | None, timeout, token, no_verify, mode):
    console = Console()
    host = resolve_host(host)
    try:
        async with P1ClientV2(
            host, timeout, token=token, verify_cert=not no_verify
        ) as c:
            if mode:
                result = await c.put_json("/api/batteries", {"mode": mode})
                console.print(f"Set mode to {mode}: {json.dumps(result)}")
            else:
                b = await c.get_json_v2("/api/batteries", BatteryState)
                console.print(b.model_dump_json(indent=2))
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code)

"""homewizard-cli batteries command (API v2 only)."""

import asyncio
import json

import typer
from rich.console import Console

from ..client_v2 import P1ClientV2
from ..config import resolve_host, resolve_no_verify, resolve_token
from ..errors import P1Error, UnsupportedError
from ..models.v2 import BatteryState

app = typer.Typer()


@app.callback(invoke_without_command=True)
def batteries(
    api_version: str = typer.Option(
        "v2", "--api-version", help="API version (v2 only)"
    ),
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
    asyncio.run(_batteries_async(api_version, host, timeout, token, no_verify, mode))


async def _batteries_async(api_version, host, timeout, token, no_verify, mode):
    if api_version != "v2":
        raise UnsupportedError("This command only supports API v2")
    console = Console()
    host = resolve_host(host)
    token = resolve_token(token)
    no_verify = resolve_no_verify(no_verify)
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
        raise typer.Exit(code=e.code) from e

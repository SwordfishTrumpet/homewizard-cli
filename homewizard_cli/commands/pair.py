"""homewizard-cli pair command (API v2 only)."""

import asyncio

import typer
from rich.console import Console

from ..client_v2 import P1ClientV2
from ..config import resolve_host
from ..errors import HttpError, P1Error, UnsupportedError

app = typer.Typer()


@app.callback(invoke_without_command=True)
def pair(
    api_version: str = typer.Option(
        "v2", "--api-version", help="API version (v2 only)"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    name: str = typer.Option(
        "local/cli", "--name", help="User name (must start with local/)"
    ),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
):
    """Create auth token (press device button within 30s)."""
    asyncio.run(_pair_async(api_version, host, timeout, name, no_verify))


async def _pair_async(api_version, host: str | None, timeout, name, no_verify):
    if api_version != "v2":
        raise UnsupportedError("This command only supports API v2")
    console = Console()
    host = resolve_host(host)
    try:
        async with P1ClientV2(host, timeout, verify_cert=not no_verify) as c:
            try:
                result = await c.pair(name)
                console.print(f"User:  {result.get('name')}")
                console.print(f"Token: {result.get('token')}")
            except HttpError as e:
                if e.status == 403:
                    console.print(
                        "Press the button on the device within 30 seconds, then retry.",
                        style="yellow",
                    )
                else:
                    raise
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code) from e

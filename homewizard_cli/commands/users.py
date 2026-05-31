"""homewizard-cli users command (API v2 only)."""

import asyncio
import json

import typer
from rich.console import Console
from rich.table import Table

from ..client_v2 import P1ClientV2
from ..config import resolve_host
from ..errors import P1Error, UnsupportedError

app = typer.Typer()


@app.callback()
def users():
    """Manage API v2 users."""


@app.command("list")
def users_list(
    api_version: str = typer.Option(
        "v2", "--api-version", help="API version (v2 only)"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
):
    """List API users."""
    asyncio.run(_users_list_async(api_version, host, timeout, token, no_verify))


async def _users_list_async(api_version, host: str | None, timeout, token, no_verify):
    if api_version != "v2":
        raise UnsupportedError("This command only supports API v2")
    console = Console()
    host = resolve_host(host)
    try:
        async with P1ClientV2(
            host, timeout, token=token, verify_cert=not no_verify
        ) as c:
            result = await c.get("/api/user")
            users = json.loads(result)
            if isinstance(users, list):
                t = Table(show_header=True, header_style="bold magenta")
                t.add_column("Name", style="cyan")
                for u in users:
                    t.add_row(u.get("name", ""))
                console.print(t)
            else:
                console.print(result)
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code) from e


@app.command("delete")
def users_delete(
    api_version: str = typer.Option(
        "v2", "--api-version", help="API version (v2 only)"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
    name: str = typer.Option(..., "--name", help="User name to delete"),
):
    """Delete an API user."""
    asyncio.run(_users_delete_async(api_version, host, timeout, token, no_verify, name))


async def _users_delete_async(
    api_version, host: str | None, timeout, token, no_verify, name
):
    if api_version != "v2":
        raise UnsupportedError("This command only supports API v2")
    console = Console()
    host = resolve_host(host)
    try:
        async with P1ClientV2(
            host, timeout, token=token, verify_cert=not no_verify
        ) as c:
            result = await c.delete(f"/api/user?name={name}")
            console.print(f"Deleted: {json.dumps(result)}")
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code) from e

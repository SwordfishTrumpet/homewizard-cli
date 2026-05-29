"""homewizard-cli ping command."""

import asyncio
import time

import typer
from rich.console import Console

from ..client_factory import resolve_client, API_VERSIONS
from ..config import resolve_host

app = typer.Typer()


@app.callback(invoke_without_command=True)
def ping(
    quiet: bool = typer.Option(
        False, "--quiet", "-q", help="Only exit code, no output"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Check if the P1 meter is reachable."""
    asyncio.run(
        _ping_async(
            quiet,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _ping_async(
    quiet: bool,
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    start = time.monotonic()
    try:
        client = resolve_client(
            api_version,
            host,
            request_timeout,
            token=token,
            verify_cert=not no_verify,
            proxy=proxy,
        )
        async with client as c:
            await c.get("/api/")
        elapsed = (time.monotonic() - start) * 1000
        if not quiet:
            console.print(f"P1 Meter at {host} \u2014 OK ({elapsed:.0f}ms)")
    except Exception:
        if not quiet:
            console.print(f"P1 Meter at {host} \u2014 FAIL", style="red")
        raise typer.Exit(code=2)
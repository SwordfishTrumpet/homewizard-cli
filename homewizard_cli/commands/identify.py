"""homewizard-cli identify command."""

import asyncio

import typer
from rich.console import Console

from ..client_factory import resolve_client, API_VERSIONS
from ..config import resolve_host

app = typer.Typer()


@app.callback(invoke_without_command=True)
def identify(
    count: int = typer.Option(1, "--count", "-c", help="Number of blinks"),
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
    """Blink the LED on the P1 meter."""
    asyncio.run(
        _identify_async(
            count,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _identify_async(
    count: int,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    client = resolve_client(
        api_version,
        host,
        request_timeout,
        token=token,
        verify_cert=not no_verify,
        proxy=proxy,
    )

    async with client as c:
        endpoint = "/api/system/identify" if api_version == "v2" else "/api/v1/identify"
        for _ in range(count):
            await c.put_json(endpoint, {})

        console.print(f"LED blink triggered on P1 Meter ({count}x)")
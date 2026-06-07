"""homewizard-cli system command."""

import asyncio

import typer

from ..util import _dumps_json
from rich.console import Console
from rich.table import Table

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import SystemResponse
from ..models.v2 import SystemV2

app = typer.Typer()


@app.callback(invoke_without_command=True)
def system(
    cloud: bool | None = typer.Option(None, "--cloud", help="Set cloud_enabled"),
    cloud_toggle: bool = typer.Option(
        False, "--cloud-toggle", help="Toggle cloud_enabled"
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
    led_brightness: int | None = typer.Option(
        None, "--led-brightness", help="Set LED brightness (0-100)"
    ),
):
    """Read or modify system settings."""
    asyncio.run(
        _system_async(
            cloud,
            cloud_toggle,
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            led_brightness=led_brightness,
        )
    )


async def _system_async(
    cloud: bool | None,
    cloud_toggle: bool,
    host: str | None,
    request_timeout: float,
    proxy: str | None = None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    led_brightness: int | None = None,
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
        if api_version == "v2":
            has_changes = (
                cloud is not None or cloud_toggle or led_brightness is not None
            )
            if has_changes:
                body: dict[str, object] = {}
                if cloud is not None:
                    body["cloud_enabled"] = cloud
                elif cloud_toggle:
                    current = await c.get_json_v2("/api/system", SystemV2)
                    body["cloud_enabled"] = not current.cloud_enabled
                if led_brightness is not None:
                    body["status_led_brightness_pct"] = led_brightness
                result = await c.put_json("/api/system", body)
                console.print(_dumps_json(result, indent=True))
            else:
                s = await c.get_json_v2("/api/system", SystemV2)
                t = Table(show_header=True, header_style="bold magenta")
                t.add_column("Field", style="cyan")
                t.add_column("Value", style="white")
                for field, value in s.model_dump().items():
                    if value is not None:
                        t.add_row(field, str(value))
                console.print(t)
        else:
            current = await c.get_json("/api/v1/system", SystemResponse)
            if cloud is None and not cloud_toggle:
                console.print(f"cloud_enabled: {current.cloud_enabled}")
                return
            if cloud_toggle:
                new_value = not current.cloud_enabled
            else:
                new_value = bool(cloud) if cloud is not None else current.cloud_enabled
            result = await c.put_json("/api/v1/system", {"cloud_enabled": new_value})
            console.print(
                f"cloud_enabled: {current.cloud_enabled} "
                f"\u2192 {result.get('cloud_enabled', new_value)}"
            )

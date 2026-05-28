"""homewizard-cli system command."""

import asyncio
from typing import Optional

import typer
from rich.console import Console

from ..client import P1Client
from ..models import SystemResponse

app = typer.Typer()


@app.callback(invoke_without_command=True)
def system(
    cloud: Optional[bool] = typer.Option(None, "--cloud", help="Set cloud_enabled"),
    cloud_toggle: bool = typer.Option(
        False, "--cloud-toggle", help="Toggle cloud_enabled"
    ),
    host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
):
    """Read or modify system settings."""
    asyncio.run(_system_async(cloud, cloud_toggle, host, timeout))


async def _system_async(cloud, cloud_toggle, host, timeout):
    console = Console()

    async with P1Client(host, timeout) as client:
        # Read current settings
        current = await client.get_json("/api/v1/system", SystemResponse)

        if cloud is None and not cloud_toggle:
            # Just read
            console.print(f"cloud_enabled: {current.cloud_enabled}")
            return

        # Determine new value
        if cloud_toggle:
            new_value = not current.cloud_enabled
        else:
            new_value = cloud

        # Write new settings
        result = await client.put_json("/api/v1/system", {"cloud_enabled": new_value})

        console.print(
            f"cloud_enabled: {current.cloud_enabled} \u2192 {result.get('cloud_enabled', new_value)}"
        )

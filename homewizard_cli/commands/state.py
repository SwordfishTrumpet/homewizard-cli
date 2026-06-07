"""homewizard-cli state command (API v2 only — Energy Socket)."""

import asyncio

import typer

from ..util import _dumps_json
from rich.console import Console

from ..client_v2 import P1ClientV2
from ..config import resolve_host, resolve_no_verify, resolve_token
from ..errors import P1Error, UnsupportedError
from ..models.v2 import StateResponse

app = typer.Typer()


@app.callback(invoke_without_command=True)
def state(
    api_version: str = typer.Option(
        "v2", "--api-version", help="API version (v2 only)"
    ),
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification"
    ),
    power_on: bool = typer.Option(False, "--power-on", help="Turn the socket on"),
    power_off: bool = typer.Option(False, "--power-off", help="Turn the socket off"),
    switch_lock: bool = typer.Option(False, "--switch-lock", help="Lock the switch"),
    switch_unlock: bool = typer.Option(
        False, "--switch-unlock", help="Unlock the switch"
    ),
    brightness: int | None = typer.Option(
        None, "--brightness", help="LED brightness (0-100)"
    ),
):
    """Get/set Energy Socket state (power, switch lock, brightness)."""
    asyncio.run(
        _state_async(
            api_version,
            host,
            timeout,
            token,
            no_verify,
            power_on,
            power_off,
            switch_lock,
            switch_unlock,
            brightness,
        )
    )


async def _state_async(
    api_version: str,
    host: str | None,
    timeout: float,
    token: str | None,
    no_verify: bool,
    power_on: bool,
    power_off: bool,
    switch_lock: bool,
    switch_unlock: bool,
    brightness: int | None,
):
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
            payload: dict = {}
            if power_on:
                payload["power_on"] = True
            if power_off:
                payload["power_on"] = False
            if switch_lock:
                payload["switch_lock"] = True
            if switch_unlock:
                payload["switch_lock"] = False
            if brightness is not None:
                payload["brightness"] = brightness

            if payload:
                result = await c.put_json("/api/state", payload)
                console.print(_dumps_json(result, indent=True))
            else:
                s = await c.get_json_v2("/api/state", StateResponse)
                console.print(s.model_dump_json(indent=2))
    except P1Error as e:
        console.print(str(e), style="red")
        raise typer.Exit(code=e.code) from e

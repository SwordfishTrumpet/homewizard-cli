"""homewizard-cli combined command."""

import asyncio
from typing import Any

from ..util import _dumps_json, _loads_json

import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..config import resolve_host
from ..models import Measurement, SystemResponse
from ..models.v2 import BatteryState, DeviceInfoV2, SystemV2
from ..storage import _setup_store

app = typer.Typer()


@app.callback(invoke_without_command=True)
def combined(
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
    db: str | None = typer.Option(
        None, "--db", help="SQLite database path for historical storage"
    ),
):
    """Fetch all device models in parallel."""
    asyncio.run(
        _combined_async(
            host,
            request_timeout=timeout,
            proxy=proxy,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
            db=db,
        )
    )


async def _combined_async(
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    db: str | None = None,
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
        store, serial = await _setup_store(db, api_version, c)
        coros = []
        if api_version == "v2":
            coros.append(c.get_json_v2("/api", DeviceInfoV2))
            coros.append(c.get_json_v2("/api/measurement", Measurement))
            coros.append(c.get_json_v2("/api/system", SystemV2))
            coros.append(c.get("/api/state"))
            coros.append(c.get_json_v2("/api/batteries", BatteryState))
        else:
            coros.append(c.get("/api/"))
            coros.append(c.get_json("/api/v1/data", Measurement))
            coros.append(c.get_json("/api/v1/system", SystemResponse))
            coros.append(asyncio.sleep(0))
            coros.append(asyncio.sleep(0))

        results = await asyncio.gather(*coros, return_exceptions=True)
        if store and serial and not isinstance(results[1], Exception):
            measurement = results[1]
            if hasattr(measurement, "model_dump"):
                store.append(measurement.model_dump(), serial)
        keys = ["device", "measurement", "system", "state", "batteries"]
        out: dict[str, Any] = {}
        for k, v in zip(keys, results, strict=False):
            if isinstance(v, Exception):
                out[k] = None
            elif isinstance(v, str):
                out[k] = _loads_json(v)
            elif hasattr(v, "model_dump"):
                out[k] = v.model_dump(mode="json")
            else:
                out[k] = v
        console.print(_dumps_json(out, indent=True))

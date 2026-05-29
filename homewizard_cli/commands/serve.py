import asyncio
import importlib
from typing import Any

import typer
from rich.console import Console

from ..client_factory import resolve_client, API_VERSIONS
from ..client_v2 import _create_ssl_context
from ..config import resolve_host

app = typer.Typer()

_HAS_FASTAPI = (
    importlib.util.find_spec("fastapi") is not None
    and importlib.util.find_spec("uvicorn") is not None
)


def _create_app(
    client_host: str,
    client_timeout: float,
    proxy: str | None,
    cache_seconds: int,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
) -> Any:
    from fastapi import FastAPI  # type: ignore[import-not-found]  # noqa: F811

    fastapi_app = FastAPI(title="homewizard-cli Proxy")
    _cache: dict[str, tuple[float, Any]] = {}

    import httpx

    protocol = "https" if api_version == "v2" else "http"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    ssl_ctx = _create_ssl_context(not no_verify) if api_version == "v2" else True

    async def _proxy(path: str):
        url = f"{protocol}://{client_host}/{path.lstrip('/')}"
        now = asyncio.get_event_loop().time()

        if cache_seconds > 0 and path in _cache:
            ts, data = _cache[path]
            if now - ts < cache_seconds:
                return data

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(client_timeout),
            headers=headers,
            verify=ssl_ctx,
        ) as c:
            resp = await c.get(url)
            data = resp.json()

        if cache_seconds > 0:
            _cache[path] = (now, data)

        return data

    @fastapi_app.get("/api/{path:path}")
    async def proxy_api(path: str):
        return await _proxy(f"api/{path}")

    @fastapi_app.get("/")
    async def root():
        return {"service": "homewizard-cli proxy", "target": client_host}

    return fastapi_app


@app.callback(invoke_without_command=True)
def serve(
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float = typer.Option(3.0, "--timeout", "-t", help="HTTP timeout"),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    bind: str = typer.Option("0.0.0.0", "--bind", "-b", help="Bind address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to listen on"),
    cache_seconds: int = typer.Option(
        0, "--cache", "-c", help="Cache responses for N seconds"
    ),
    api_version: str = typer.Option(
        "v2", "--api-version", help=f"API version ({'|'.join(API_VERSIONS)})"
    ),
    token: str | None = typer.Option(None, "--token", help="API v2 auth token"),
    no_verify: bool = typer.Option(
        False, "--no-verify", help="Disable SSL cert verification (v2 only)"
    ),
):
    """Start a FastAPI proxy server for the P1 meter."""
    asyncio.run(
        _serve_async(
            host,
            timeout,
            proxy,
            bind,
            port,
            cache_seconds,
            api_version=api_version,
            token=token,
            no_verify=no_verify,
        )
    )


async def _serve_async(
    host: str | None,
    request_timeout: float,
    proxy: str | None,
    bind: str,
    port: int,
    cache_seconds: int,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
):
    console = Console()
    host = resolve_host(host)
    if not _HAS_FASTAPI:
        console.print(
            "FastAPI and uvicorn are required for the serve command.\n"
            "Install with: pip install 'homewizard-cli[dev]'",
            style="red",
        )
        raise typer.Exit(code=1)

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
        console.print(f"P1 Meter at {host} \u2014 OK", style="green")
    except Exception as e:
        console.print(f"P1 Meter at {host} \u2014 FAIL: {e}", style="red")
        raise typer.Exit(code=2)

    import uvicorn  # type: ignore[import-not-found]

    app_instance = _create_app(
        host,
        request_timeout,
        proxy,
        cache_seconds,
        api_version=api_version,
        token=token,
        no_verify=no_verify,
    )
    console.print(f"Starting proxy at http://{bind}:{port}", style="green")
    console.print(f"Proxying to P1 Meter at {host}", style="cyan")

    config = uvicorn.Config(app_instance, host=bind, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

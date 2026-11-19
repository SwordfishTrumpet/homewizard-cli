import asyncio
import importlib
import secrets
from typing import Any

import httpx
import typer
from rich.console import Console

from ..client_factory import API_VERSIONS, resolve_client
from ..client_v2 import _create_ssl_context
from ..config import (
    resolve_host,
    resolve_no_verify,
    resolve_timeout,
    resolve_token,
)
from ..obis import lookup_obis

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
    auth_token: str | None = None,
) -> Any:
    """Build the proxy app.

    ``auth_token`` is the credential a *caller* must present. The proxy holds
    the meter's token, so without an inbound check it is a confused deputy that
    hands token-protected readings to anyone who can reach the port (issue #19).
    With no ``auth_token`` every route answers 401.
    """
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse

    protocol = "https" if api_version == "v2" else "http"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    ssl_ctx = _create_ssl_context(not no_verify) if api_version == "v2" else True

    # One shared client per app lifetime (MED-3/PERF-1): avoids a fresh
    # TCP+TLS handshake per proxied request and honors --proxy.
    shared_client = httpx.AsyncClient(
        timeout=httpx.Timeout(client_timeout),
        headers=headers,
        verify=ssl_ctx,
        proxy=proxy,
    )

    @asynccontextmanager
    async def _lifespan(app: Any):
        yield
        await shared_client.aclose()

    fastapi_app = FastAPI(title="homewizard-cli Proxy", lifespan=_lifespan)

    def _unauthorized(detail: str) -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content={"detail": detail},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @fastapi_app.middleware("http")
    async def _require_token(request: Request, call_next: Any) -> Any:
        """Refuse a caller that cannot prove it may read the meter.

        A middleware, not a per-route dependency: it runs before routing, so a
        route added later (or the auto-generated /docs and /openapi.json) cannot
        end up unprotected by omission.
        """
        if auth_token is None:
            return _unauthorized(
                "This proxy has no inbound token, so it refuses every caller: "
                "start it with --auth-token"
            )
        supplied = (request.headers.get("authorization") or "").strip()
        if supplied.lower().startswith("bearer "):
            supplied = supplied[7:].strip()
        if not supplied or not secrets.compare_digest(
            supplied.encode("utf-8"), auth_token.encode("utf-8")
        ):
            return _unauthorized("Send Authorization: Bearer <proxy token>")
        return await call_next(request)

    fastapi_app.state.shared_client = shared_client
    _cache: dict[str, tuple[float, Any]] = {}

    async def _proxy(path: str):
        url = f"{protocol}://{client_host}/{path.lstrip('/')}"
        now = asyncio.get_event_loop().time()

        if cache_seconds > 0 and path in _cache:
            ts, data = _cache[path]
            if now - ts < cache_seconds:
                return data

        resp = await shared_client.get(url)
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

    @fastapi_app.get("/obis/{code}")
    async def obis_endpoint(code: str):
        name = lookup_obis(code)
        if name is None:
            return {"code": code, "name": None, "error": "Unknown OBIS code"}
        return {"code": code, "name": name}

    return fastapi_app


@app.callback(invoke_without_command=True)
def serve(
    host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP"),
    timeout: float | None = typer.Option(
        None, "--timeout", "-t", help="HTTP timeout (default: config, else 3.0 s)"
    ),
    proxy: str | None = typer.Option(None, "--proxy", help="HTTP proxy URL"),
    bind: str = typer.Option(
        "127.0.0.1",
        "--bind",
        "-b",
        help="Bind address (loopback by default; 0.0.0.0 exposes it to the LAN)",
    ),
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
    auth_token: str | None = typer.Option(
        None,
        "--auth-token",
        help="Token callers of the proxy must send (generated when omitted)",
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
            auth_token=auth_token,
        )
    )


async def _serve_async(
    host: str | None,
    request_timeout: float | None,
    proxy: str | None,
    bind: str,
    port: int,
    cache_seconds: int,
    api_version: str = "v2",
    token: str | None = None,
    no_verify: bool = False,
    auth_token: str | None = None,
):
    console = Console()
    host = resolve_host(host)
    request_timeout = resolve_timeout(request_timeout)
    # The proxy and the WebSocket both need the configured credentials, not the
    # raw CLI defaults, or a token stored once in config.toml is dropped (#33).
    token = resolve_token(token)
    no_verify = resolve_no_verify(no_verify)
    if not _HAS_FASTAPI:
        console.print(
            "FastAPI and uvicorn are required for the serve command.\n"
            "Install with: pip install 'homewizard-cli[dev]'",
            style="red",
        )
        raise typer.Exit(code=1)

    # The proxy forwards the meter's token, so it must authenticate its own
    # callers; generate a credential rather than start an open relay (#19).
    if auth_token is None:
        auth_token = secrets.token_urlsafe(24)
        console.print(f"Proxy auth token (generated): {auth_token}", style="yellow")
        console.print(
            "  Pass --auth-token to reuse one instead of generating a new token.",
            style="cyan",
        )
    console.print(
        "  Callers must send: Authorization: Bearer <proxy token>", style="cyan"
    )

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
        raise typer.Exit(code=2) from e

    import uvicorn

    app_instance = _create_app(
        host,
        request_timeout,
        proxy,
        cache_seconds,
        api_version=api_version,
        token=token,
        no_verify=no_verify,
        auth_token=auth_token,
    )
    console.print(f"Starting proxy at http://{bind}:{port}", style="green")
    console.print(f"Proxying to P1 Meter at {host}", style="cyan")

    config = uvicorn.Config(app_instance, host=bind, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

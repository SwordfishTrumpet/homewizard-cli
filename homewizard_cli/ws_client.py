"""WebSocket client for HomeWizard API v2 real-time push updates."""

import asyncio
import json
import ssl
from pathlib import Path
from typing import Any

from .errors import P1Error

CA_CERT_PATH = Path.home() / ".config" / "homewizard-cli" / "homewizard-ca.pem"


def _create_ssl_context(verify_cert: bool = True) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify_cert:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    if CA_CERT_PATH.exists():
        ctx.load_verify_locations(CA_CERT_PATH)
    return ctx


class WebSocketClient:
    """Async WebSocket client for HomeWizard API v2 real-time push updates.

    Connects to ``wss://<host>/api/ws`` and yields parsed measurement data.
    Designed to be used as an async context manager::

        async with WebSocketClient(host, token="...") as ws:
            data = await ws.receive_data()
    """

    def __init__(
        self,
        host: str,
        token: str | None = None,
        verify_cert: bool = True,
        timeout: float = 30.0,
    ):
        self.host = host
        self.token = token
        self.verify_cert = verify_cert
        self.timeout = timeout
        self._ws: Any = None

    async def connect(self) -> None:
        import websockets

        ssl_ctx = _create_ssl_context(self.verify_cert)
        uri = f"wss://{self.host}/api/ws"
        extra_headers = {"X-Api-Version": "2"}
        if self.token:
            extra_headers["Authorization"] = f"Bearer {self.token}"
        self._ws = await websockets.connect(
            uri,
            ssl=ssl_ctx,
            extra_headers=extra_headers,
            ping_interval=30,
            ping_timeout=10,
        )

    async def receive_data(self) -> dict | None:
        """Receive a single JSON message from the WebSocket.

        Returns a parsed dict on success, or ``None`` if no data arrived
        within the configured timeout.
        """
        if self._ws is None:
            return None
        try:
            message = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
            if isinstance(message, bytes):
                message = message.decode("utf-8")
            return json.loads(message)
        except TimeoutError:
            return None

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()

    async def __aenter__(self):
        try:
            await self.connect()
        except ImportError:
            raise P1Error(
                "WebSocket support requires 'websockets' package.\n"
                "  Install: pip install homewizard-cli[ws]",
                code=1,
            ) from None
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

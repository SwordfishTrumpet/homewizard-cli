"""Async HTTPS client for HomeWizard API v2."""

import asyncio
import contextlib
import logging
import ssl
from pathlib import Path
from typing import TypeVar

import httpx
from pydantic import BaseModel

from .cacert import HOMEWIZARD_CA_CERT
from .client import _get_proxy_url
from .errors import HttpError, TimeoutError

log = logging.getLogger(__name__)

_MAX_BACKOFF = 8.0

CA_CERT_PATH = Path.home() / ".config" / "homewizard-cli" / "homewizard-ca.pem"

T = TypeVar("T", bound=BaseModel)


def _create_ssl_context(
    verify_cert: bool = True, identifier: str | None = None
) -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    if not verify_cert:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    # Load bundled cert first
    if HOMEWIZARD_CA_CERT and "BEGIN CERTIFICATE" in HOMEWIZARD_CA_CERT:
        ctx.load_verify_locations(cadata=HOMEWIZARD_CA_CERT)
        ctx.verify_flags |= ssl.VERIFY_X509_PARTIAL_CHAIN
    # Allow user override
    if CA_CERT_PATH.exists():
        ctx.load_verify_locations(CA_CERT_PATH)
    if identifier and verify_cert:
        ctx.hostname_checks_common_name = True
    return ctx


class P1ClientV2:
    """Async HTTPS client for HomeWizard API v2."""

    def __init__(
        self,
        host: str,
        timeout: float = 3.0,
        token: str | None = None,
        proxy: str | None = None,
        verify_cert: bool = True,
        identifier: str | None = None,
    ):
        self.host = host
        self.timeout = timeout
        self.token = token
        self.identifier = identifier
        if not verify_cert:
            log.warning("SSL verification disabled — connections are insecure.")
        proxy_url = _get_proxy_url(proxy, host)
        ssl_ctx = _create_ssl_context(verify_cert, identifier=identifier)
        headers = {"X-Api-Version": "2"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._client = httpx.AsyncClient(
            base_url=f"https://{host}",
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(keepalive_expiry=30.0),
            verify=ssl_ctx,
            headers=headers,
            proxy=proxy_url,
        )
        self._retries = 3
        self._backoff_base = 1.0

    async def get(self, path: str) -> str:
        """GET request returning raw text."""
        last_error: Exception = TimeoutError(self.timeout)
        for attempt in range(self._retries):
            try:
                resp = await self._client.get(path)
                resp.raise_for_status()
                return resp.text
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
            except httpx.HTTPStatusError as e:
                code = e.response.status_code
                if code == 401:
                    raise HttpError(code, "Unauthorized — need valid token") from e
                if code == 403:
                    raise HttpError(code, "Forbidden — button press required") from e
                if code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
                raise HttpError(code, str(e.request.url)) from e
        raise last_error

    async def get_json_v2(self, path: str, model: type[T]) -> T:
        text = await self.get(path)
        return model.model_validate_json(text)

    async def get_json(self, path: str, model: type[T]) -> T:
        """Alias for get_json_v2 — same interface as P1Client.get_json."""
        return await self.get_json_v2(path, model)

    async def put_json(self, path: str, data: dict) -> dict:
        last_error: Exception = TimeoutError(self.timeout)
        for attempt in range(self._retries):
            try:
                resp = await self._client.put(path, json=data)
                resp.raise_for_status()
                if resp.status_code == 204:
                    return {}
                return resp.json()
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
                raise HttpError(e.response.status_code, str(e.request.url)) from e
        raise last_error

    async def post_json(self, path: str, data: dict) -> dict:
        last_error: Exception = TimeoutError(self.timeout)
        for attempt in range(self._retries):
            try:
                resp = await self._client.post(path, json=data)
                resp.raise_for_status()
                if resp.status_code == 204:
                    return {}
                return resp.json()
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
                raise HttpError(e.response.status_code, str(e.request.url)) from e
        raise last_error

    async def delete(self, path: str) -> dict:
        last_error: Exception = TimeoutError(self.timeout)
        for attempt in range(self._retries):
            try:
                resp = await self._client.delete(path)
                resp.raise_for_status()
                if resp.status_code == 204:
                    return {}
                return resp.json()
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
                raise HttpError(e.response.status_code, str(e.request.url)) from e
        raise last_error

    async def pair(self, name: str = "local/cli") -> dict:
        return await self.post_json("/api/user", {"name": name})

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        with contextlib.suppress(Exception):
            await self.close()

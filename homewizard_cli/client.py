"""Async HTTP client for P1 Meter API."""

import asyncio
import contextlib
import os
from typing import TypeVar

import httpx
from pydantic import BaseModel

from .errors import HttpError, TimeoutError

_MAX_BACKOFF = 8.0

T = TypeVar("T", bound=BaseModel)


def _proxy_excluded(host: str) -> bool:
    no_proxy = os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or ""
    return any(
        host == excluded.strip() for excluded in no_proxy.split(",") if excluded.strip()
    )


def _get_proxy_url(
    explicit_proxy: str | None = None, host: str | None = None
) -> str | None:
    if explicit_proxy:
        return explicit_proxy
    if host and _proxy_excluded(host):
        return None
    return (
        os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
    )


class P1Client:
    """Async HTTP client for HomeWizard P1 Meter."""

    def __init__(self, host: str, timeout: float = 3.0, proxy: str | None = None):
        self.host = host
        self.timeout = timeout
        proxy_url = _get_proxy_url(proxy, host)
        if proxy_url:
            self._client = httpx.AsyncClient(
                base_url=f"http://{host}",
                timeout=httpx.Timeout(timeout),
                limits=httpx.Limits(keepalive_expiry=30.0),
                proxy=proxy_url,
            )
        else:
            self._client = httpx.AsyncClient(
                base_url=f"http://{host}",
                timeout=httpx.Timeout(timeout),
                limits=httpx.Limits(keepalive_expiry=30.0),
            )
        self._retries = 3
        self._backoff_base = 1.0

    async def get(self, path: str) -> str:
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
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(
                        min(self._backoff_base * (2**attempt), _MAX_BACKOFF)
                    )
                    continue
                raise HttpError(e.response.status_code, str(e.request.url)) from e
        raise last_error

    async def get_json(self, path: str, model: type[T]) -> T:
        """GET request returning parsed Pydantic model."""
        text = await self.get(path)
        return model.model_validate_json(text)

    async def get_json_v2(self, path: str, model: type[T]) -> T:
        """Alias for get_json — same interface as P1ClientV2.get_json_v2."""
        return await self.get_json(path, model)

    async def put_json(self, path: str, data: dict) -> dict:
        """PUT request with JSON body."""
        last_error: Exception = TimeoutError(self.timeout)
        for attempt in range(self._retries):
            try:
                resp = await self._client.put(path, json=data)
                resp.raise_for_status()
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

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        with contextlib.suppress(Exception):
            await self.close()

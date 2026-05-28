"""Async HTTP client for P1 Meter API."""

import asyncio
import os
import httpx
from typing import Optional, Type, TypeVar
from pydantic import BaseModel

from .errors import HttpError, TimeoutError

T = TypeVar("T", bound=BaseModel)


def _get_proxy_url(explicit_proxy: Optional[str] = None) -> Optional[str]:
    """Get proxy URL from explicit arg or env vars."""
    if explicit_proxy:
        return explicit_proxy
    return os.environ.get("HTTP_PROXY") or os.environ.get("HTTPS_PROXY")


class P1Client:
    """Async HTTP client for HomeWizard P1 Meter."""

    def __init__(self, host: str, timeout: float = 3.0, proxy: Optional[str] = None):
        self.host = host
        self.timeout = timeout
        proxy_url = _get_proxy_url(proxy)
        client_kwargs = {
            "base_url": f"http://{host}",
            "timeout": httpx.Timeout(timeout),
            "limits": httpx.Limits(keepalive_expiry=30.0),
        }
        if proxy_url:
            client_kwargs["proxies"] = {"http://": proxy_url, "https://": proxy_url}
        self._client = httpx.AsyncClient(**client_kwargs)
        self._retries = 3
        self._backoff_base = 1.0

    async def get(self, path: str) -> str:
        """GET request returning raw text."""
        last_error = None
        for attempt in range(self._retries):
            try:
                resp = await self._client.get(path)
                resp.raise_for_status()
                return resp.text
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(min(self._backoff_base * (2**attempt), 8.0))
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(min(self._backoff_base * (2**attempt), 8.0))
                    continue
                raise HttpError(e.response.status_code, str(e.request.url))
        raise last_error

    async def get_json(self, path: str, model: Type[T]) -> T:
        """GET request returning parsed Pydantic model."""
        text = await self.get(path)
        return model.model_validate_json(text)

    async def put_json(self, path: str, data: dict) -> dict:
        """PUT request with JSON body."""
        last_error = None
        for attempt in range(self._retries):
            try:
                resp = await self._client.put(path, json=data)
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                last_error = TimeoutError(self.timeout)
                if attempt < self._retries - 1:
                    await asyncio.sleep(min(self._backoff_base * (2**attempt), 8.0))
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 and attempt < self._retries - 1:
                    await asyncio.sleep(min(self._backoff_base * (2**attempt), 8.0))
                    continue
                raise HttpError(e.response.status_code, str(e.request.url))
        raise last_error

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

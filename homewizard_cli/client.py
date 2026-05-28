"""Async HTTP client for P1 Meter API."""

import httpx
from typing import Type, TypeVar
from pydantic import BaseModel

from .errors import HttpError, TimeoutError

T = TypeVar("T", bound=BaseModel)


class P1Client:
    """Async HTTP client for HomeWizard P1 Meter."""

    def __init__(self, host: str, timeout: float = 3.0):
        self.host = host
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=f"http://{host}",
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(keepalive_expiry=30.0),
        )

    async def get(self, path: str) -> str:
        """GET request returning raw text."""
        try:
            resp = await self._client.get(path)
            resp.raise_for_status()
            return resp.text
        except httpx.TimeoutException:
            raise TimeoutError(self.timeout)
        except httpx.HTTPStatusError as e:
            raise HttpError(e.response.status_code, str(e.request.url))

    async def get_json(self, path: str, model: Type[T]) -> T:
        """GET request returning parsed Pydantic model."""
        text = await self.get(path)
        return model.model_validate_json(text)

    async def put_json(self, path: str, data: dict) -> dict:
        """PUT request with JSON body."""
        try:
            resp = await self._client.put(path, json=data)
            resp.raise_for_status()
            return resp.json()
        except httpx.TimeoutException:
            raise TimeoutError(self.timeout)
        except httpx.HTTPStatusError as e:
            raise HttpError(e.response.status_code, str(e.request.url))

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

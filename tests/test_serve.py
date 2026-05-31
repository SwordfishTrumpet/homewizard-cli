# tests/test_serve.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import typer
from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_serve_help():
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "serve" in result.output.lower()


# ---------------------------------------------------------------------------
# _create_app tests — use respx to mock proxy HTTP calls
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_create_app_root():
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "service": "homewizard-cli proxy",
        "target": "192.168.1.100",
    }


@pytest.mark.anyio
async def test_create_app_proxy_v2():
    import respx

    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v2",
        token="secret_token",
        no_verify=True,
    )

    with respx.mock:
        route = respx.get("https://192.168.1.100/api/measurement")
        route.return_value = httpx.Response(200, json={"active_power_w": 500})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/measurement")
        assert response.status_code == 200
        assert response.json() == {"active_power_w": 500}

        # Verify the mocked call used HTTPS
        assert route.called


@pytest.mark.anyio
async def test_create_app_proxy_v1():
    import respx

    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"active_power_w": 500})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/data")
        assert response.status_code == 200
        assert response.json() == {"active_power_w": 500}

        assert route.called


@pytest.mark.anyio
async def test_create_app_cache_hit():
    import respx

    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=60,
        api_version="v1",
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"cached": True})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
        ) as client:
            # First request hits backend
            response = await client.get("/api/v1/data")
            assert response.status_code == 200
            assert response.json() == {"cached": True}
            assert route.call_count == 1

            # Second request hits cache (no additional backend call)
            response = await client.get("/api/v1/data")
            assert response.status_code == 200
            assert response.json() == {"cached": True}
            assert route.call_count == 1  # no new backend call


@pytest.mark.anyio
async def test_create_app_cache_miss_expired():
    import respx

    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=1,
        api_version="v1",
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"fresh": True})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
        ) as client:
            # First request
            response = await client.get("/api/v1/data")
            assert response.status_code == 200
            assert response.json() == {"fresh": True}

        import time

        time.sleep(1.1)

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/v1/data")
            assert response.status_code == 200
        assert route.call_count == 2


@pytest.mark.anyio
async def test_create_app_obis_known():
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/obis/1-0:1.8.0")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["code"] == "1-0:1.8.0"
    assert json_data["name"] == "Total imported energy — kWh"
    assert "error" not in json_data


@pytest.mark.anyio
async def test_create_app_obis_unknown():
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/obis/unknown")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["code"] == "unknown"
    assert json_data["name"] is None
    assert json_data["error"] == "Unknown OBIS code"


# ---------------------------------------------------------------------------
# _serve_async integration tests
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_serve_async_missing_fastapi():
    from homewizard_cli.commands.serve import _serve_async

    with patch("homewizard_cli.commands.serve._HAS_FASTAPI", False):
        with pytest.raises(typer.Exit) as exc_info:
            await _serve_async(
                host="192.168.1.100",
                request_timeout=3.0,
                proxy=None,
                bind="0.0.0.0",
                port=8000,
                cache_seconds=0,
            )
        assert exc_info.value.exit_code == 1


@pytest.mark.anyio
async def test_serve_async_connect_fail():
    from homewizard_cli.commands.serve import _serve_async

    with (
        patch("homewizard_cli.commands.serve._HAS_FASTAPI", True),
        patch(
            "homewizard_cli.commands.serve.resolve_client",
            return_value=AsyncMock(),
        ) as mock_resolve,
    ):
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))

        with pytest.raises(typer.Exit) as exc_info:
            await _serve_async(
                host="192.168.1.100",
                request_timeout=3.0,
                proxy=None,
                bind="0.0.0.0",
                port=8000,
                cache_seconds=0,
            )
        assert exc_info.value.exit_code == 2


@pytest.mark.anyio
async def test_serve_async_success_starts_uvicorn():
    from homewizard_cli.commands.serve import _serve_async

    with (
        patch("homewizard_cli.commands.serve._HAS_FASTAPI", True),
        patch(
            "homewizard_cli.commands.serve.resolve_client",
            return_value=AsyncMock(),
        ) as mock_resolve,
    ):
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(return_value={"ok": True})

        with patch(
            "homewizard_cli.commands.serve._create_app",
            return_value=MagicMock(),
        ) as mock_create_app:
            mock_server = MagicMock()
            mock_server.serve = AsyncMock()
            mock_config = MagicMock()

            with (
                patch("uvicorn.Config", return_value=mock_config) as mock_config_cls,
                patch("uvicorn.Server", return_value=mock_server) as mock_server_cls,
            ):
                await _serve_async(
                    host="192.168.1.100",
                    request_timeout=3.0,
                    proxy=None,
                    bind="0.0.0.0",
                    port=8000,
                    cache_seconds=0,
                )

                mock_create_app.assert_called_once()
                mock_config_cls.assert_called_once()
                mock_server_cls.assert_called_once_with(mock_config)
                mock_server.serve.assert_awaited_once()

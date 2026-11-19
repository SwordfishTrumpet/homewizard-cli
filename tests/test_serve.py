# tests/test_serve.py
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import typer
from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()

# The proxy refuses callers without an inbound token (issue #19).
PROXY_TOKEN = "proxy-test-token"
AUTH_HEADERS = {"Authorization": f"Bearer {PROXY_TOKEN}"}


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
        auth_token=PROXY_TOKEN,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )

    with respx.mock:
        route = respx.get("https://192.168.1.100/api/measurement")
        route.return_value = httpx.Response(200, json={"active_power_w": 500})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
            headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"active_power_w": 500})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
            headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"cached": True})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
            headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )

    with respx.mock:
        route = respx.get("http://192.168.1.100/api/v1/data")
        route.return_value = httpx.Response(200, json={"fresh": True})

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=fastapi_app),
            base_url="http://test",
            headers=AUTH_HEADERS,
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
            headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers=AUTH_HEADERS,
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
        auth_token=PROXY_TOKEN,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers=AUTH_HEADERS,
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


@pytest.mark.anyio
async def test_create_app_shared_client_with_proxy():
    """MED-3/PERF-1: one shared httpx client wired with --proxy, reused."""
    from homewizard_cli.commands.serve import _create_app

    fake_client = AsyncMock()
    fake_client.get = AsyncMock(return_value=httpx.Response(200, json={"ok": True}))

    with patch(
        "homewizard_cli.commands.serve.httpx.AsyncClient",
        return_value=fake_client,
    ) as mock_cls:
        fastapi_app = _create_app(
            client_host="192.168.1.100",
            client_timeout=3.0,
            proxy="http://proxy.local:3128",
            cache_seconds=0,
            api_version="v1",
            auth_token=PROXY_TOKEN,
        )
        # Exactly one shared client, constructed with the --proxy value
        assert mock_cls.call_count == 1
        assert mock_cls.call_args.kwargs.get("proxy") == "http://proxy.local:3128"
        assert fastapi_app.state.shared_client is fake_client

    # Requests run outside the patch so the test's own httpx is untouched;
    # the app's captured shared client still routes through the fake.
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers=AUTH_HEADERS,
    ) as client:
        r1 = await client.get("/api/v1/data")
        r2 = await client.get("/api/v1/data")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both requests flowed through the SAME client instance
    assert fake_client.get.await_count == 2


# ---------------------------------------------------------------------------
# Inbound authentication (issue #19): the proxy holds the meter's token, so it
# must not hand readings to a caller that presents nothing.
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_proxy_refuses_every_route_without_inbound_token():
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
        auth_token=PROXY_TOKEN,
    )

    paths = ["/", "/api/v1/data", "/api/measurement", "/obis/1-0:1.8.0", "/openapi.json"]
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        for path in paths:
            response = await client.get(path)
            assert response.status_code == 401, path
            assert response.headers.get("www-authenticate") == "Bearer"


@pytest.mark.anyio
async def test_proxy_refuses_a_wrong_token():
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v1",
        auth_token=PROXY_TOKEN,
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers={"Authorization": "Bearer not-the-token"},
    ) as client:
        response = await client.get("/api/v1/data")
    assert response.status_code == 401


@pytest.mark.anyio
async def test_app_without_an_inbound_token_refuses_everyone():
    """No configured credential must never mean "no check"."""
    from homewizard_cli.commands.serve import _create_app

    fastapi_app = _create_app(
        client_host="192.168.1.100",
        client_timeout=3.0,
        proxy=None,
        cache_seconds=0,
        api_version="v2",
        token="SECRET_DEVICE_TOKEN",
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/measurement")
    assert response.status_code == 401
    assert "SECRET_DEVICE_TOKEN" not in response.text


@pytest.mark.anyio
async def test_serve_async_generates_a_proxy_token():
    from homewizard_cli.commands import serve as serve_mod

    fake_client = AsyncMock()
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    fake_client.get = AsyncMock(return_value={"ok": True})

    mock_server = MagicMock()
    mock_server.serve = AsyncMock()

    with (
        patch.object(serve_mod, "_HAS_FASTAPI", True),
        patch.object(serve_mod, "resolve_client", return_value=fake_client),
        patch.object(serve_mod, "_create_app", return_value=MagicMock()) as create,
        patch("uvicorn.Config", return_value=MagicMock()),
        patch("uvicorn.Server", return_value=mock_server),
    ):
        await serve_mod._serve_async(
            host="192.168.1.100",
            request_timeout=3.0,
            proxy=None,
            bind="127.0.0.1",
            port=8000,
            cache_seconds=0,
        )

    generated = create.call_args.kwargs.get("auth_token")
    assert generated
    assert len(generated) >= 16


# ---------------------------------------------------------------------------
# #33: config.toml credentials reach the proxy
# ---------------------------------------------------------------------------


def test_serve_proxy_uses_the_configured_credentials(monkeypatch, tmp_path):
    """A token stored once in config.toml must not be dropped by the proxy."""
    import asyncio
    import sys
    import types

    from homewizard_cli import config as config_mod
    from homewizard_cli.client_v2 import P1ClientV2
    from homewizard_cli.commands import serve as serve_mod

    config_file = tmp_path / "config.toml"
    config_file.write_text(
        '[default]\nhost = "192.0.2.10"\ntoken = "CONFIG_TOKEN"\nno_verify = true\n'
    )
    monkeypatch.setattr(config_mod, "CONFIG_FILE", config_file)

    captured: dict = {}

    def fake_create_app(*args, **kwargs):
        captured.update(kwargs)
        return object()

    class FakeServer:
        def __init__(self, config):
            pass

        async def serve(self):
            return None

    fake_uvicorn = types.SimpleNamespace(
        Config=lambda *a, **k: object(), Server=FakeServer
    )

    with (
        patch.object(P1ClientV2, "get", AsyncMock(return_value="{}")),
        patch.object(serve_mod, "_create_app", side_effect=fake_create_app),
        patch.dict(sys.modules, {"uvicorn": fake_uvicorn}),
    ):
        asyncio.run(
            serve_mod._serve_async(
                None,
                3.0,
                None,
                "127.0.0.1",
                8000,
                0,
                api_version="v2",
                token=None,
                no_verify=False,
            )
        )

    assert captured["token"] == "CONFIG_TOKEN"
    assert captured["no_verify"] is True

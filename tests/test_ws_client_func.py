"""Functional tests for homewizard_cli.ws_client — WebSocketClient."""

import asyncio
import json
import ssl
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from homewizard_cli.errors import P1Error
from homewizard_cli.ws_client import WebSocketClient, _create_ssl_context

# Valid test cert for SSL context tests
_TEST_CERT = """\
-----BEGIN CERTIFICATE-----
MIIC9zCCAd+gAwIBAgIUDGUaI+TVbNPsvninL5v5DLUM3RwwDQYJKoZIhvcNAQEL
BQAwKzELMAkGA1UEBhMCTkwxDTALBgNVBAoMBFRlc3QxDTALBgNVBAMMBHRlc3Qw
HhcNMjYwNTI5MTE0NTI4WhcNMjYwNTMwMTE0NTI4WjArMQswCQYDVQQGEwJOTDEN
MAsGA1UECgwEVGVzdDENMAsGA1UEAwwEdGVzdDCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAMauO0WIU3Sxn/Nb2oOmCHXYJKiQM3wPQzO3k4p8xkaEJz2d
cK092v3SFkQJcN4UN4GK1UMaJRobrw/c3aXwn9bbPq1OI88Mo+aX53z4OZ33rI1G
aZ4TYs7UcQlhf1z0ewRNnggIdl68uDT//sGlwKLNKZROtvzxram9akaLfhhH8fJz
iYtSu6L17MgTgUHRdEMAOSFBiWfq7XgQwQ6WzxxT+tbck3ftH8td+Yiw3IFXEMHD
dTlT6r6+o+t1ULOx0vILUpxFPP7zsQSZjvGbm+O3n5rulCqRVG5A9M2bfce7TLAH
xSxenD2PPeqDIX+PWNPhZrgZKtMS3gvF/7ZJgnECAwEAAaMTMBEwDwYDVR0RBAgw
BoIEdGVzdDANBgkqhkiG9w0BAQsFAAOCAQEAO1d5wClKf7nZGenLFxrCs7O0dWvY
Hxdg99PAHs4R6Jj/nL5RrQOMtU4U2A8EJFO3stXAC67fGpbi1evp0psyK54EcgqD
LBvoS/QkiJh9FUZZ1vQJgivgt2LtTM36mKcdLqv40u+yh+jjJViHt6gGwg5Yh6sG
woU4c4Du3R1gLFvxkp4+Z1MV0OP4pVV1YqC3ChMWmLDX1eGXMVZBSUreWGjqVUcj
9DScrnsDsGXl3Va+mxEv4HAiov6zQzjpmpbB5l/Of/+zgHw9j3bHPnTXfVjKUR46
R7rR0z/REHVi5EvJYiVJ+KDlu4Y/3An2YprZafRMzLyYKLMp7LoJ8ctpqg==
-----END CERTIFICATE-----
"""


class TestCreateSSLContext:
    def test_no_verify(self):
        ctx = _create_ssl_context(verify_cert=False)
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    def test_verify_no_user_cert(self):
        with patch("pathlib.Path.exists", return_value=False):
            ctx = _create_ssl_context(verify_cert=True)
            assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_verify_with_user_cert(self, tmp_path: Path):
        cert_dir = tmp_path / ".config" / "homewizard-cli"
        cert_dir.mkdir(parents=True)
        cert_file = cert_dir / "homewizard-ca.pem"
        cert_file.write_text(_TEST_CERT)
        with patch("homewizard_cli.ws_client.CA_CERT_PATH", cert_file):
            ctx = _create_ssl_context(verify_cert=True)
            assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_verify_with_user_cert_not_found(self, tmp_path: Path):
        """Test that a missing user cert file does not break context creation."""
        cert_dir = tmp_path / ".config" / "homewizard-cli"
        cert_dir.mkdir(parents=True)
        missing_cert = cert_dir / "nonexistent.pem"
        assert not missing_cert.exists()
        with patch("homewizard_cli.ws_client.CA_CERT_PATH", missing_cert):
            ctx = _create_ssl_context(verify_cert=True)
            assert ctx.verify_mode == ssl.CERT_REQUIRED


class TestWebSocketClientInit:
    def test_defaults(self):
        ws = WebSocketClient("192.168.1.1")
        assert ws.host == "192.168.1.1"
        assert ws.token is None
        assert ws.verify_cert is True
        assert ws.timeout == 30.0
        assert ws._ws is None

    def test_custom_values(self):
        ws = WebSocketClient(
            "192.168.1.1", token="abc", verify_cert=False, timeout=10.0
        )
        assert ws.token == "abc"
        assert ws.verify_cert is False
        assert ws.timeout == 10.0


class TestConnect:
    @pytest.mark.asyncio
    async def test_connect_success(self):
        ws = WebSocketClient("192.168.1.1", token="my-token", verify_cert=False)
        mock_ws = AsyncMock()
        with patch("websockets.connect", new=AsyncMock(return_value=mock_ws)):
            await ws.connect()
            assert ws._ws is mock_ws

    @pytest.mark.asyncio
    async def test_connect_without_token(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        mock_ws = AsyncMock()
        with patch("websockets.connect", new=AsyncMock(return_value=mock_ws)):
            await ws.connect()
            assert ws._ws is mock_ws

    @pytest.mark.asyncio
    async def test_connect_no_websockets_package(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        real_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "websockets":
                raise ImportError("No module named 'websockets'")
            return real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=mock_import),
            pytest.raises(ImportError),
        ):
            await ws.connect()


class TestReceiveData:
    @pytest.mark.asyncio
    async def test_receive_no_ws(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        result = await ws.receive_data()
        assert result is None

    @pytest.mark.asyncio
    async def test_receive_string_message(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        ws._ws = AsyncMock()
        ws._ws.recv = AsyncMock(return_value=json.dumps({"power_w": 100}))
        result = await ws.receive_data()
        assert result == {"power_w": 100}

    @pytest.mark.asyncio
    async def test_receive_bytes_message(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        ws._ws = AsyncMock()
        ws._ws.recv = AsyncMock(return_value=b'{"power_w": 200}')
        result = await ws.receive_data()
        assert result == {"power_w": 200}

    @pytest.mark.asyncio
    async def test_receive_timeout(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False, timeout=0.01)
        ws._ws = AsyncMock()
        ws._ws.recv = AsyncMock(side_effect=asyncio.TimeoutError)
        result = await ws.receive_data()
        assert result is None

    @pytest.mark.asyncio
    async def test_receive_multiple_messages(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        ws._ws = AsyncMock()
        ws._ws.recv = AsyncMock()
        ws._ws.recv.side_effect = [
            json.dumps({"power_w": 100}),
            json.dumps({"power_w": 200}),
        ]
        r1 = await ws.receive_data()
        r2 = await ws.receive_data()
        assert r1 == {"power_w": 100}
        assert r2 == {"power_w": 200}


class TestClose:
    @pytest.mark.asyncio
    async def test_close_with_ws(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        ws._ws = AsyncMock()
        await ws.close()
        ws._ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_without_ws(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        await ws.close()


class TestContextManager:
    @pytest.mark.asyncio
    async def test_aenter_aexit_success(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        mock_ws = AsyncMock()
        with patch("websockets.connect", new=AsyncMock(return_value=mock_ws)):
            async with ws as w:
                assert w is ws
                assert ws._ws is mock_ws
            mock_ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aexit_without_ws(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        with patch("websockets.connect", new=AsyncMock(return_value=AsyncMock())):
            async with ws:
                pass

    @pytest.mark.asyncio
    async def test_aenter_import_error(self):
        ws = WebSocketClient("192.168.1.1", verify_cert=False)
        real_import = __import__

        def mock_import(name, *args, **kwargs):
            if name == "websockets":
                raise ImportError("No module named 'websockets'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(P1Error) as exc_info:
                await ws.__aenter__()
            assert "WebSocket support" in str(exc_info.value)
            assert exc_info.value.code == 1

"""Tests for homewizard_cli.client_v2."""

import ssl
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import respx
from httpx import Response

from homewizard_cli.client_v2 import P1ClientV2, _create_ssl_context
from homewizard_cli.errors import HttpError, TimeoutError
from homewizard_cli.models.v2 import MeasurementV2

# A valid self-signed certificate for testing SSL context loading
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


@pytest.fixture
def valid_cert():
    with patch("homewizard_cli.client_v2.HOMEWIZARD_CA_CERT", _TEST_CERT):
        yield


class TestCreateSSLContext:
    def test_no_verify_disables_check_hostname(self):
        ctx = _create_ssl_context(verify_cert=False)
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.check_hostname is False

    def test_verify_with_bundled_cert(self, valid_cert):
        ctx = _create_ssl_context(verify_cert=True)
        assert ctx.verify_mode == ssl.CERT_REQUIRED
        assert ctx.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN

    def test_verify_with_user_override(self, tmp_path: Path, valid_cert):
        cert_dir = tmp_path / ".config" / "homewizard-cli"
        cert_dir.mkdir(parents=True)
        cert_file = cert_dir / "homewizard-ca.pem"
        cert_file.write_text(_TEST_CERT)
        with patch("homewizard_cli.client_v2.CA_CERT_PATH", cert_file):
            ctx = _create_ssl_context(verify_cert=True)
            assert ctx.verify_mode == ssl.CERT_REQUIRED

    def test_verify_with_identifier_sets_hostname_checks(self, valid_cert):
        ctx = _create_ssl_context(verify_cert=True, identifier="my-device")
        assert ctx.hostname_checks_common_name is True

    def test_verify_without_identifier_no_hostname_checks(self, valid_cert):
        ctx = _create_ssl_context(verify_cert=True, identifier=None)
        # When identifier is None, the context should not be modified from default
        default_ctx = ssl.create_default_context()
        assert (
            ctx.hostname_checks_common_name == default_ctx.hostname_checks_common_name
        )


class TestP1ClientV2Init:
    def test_init_sets_identifier(self, valid_cert):
        client = P1ClientV2("192.168.1.1", identifier="my-device")
        assert client.identifier == "my-device"

    def test_init_without_identifier(self, valid_cert):
        client = P1ClientV2("192.168.1.1")
        assert client.identifier is None


class TestGetJsonV2:
    @pytest.mark.asyncio
    async def test_get_json_v2_success(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(
                200,
                json={
                    "power_w": 100,
                    "energy_import_kwh": 50.0,
                },
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 100
            assert result.energy_import_kwh == 50.0

    @pytest.mark.asyncio
    async def test_get_json_v2_401(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(401, text="Unauthorized")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/measurement", MeasurementV2)
            assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_get_json_v2_403(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(403, text="Forbidden")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/measurement", MeasurementV2)
            assert exc_info.value.status == 403

    @pytest.mark.asyncio
    async def test_get_json_v2_404(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/missing")
            route.return_value = Response(404, text="Not Found")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/missing", MeasurementV2)
            assert exc_info.value.status == 404

    @pytest.mark.asyncio
    async def test_get_json_v2_500(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(500, text="Internal Server Error")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/measurement", MeasurementV2)
            assert exc_info.value.status == 500

    @pytest.mark.asyncio
    async def test_get_json_v2_500_retry_then_success(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                Response(500, text="Internal Server Error"),
                Response(200, json={"power_w": 100}),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 100

    @pytest.mark.asyncio
    async def test_get_json_v2_timeout(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = httpx.TimeoutException("Request timed out")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._retries = 1
            with pytest.raises(TimeoutError):
                await client.get_json_v2("/api/measurement", MeasurementV2)

    @pytest.mark.asyncio
    async def test_get_json_alias(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(200, json={"power_w": 100})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get_json("/api/measurement", MeasurementV2)
            assert result.power_w == 100


class TestPutJson:
    @pytest.mark.asyncio
    async def test_put_json_success(self):
        with respx.mock:
            route = respx.put("https://192.168.1.1/api/system")
            route.return_value = Response(200, json={"cloud_enabled": True})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.put_json("/api/system", {"cloud_enabled": True})
            assert result == {"cloud_enabled": True}

    @pytest.mark.asyncio
    async def test_put_json_500(self):
        with respx.mock:
            route = respx.put("https://192.168.1.1/api/system")
            route.return_value = Response(500, text="Error")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._retries = 1
            with pytest.raises(HttpError) as exc_info:
                await client.put_json("/api/system", {"cloud_enabled": True})
            assert exc_info.value.status == 500


class TestPair:
    @pytest.mark.asyncio
    async def test_pair_success(self):
        with respx.mock:
            route = respx.post("https://192.168.1.1/api/user")
            route.return_value = Response(
                200, json={"name": "local/cli", "token": "abc123"}
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.pair()
            assert result == {"name": "local/cli", "token": "abc123"}
            assert route.calls.last.request.content == b'{"name":"local/cli"}'

    @pytest.mark.asyncio
    async def test_pair_custom_name(self):
        with respx.mock:
            route = respx.post("https://192.168.1.1/api/user")
            route.return_value = Response(
                200, json={"name": "my-device", "token": "abc123"}
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.pair("my-device")
            assert result == {"name": "my-device", "token": "abc123"}


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self):
        with respx.mock:
            route = respx.delete("https://192.168.1.1/api/user/123")
            route.return_value = Response(200, json={"ok": True})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.delete("/api/user/123")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_delete_500(self):
        with respx.mock:
            route = respx.delete("https://192.168.1.1/api/user/123")
            route.return_value = Response(500, text="Error")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._retries = 1
            with pytest.raises(HttpError) as exc_info:
                await client.delete("/api/user/123")
            assert exc_info.value.status == 500


class TestPostJson:
    @pytest.mark.asyncio
    async def test_post_json_success(self):
        with respx.mock:
            route = respx.post("https://192.168.1.1/api/user")
            route.return_value = Response(200, json={"ok": True})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.post_json("/api/user", {"name": "test"})
            assert result == {"ok": True}


class TestClose:
    @pytest.mark.asyncio
    async def test_close(self):
        client = P1ClientV2("192.168.1.1", verify_cert=False)
        mock_aclose = AsyncMock()
        object.__setattr__(client._client, "aclose", mock_aclose)
        await client.close()
        mock_aclose.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_aenter_aexit(self):
        client = P1ClientV2("192.168.1.1", verify_cert=False)
        mock_aclose = AsyncMock()
        object.__setattr__(client._client, "aclose", mock_aclose)
        async with client as c:
            assert c is client
        mock_aclose.assert_awaited_once()


class TestTokenHeader:
    @pytest.mark.asyncio
    async def test_token_in_header(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(200, json={"power_w": 100})
            client = P1ClientV2("192.168.1.1", token="my-token", verify_cert=False)
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 100
            assert (
                route.calls.last.request.headers["Authorization"] == "Bearer my-token"
            )


class TestProxy:
    def test_proxy_passed_to_httpx(self):
        with (
            patch(
                "homewizard_cli.client_v2._get_proxy_url",
                return_value="http://proxy:8080",
            ),
            patch("httpx.AsyncClient.__init__", return_value=None) as mock_init,
        ):
            P1ClientV2("192.168.1.1", proxy="http://proxy:8080", verify_cert=False)
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs.get("proxy") == "http://proxy:8080"

    def test_no_proxy(self):
        with (
            patch("homewizard_cli.client_v2._get_proxy_url", return_value=None),
            patch("httpx.AsyncClient.__init__", return_value=None) as mock_init,
        ):
            P1ClientV2("192.168.1.1", verify_cert=False)
            call_kwargs = mock_init.call_args.kwargs
            assert call_kwargs.get("proxy") is None


class TestHostnameVerification:
    def test_identifier_sets_hostname_checks(self):
        with patch("homewizard_cli.client_v2._create_ssl_context") as mock_ctx:
            mock_ctx.return_value = ssl.create_default_context()
            P1ClientV2("192.168.1.1", identifier="my-device")
            mock_ctx.assert_called_once_with(True, identifier="my-device")

    def test_no_identifier_no_hostname_checks(self):
        with patch("homewizard_cli.client_v2._create_ssl_context") as mock_ctx:
            mock_ctx.return_value = ssl.create_default_context()
            P1ClientV2("192.168.1.1")
            mock_ctx.assert_called_once_with(True, identifier=None)

    def test_no_verify_with_identifier(self):
        with patch("homewizard_cli.client_v2._create_ssl_context") as mock_ctx:
            mock_ctx.return_value = ssl.create_default_context()
            P1ClientV2("192.168.1.1", verify_cert=False, identifier="my-device")
            mock_ctx.assert_called_once_with(False, identifier="my-device")


class TestRetries:
    @pytest.mark.asyncio
    async def test_get_retries_on_500_then_fails(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                Response(500, text="Error 1"),
                Response(500, text="Error 2"),
                Response(500, text="Error 3"),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            with pytest.raises(HttpError) as exc_info:
                await client.get("/api/measurement")
            assert exc_info.value.status == 500
            assert len(route.calls) == 3

    @pytest.mark.asyncio
    async def test_get_retries_on_timeout_then_fails(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            with pytest.raises(TimeoutError):
                await client.get("/api/measurement")
            assert len(route.calls) == 3

    @pytest.mark.asyncio
    async def test_get_retries_on_timeout_then_success(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                Response(200, text="ok"),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            result = await client.get("/api/measurement")
            assert result == "ok"
            assert len(route.calls) == 3

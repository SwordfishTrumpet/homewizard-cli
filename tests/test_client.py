from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from homewizard_cli.client import P1Client
from homewizard_cli.errors import HttpError, TimeoutError
from homewizard_cli.models import DataResponse


@pytest.mark.asyncio
async def test_client_get_json():
    """Test GET request with JSON response."""
    mock_response = MagicMock()
    mock_response.text = (
        '{"wifi_ssid":"Test","wifi_strength":100,"smr_version":50,"meter_model":"TEST",'
        '"unique_id":"abc","active_tariff":1,"total_power_import_kwh":100.0,"total_power_import_t1_kwh":50.0,"total_power_import_t2_kwh":50.0,"total_power_export_kwh":0.0,"total_power_export_t1_kwh":0.0,"total_power_export_t2_kwh":0.0,"active_power_w":500.0}'
    )
    mock_response.status_code = 200

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        async with P1Client("192.168.1.1") as client:
            data = await client.get_json("/api/v1/data", DataResponse)
            assert data.wifi_ssid == "Test"
            assert data.active_power_w == 500.0


@pytest.mark.asyncio
async def test_client_http_error():
    """Test HTTP error handling."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        async with P1Client("192.168.1.1") as client:
            with pytest.raises(HttpError) as exc_info:
                await client.get("/api/v1/data")
            assert exc_info.value.code == 3


@pytest.mark.asyncio
async def test_client_timeout():
    """Test timeout handling."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        async with P1Client("192.168.1.1", timeout=1.0) as client:
            with pytest.raises(TimeoutError) as exc_info:
                await client.get("/api/v1/data")
            assert exc_info.value.code == 4


@pytest.mark.asyncio
async def test_client_proxy_from_env():
    """Test proxy URL is read from env var."""
    with patch.dict("os.environ", {"HTTP_PROXY": "http://proxy:8080"}):
        from homewizard_cli.client import _get_proxy_url

        assert _get_proxy_url() == "http://proxy:8080"


@pytest.mark.asyncio
async def test_client_explicit_proxy_overrides_env():
    """Test explicit --proxy overrides env var."""
    with patch.dict("os.environ", {"HTTP_PROXY": "http://proxy:8080"}):
        from homewizard_cli.client import _get_proxy_url

        assert _get_proxy_url("http://custom:3128") == "http://custom:3128"


@pytest.mark.asyncio
async def test_client_proxy_passed_to_httpx():
    """Test that proxy config reaches httpx.AsyncClient."""
    with patch("httpx.AsyncClient") as mock:
        client = P1Client("192.168.1.1", proxy="http://p:8080")
        with patch.object(client._client, "aclose", new=AsyncMock()):
            await client.close()
    assert mock.call_args[1]["proxy"] == "http://p:8080"


@pytest.mark.asyncio
async def test_client_proxy_not_set():
    """Test no proxy when neither env var nor explicit arg."""
    with patch.dict("os.environ", clear=True):
        from homewizard_cli.client import _get_proxy_url

        assert _get_proxy_url() is None


@pytest.mark.asyncio
async def test_client_retry_on_timeout():
    """Test retry with backoff on timeout."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise httpx.TimeoutException("Timeout")
        resp = MagicMock()
        resp.text = '{"key": "value"}'
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        return resp

    with patch("httpx.AsyncClient.get", side_effect=side_effect):
        client = P1Client("192.168.1.1", timeout=1.0)
        client._retries = 3
        result = await client.get("/api/v1/data")
        assert call_count == 3
        assert result == '{"key": "value"}'
        await client.close()


@pytest.mark.asyncio
async def test_client_retry_exhausted():
    """Test that retries eventually raise."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.TimeoutException("Timeout")):
        client = P1Client("192.168.1.1", timeout=0.1)
        client._retries = 2
        with pytest.raises(TimeoutError):
            await client.get("/api/v1/data")
        await client.close()


@pytest.mark.asyncio
async def test_client_retry_on_5xx():
    """Test retry on HTTP 5xx errors."""
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            resp = MagicMock()
            resp.status_code = 502
            resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                "502", request=MagicMock(), response=resp
            )
            raise httpx.HTTPStatusError("502", request=MagicMock(), response=resp)
        resp = MagicMock()
        resp.text = '{"key": "value"}'
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        return resp

    with patch("httpx.AsyncClient.get", side_effect=side_effect):
        client = P1Client("192.168.1.1")
        client._retries = 3
        result = await client.get("/api/v1/data")
        assert call_count == 3
        assert result == '{"key": "value"}'
        await client.close()


@pytest.mark.asyncio
async def test_client_no_retry_on_4xx():
    """Test that 4xx errors are not retried."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_response
    )

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        client = P1Client("192.168.1.1")
        client._retries = 3
        with pytest.raises(HttpError):
            await client.get("/api/v1/data")
        await client.close()


@pytest.mark.asyncio
async def test_client_proxy_scheme_prefers_https_for_https():
    """MED-2: the v2 (HTTPS) client must prefer HTTPS_PROXY over HTTP_PROXY."""
    with patch.dict(
        "os.environ",
        {
            "HTTP_PROXY": "http://proxy-http:8080",
            "HTTPS_PROXY": "http://proxy-https:8443",
        },
    ):
        from homewizard_cli.client import _get_proxy_url

        assert _get_proxy_url(scheme="https") == "http://proxy-https:8443"
        # v1 (http) keeps preferring HTTP_PROXY
        assert _get_proxy_url(scheme="http") == "http://proxy-http:8080"
        # explicit proxy still wins for both schemes
        assert (
            _get_proxy_url("http://custom:3128", scheme="https")
            == "http://custom:3128"
        )


# ── transport and parse failures name what failed (issues #41, #42, #45, #23) ──


@pytest.mark.asyncio
async def test_timeout_message_names_host_and_path():
    """#41: a timeout must say which request timed out."""
    with patch("httpx.AsyncClient.get", side_effect=httpx.ConnectTimeout("timeout")):
        async with P1Client("192.168.1.1", timeout=0.2) as client:
            client._retries = 1
            with pytest.raises(TimeoutError) as exc_info:
                await client.get("/api/v1/data")
    message = str(exc_info.value)
    assert "192.168.1.1" in message
    assert "GET http://192.168.1.1/api/v1/data" in message


@pytest.mark.asyncio
async def test_connect_error_becomes_device_not_found():
    """#42: a transport failure is a P1Error naming the host, with exit code 2."""
    from homewizard_cli.errors import DeviceNotFoundError

    with patch(
        "httpx.AsyncClient.get",
        side_effect=httpx.ConnectError("All connection attempts failed"),
    ):
        async with P1Client("192.168.1.1", timeout=0.2) as client:
            with pytest.raises(DeviceNotFoundError) as exc_info:
                await client.get("/api/v1/data")
    assert exc_info.value.code == 2
    assert "192.168.1.1" in str(exc_info.value)


@pytest.mark.asyncio
async def test_unparsable_json_raises_parse_error():
    """#45: malformed device JSON is a ParseError (exit 5) naming the request."""
    from homewizard_cli.errors import ParseError

    async with P1Client("192.168.1.1") as client:
        client.get = AsyncMock(return_value="not json at all")
        with pytest.raises(ParseError) as exc_info:
            await client.get_json("/api/v1/data", DataResponse)
    assert exc_info.value.code == 5
    assert "/api/v1/data" in str(exc_info.value)


@pytest.mark.asyncio
async def test_put_json_is_sent_once_after_timeout():
    """#23: a timed-out write is not retried, so the device acts once."""
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("response lost after commit", request=request)

    async with P1Client("192.168.1.1", timeout=0.2) as client:
        await client._client.aclose()
        client._client = httpx.AsyncClient(
            base_url="http://192.168.1.1", transport=httpx.MockTransport(handler)
        )
        client._backoff_base = 0.01
        with pytest.raises(TimeoutError):
            await client.put_json("/api/v1/identify", {})
    assert len(calls) == 1

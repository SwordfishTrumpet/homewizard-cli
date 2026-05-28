import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from homewizard_cli.client import P1Client
from homewizard_cli.models import DataResponse
from homewizard_cli.errors import HttpError, TimeoutError


@pytest.mark.asyncio
async def test_client_get_json():
    """Test GET request with JSON response."""
    mock_response = MagicMock()
    mock_response.text = '{"wifi_ssid":"Test","wifi_strength":100,"smr_version":50,"meter_model":"TEST","unique_id":"abc","active_tariff":1,"total_power_import_kwh":100.0,"total_power_import_t1_kwh":50.0,"total_power_import_t2_kwh":50.0,"total_power_export_kwh":0.0,"total_power_export_t1_kwh":0.0,"total_power_export_t2_kwh":0.0,"active_power_w":500.0}'
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

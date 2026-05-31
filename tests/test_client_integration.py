"""HTTP integration tests for homewizard-cli clients using respx."""

import json

import pytest
import respx
from httpx import Response

from homewizard_cli.client import P1Client
from homewizard_cli.client_v2 import P1ClientV2
from homewizard_cli.errors import HttpError, TimeoutError
from homewizard_cli.models import Measurement
from homewizard_cli.models.v2 import DeviceInfoV2, MeasurementV2, SystemV2


class TestP1ClientV2Integration:
    @pytest.mark.asyncio
    async def test_get_measurement(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(
                200,
                json={
                    "power_w": 456.7,
                    "energy_import_kwh": 12345.6,
                    "energy_export_kwh": 2345.6,
                },
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 456.7
            assert result.energy_import_kwh == 12345.6
            assert result.energy_export_kwh == 2345.6

    @pytest.mark.asyncio
    async def test_get_system(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/system")
            route.return_value = Response(
                200,
                json={
                    "cloud_enabled": True,
                    "wifi_ssid": "MyWiFi",
                    "wifi_rssi_db": -42.0,
                },
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get_json_v2("/api/system", SystemV2)
            assert result.cloud_enabled is True
            assert result.wifi_ssid == "MyWiFi"

    @pytest.mark.asyncio
    async def test_get_device_info(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api")
            route.return_value = Response(
                200,
                json={
                    "product_type": "HWE-P1",
                    "serial": "ABC123",
                    "product_name": "P1 Meter",
                },
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get_json_v2("/api", DeviceInfoV2)
            assert result.product_type == "HWE-P1"
            assert result.serial == "ABC123"

    @pytest.mark.asyncio
    async def test_get_telegram(self):
        with respx.mock:
            raw_telegram = "/XMX5LGBBFG123456789\n1-0:1.8.1(0012345.678*kWh)\n!522F"
            route = respx.get("https://192.168.1.1/api/telegram")
            route.return_value = Response(200, text=raw_telegram)
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.get("/api/telegram")
            assert "1-0:1.8.1" in result

    @pytest.mark.asyncio
    async def test_put_system_settings(self):
        with respx.mock:
            route = respx.put("https://192.168.1.1/api/system")
            route.return_value = Response(200, json={"cloud_enabled": False})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.put_json("/api/system", {"cloud_enabled": False})
            assert result == {"cloud_enabled": False}

    @pytest.mark.asyncio
    async def test_pair_user(self):
        with respx.mock:
            route = respx.post("https://192.168.1.1/api/user")
            route.return_value = Response(
                200, json={"name": "test/user", "token": "abc123def"}
            )
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.pair("test/user")
            assert result["name"] == "test/user"
            assert result["token"] == "abc123def"

    @pytest.mark.asyncio
    async def test_delete_user(self):
        with respx.mock:
            route = respx.delete("https://192.168.1.1/api/user/123")
            route.return_value = Response(200, json={"ok": True})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            result = await client.delete("/api/user/123")
            assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_retry_on_500_then_success(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                Response(500, text="Error"),
                Response(500, text="Error"),
                Response(200, json={"power_w": 100}),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 100
            assert len(route.calls) == 3

    @pytest.mark.asyncio
    async def test_timeout_retry(self):
        import httpx

        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.side_effect = [
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                Response(200, json={"power_w": 100}),
            ]
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._backoff_base = 0.01
            result = await client.get_json_v2("/api/measurement", MeasurementV2)
            assert result.power_w == 100
            assert len(route.calls) == 3

    @pytest.mark.asyncio
    async def test_unauthorized(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(401, text="Unauthorized")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._retries = 1
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/measurement", MeasurementV2)
            assert exc_info.value.status == 401

    @pytest.mark.asyncio
    async def test_forbidden(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(403, text="Forbidden")
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            client._retries = 1
            with pytest.raises(HttpError) as exc_info:
                await client.get_json_v2("/api/measurement", MeasurementV2)
            assert exc_info.value.status == 403

    @pytest.mark.asyncio
    async def test_content_type_header(self):
        with respx.mock:
            route = respx.put("https://192.168.1.1/api/system")
            route.return_value = Response(200, json={})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            await client.put_json("/api/system", {"key": "value"})
            assert (
                route.calls.last.request.headers["Content-Type"] == "application/json"
            )

    @pytest.mark.asyncio
    async def test_api_version_header(self):
        with respx.mock:
            route = respx.get("https://192.168.1.1/api/measurement")
            route.return_value = Response(200, json={"power_w": 100})
            client = P1ClientV2("192.168.1.1", verify_cert=False)
            await client.get("/api/measurement")
            assert route.calls.last.request.headers["X-Api-Version"] == "2"


class TestP1ClientIntegration:
    @pytest.mark.asyncio
    async def test_get_data_v1(self):
        with respx.mock:
            route = respx.get("http://192.168.1.1/api/v1/data")
            route.return_value = Response(
                200,
                json={
                    "active_power_w": 456.7,
                    "total_power_import_kwh": 12345.6,
                },
            )
            client = P1Client("192.168.1.1")
            result = await client.get_json("/api/v1/data", Measurement)
            assert result.active_power_w == 456.7
            assert result.total_power_import_kwh == 12345.6

    @pytest.mark.asyncio
    async def test_get_system_v1(self):
        with respx.mock:
            route = respx.get("http://192.168.1.1/api/v1/system")
            route.return_value = Response(200, json={"cloud_enabled": True})
            client = P1Client("192.168.1.1")
            text = await client.get("/api/v1/system")
            data = json.loads(text)
            assert data["cloud_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_device_info_v1(self):
        with respx.mock:
            route = respx.get("http://192.168.1.1/api/")
            route.return_value = Response(
                200,
                json={"product_type": "HWE-P1", "serial": "ABC123"},
            )
            client = P1Client("192.168.1.1")
            result = await client.get("/api/")
            data = json.loads(result)
            assert data["product_type"] == "HWE-P1"

    @pytest.mark.asyncio
    async def test_put_identify_v1(self):
        with respx.mock:
            route = respx.put("http://192.168.1.1/api/v1/identify")
            route.return_value = Response(200, json={"status": "ok"})
            client = P1Client("192.168.1.1")
            result = await client.put_json("/api/v1/identify", {})
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_get_telegram_v1(self):
        with respx.mock:
            raw = "/XMX5LGBBFG123456789\n1-0:1.8.1(0012345.678*kWh)\n!522F"
            route = respx.get("http://192.168.1.1/api/v1/telegram")
            route.return_value = Response(200, text=raw)
            client = P1Client("192.168.1.1")
            result = await client.get("/api/v1/telegram")
            assert "1-0:1.8.1" in result

    @pytest.mark.asyncio
    async def test_v1_timeout(self):
        import httpx

        with respx.mock:
            route = respx.get("http://192.168.1.1/api/v1/data")
            route.side_effect = httpx.TimeoutException("timeout")
            client = P1Client("192.168.1.1")
            with pytest.raises(TimeoutError):
                await client.get_json("/api/v1/data", Measurement)

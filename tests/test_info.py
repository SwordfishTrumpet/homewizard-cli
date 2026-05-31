from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_info_help():
    result = runner.invoke(app, ["info", "--help"])
    assert result.exit_code == 0
    assert "info" in result.output.lower()


def test_info_default():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models.v2 import DeviceInfoV2, SystemV2

    with patch(
        "homewizard_cli.commands.info.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            side_effect=[
                DeviceInfoV2(
                    product_name="P1 Meter",
                    product_type="HWE-P1",
                    serial="ABC123",
                    firmware_version="4.2.1",
                    api_version="v2",
                ),
                SystemV2(
                    cloud_enabled=True,
                    wifi_ssid="MyWifi",
                    wifi_rssi_db=-50.0,
                ),
            ]
        )

        result = runner.invoke(app, ["info", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "P1 Meter" in result.output
        assert "ABC123" in result.output
        assert "MyWifi" in result.output


def test_info_v1():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.info.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(
            side_effect=[
                (
                    '{"product_name":"P1 Meter","product_type":"HWE-P1",'
                    '"serial":"ABC123","firmware_version":"4.2.1","api_version":"v1"}'
                ),
                '{"cloud_enabled":true}',
            ]
        )
        client.get_json = AsyncMock(
            return_value=Measurement(
                wifi_ssid="MyWifi",
                wifi_strength=80,
                meter_model="ISKRA",
                smr_version=50,
            )
        )

        result = runner.invoke(
            app, ["info", "--api-version", "v1", "--host", "192.168.1.1"]
        )
        assert result.exit_code == 0
        assert "P1 Meter" in result.output
        assert "ABC123" in result.output
        assert "MyWifi" in result.output
        assert "ISKRA" in result.output
        assert "5.0" in result.output

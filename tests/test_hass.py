from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_hass_help():
    result = runner.invoke(app, ["hass", "--help"])
    assert result.exit_code == 0
    assert "hass" in result.output.lower()


def test_hass_mqtt_default():
    from homewizard_cli.models import Measurement
    from homewizard_cli.models.v2 import DeviceInfoV2, SystemV2

    with patch(
        "homewizard_cli.commands.hass.resolve_client",
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
                Measurement(
                    active_power_w=500.0,
                    total_power_import_kwh=100.0,
                    total_power_export_kwh=0.0,
                ),
                SystemV2(cloud_enabled=True),
            ]
        )

        result = runner.invoke(app, ["hass"])
        assert result.exit_code == 0
        assert "homeassistant/sensor/ABC123/active_power_w/config" in result.output
        assert "Power" in result.output


def test_hass_rest():
    from homewizard_cli.models import Measurement
    from homewizard_cli.models.v2 import DeviceInfoV2, SystemV2

    with patch(
        "homewizard_cli.commands.hass.resolve_client",
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
                Measurement(active_power_w=500.0),
                SystemV2(cloud_enabled=True),
            ]
        )

        result = runner.invoke(app, ["hass", "--rest", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert '"sensor":' in result.output
        assert "rest" in result.output
        assert "https://192.168.1.1/api/measurement" in result.output

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_combined_help():
    result = runner.invoke(app, ["combined", "--help"])
    assert result.exit_code == 0
    assert "combined" in result.output.lower()


def test_combined_v2():
    from homewizard_cli.models import Measurement
    from homewizard_cli.models.v2 import BatteryState, DeviceInfoV2, SystemV2

    with patch(
        "homewizard_cli.commands.combined.resolve_client",
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
                BatteryState(mode="to_full", battery_count=2),
            ]
        )
        client.get = AsyncMock(return_value='{"power_on": true}')

        result = runner.invoke(app, ["combined"])
        assert result.exit_code == 0
        assert "ABC123" in result.output
        assert "500.0" in result.output


def test_combined_v1():
    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.combined.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get = AsyncMock(
            return_value=(
                '{"product_name": "P1 Meter", "product_type": "HWE-P1", '
                '"serial": "ABC123", "firmware_version": "3.8.0", "api_version": "v1"}'
            )
        )
        client.get_json = AsyncMock(
            side_effect=[
                Measurement(active_power_w=500.0),
                {"cloud_enabled": True},
            ]
        )

        result = runner.invoke(app, ["combined", "--api-version", "v1"])
        assert result.exit_code == 0
        assert "ABC123" in result.output

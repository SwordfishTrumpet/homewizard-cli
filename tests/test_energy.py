from typer.testing import CliRunner

from homewizard_cli.main import app

runner = CliRunner()


def test_energy_help():
    result = runner.invoke(app, ["energy", "--help"])
    assert result.exit_code == 0
    assert "energy" in result.output.lower()


def test_energy_default():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.energy.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                total_power_import_kwh=100.0,
                total_power_export_kwh=50.0,
            )
        )

        result = runner.invoke(app, ["energy", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "100.00" in result.output
        assert "50.00" in result.output
        assert "consumed" in result.output


def test_energy_tariffs():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.energy.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                total_power_import_kwh=100.0,
                total_power_export_kwh=50.0,
                total_power_import_t1_kwh=60.0,
                total_power_import_t2_kwh=40.0,
                total_power_export_t1_kwh=20.0,
                total_power_export_t2_kwh=30.0,
                total_power_import_t3_kwh=10.0,
                total_power_export_t3_kwh=5.0,
                total_power_import_t4_kwh=1.0,
                total_power_export_t4_kwh=2.0,
            )
        )

        result = runner.invoke(app, ["energy", "--tariffs", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "T1" in result.output
        assert "T2" in result.output
        assert "T3" in result.output
        assert "T4" in result.output


def test_energy_exporting():
    from unittest.mock import AsyncMock, patch

    from homewizard_cli.models import Measurement

    with patch(
        "homewizard_cli.commands.energy.resolve_client",
        return_value=AsyncMock(),
    ) as mock_resolve:
        client = mock_resolve.return_value
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        client.get_json_v2 = AsyncMock(
            return_value=Measurement(
                total_power_import_kwh=50.0,
                total_power_export_kwh=100.0,
            )
        )

        result = runner.invoke(app, ["energy", "--host", "192.168.1.1"])
        assert result.exit_code == 0
        assert "produced" in result.output

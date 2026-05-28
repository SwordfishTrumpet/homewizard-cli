import pytest
from unittest.mock import AsyncMock, patch
from typer.testing import CliRunner
from homewizard_cli.main import app
from homewizard_cli.models import DataResponse

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "homewizard-cli version:" in result.output


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "HomeWizard P1 Meter CLI" in result.output


def test_data_help():
    result = runner.invoke(app, ["data", "--help"])
    assert result.exit_code == 0
    assert "Fetch and display" in result.output


def test_power_help():
    result = runner.invoke(app, ["power", "--help"])
    assert result.exit_code == 0
    assert "real-time power" in result.output


def test_default_command():
    """Test that running without subcommand shows data."""
    with patch("homewizard_cli.main.P1Client") as mock_client:
        mock_instance = AsyncMock()
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_instance.get_json = AsyncMock(
            return_value=DataResponse(
                wifi_ssid="Test",
                wifi_strength=100,
                smr_version=50,
                meter_model="TEST",
                unique_id="abc",
                active_tariff=1,
                total_power_import_kwh=100.0,
                total_power_import_t1_kwh=50.0,
                total_power_import_t2_kwh=50.0,
                total_power_export_kwh=0.0,
                total_power_export_t1_kwh=0.0,
                total_power_export_t2_kwh=0.0,
                active_power_w=500.0,
            )
        )
        mock_client.return_value = mock_instance

        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "TEST" in result.output


def test_energy_help():
    result = runner.invoke(app, ["energy", "--help"])
    assert result.exit_code == 0
    assert "energy" in result.output.lower()


def test_gas_help():
    result = runner.invoke(app, ["gas", "--help"])
    assert result.exit_code == 0
    assert "gas" in result.output.lower()


def test_data_fields_filter():
    """Test --fields option is accepted."""
    result = runner.invoke(app, ["data", "data", "--help"])
    assert result.exit_code == 0
    assert "--fields" in result.output


def test_quality_help():
    result = runner.invoke(app, ["quality", "--help"])
    assert result.exit_code == 0
    assert "quality" in result.output.lower()

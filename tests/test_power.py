"""Tests for the power CLI command — focused on undercovered paths."""

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app
from homewizard_cli.models import Measurement

runner = CliRunner()


def _make_client(measurement: Measurement):
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.get_json_v2 = AsyncMock(return_value=measurement)
    client.get_json = AsyncMock(return_value=measurement)
    return client


# ---------------------------------------------------------------------------
# --full mode
# ---------------------------------------------------------------------------


def test_power_full_default():
    measurement = Measurement(
        active_power_w=456.8,
        active_voltage_l1_v=238.5,
        active_current_l1_a=1.9,
    )
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--full", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "Net:" in result.output
    assert "456.8" in result.output
    assert "Import:" in result.output
    assert "Export:" in result.output
    assert "Voltage:" in result.output
    assert "238.5" in result.output
    assert "Current:" in result.output
    assert "1.9" in result.output


def test_power_full_exporting():
    measurement = Measurement(
        active_power_w=-106.0,
        active_voltage_l1_v=None,
        active_current_l1_a=None,
    )
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--full", "--api-version", "v2"])
    assert result.exit_code == 0
    assert "-106.0" in result.output
    assert "Voltage:" not in result.output
    assert "Current:" not in result.output


# ---------------------------------------------------------------------------
# --full with sparkline (no watch)
# ---------------------------------------------------------------------------


def test_power_full_sparkline_oneshot():
    measurement = Measurement(
        active_power_w=200.0,
        active_voltage_l1_v=230.0,
        active_current_l1_a=0.87,
    )
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["power", "--full", "--sparkline", "--api-version", "v2"]
        )
    assert result.exit_code == 0
    assert "Trend:" in result.output


def test_power_sparkline_oneshot():
    measurement = Measurement(active_power_w=200.0)
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--sparkline", "--api-version", "v2"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --color flag
# ---------------------------------------------------------------------------


def test_power_color_importing():
    measurement = Measurement(active_power_w=500.0)
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--color", "--api-version", "v2"])
    assert result.exit_code == 0


def test_power_color_exporting():
    measurement = Measurement(active_power_w=-100.0)
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--color", "--api-version", "v2"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# --format json / csv
# ---------------------------------------------------------------------------


def test_power_format_json():
    measurement = Measurement(active_power_w=456.8)
    client = _make_client(measurement)

    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(
            app, ["power", "--format", "json", "--api-version", "v2"]
        )
    assert result.exit_code == 0
    assert '"active_power_w"' in result.output


def test_power_format_csv():
    measurement = Measurement(active_power_w=456.8, total_power_import_kwh=100.0)
    client = _make_client(measurement)

    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--format", "csv", "--api-version", "v2"])
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# v1 path
# ---------------------------------------------------------------------------


def test_power_v1():
    measurement = Measurement(active_power_w=456.8)
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(app, ["power", "--api-version", "v1"])
    assert result.exit_code == 0
    assert "456.8" in result.output


# ---------------------------------------------------------------------------
# --until with alert dispatcher in watch mode
# ---------------------------------------------------------------------------


def test_power_until_with_alert_watch():
    measurement = Measurement(active_power_w=2000.0)
    client = _make_client(measurement)

    side_effects = [SystemExit(10)]

    async def mock_get(endpoint, model):
        raise side_effects.pop(0)

    client.get_json = AsyncMock(side_effect=mock_get)

    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            [
                "power",
                "--api-version",
                "v1",
                "--until",
                "active_power_w > 1000",
                "--alert-webhook",
                "https://example.com/hook",
            ],
        )
    assert result.exit_code == 10


# ---------------------------------------------------------------------------
# v1 full + sparkline
# ---------------------------------------------------------------------------


def test_power_v1_full_sparkline():
    measurement = Measurement(
        active_power_w=456.8,
        active_voltage_l1_v=238.5,
        active_current_l1_a=1.9,
    )
    client = _make_client(measurement)
    with patch("homewizard_cli.commands.power.resolve_client", return_value=client):
        result = runner.invoke(
            app,
            ["power", "--full", "--sparkline", "--api-version", "v1"],
        )
    assert result.exit_code == 0
    assert "Net:" in result.output
    assert "Trend:" in result.output

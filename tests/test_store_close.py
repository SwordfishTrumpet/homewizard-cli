"""HIGH-1 regression: every command that opens MeasurementStore must close it.

The 2026-06-07 audit fixed data/export/dashboard/history/cost but missed
power/energy/gas/water/combined — their SQLite connections leaked (WAL files
accumulated in watch modes).
"""

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app
from homewizard_cli.models import Measurement

runner = CliRunner()

_MEASUREMENT = Measurement(
    wifi_ssid="Test",
    wifi_strength=80,
    smr_version=50,
    meter_model="TEST",
    unique_id="abc123",
    active_tariff=1,
    total_power_import_kwh=1000.0,
    total_power_import_t1_kwh=500.0,
    total_power_import_t2_kwh=500.0,
    total_power_export_kwh=0.0,
    total_power_export_t1_kwh=0.0,
    total_power_export_t2_kwh=0.0,
    active_power_w=500.0,
    total_gas_m3=9000.0,
)


def _mock_client():
    client = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    client.get_json_v2 = AsyncMock(return_value=_MEASUREMENT)
    return client


def _mock_store():
    store = MagicMock()
    store.append = MagicMock()
    store.close = MagicMock()
    return store


def _assert_store_closed(cmd: list[str], module: str):
    with (
        patch(f"homewizard_cli.commands.{module}.resolve_client", return_value=_mock_client()),
        patch(
            f"homewizard_cli.commands.{module}._setup_store",
            new=AsyncMock(return_value=(_mock_store(), "SERIAL001")),
        ) as mock_setup,
    ):
        result = runner.invoke(app, cmd)
        assert result.exit_code == 0, result.output
        store = mock_setup.return_value[0]
        store.append.assert_called()
        store.close.assert_called_once()


def test_power_closes_store():
    _assert_store_closed(["power", "--db", "x.db", "--format", "json"], "power")


def test_energy_closes_store():
    _assert_store_closed(["energy", "--db", "x.db"], "energy")


def test_gas_closes_store():
    _assert_store_closed(["gas", "--db", "x.db"], "gas")


def test_water_closes_store():
    _assert_store_closed(["water", "--db", "x.db"], "water")


def test_combined_closes_store():
    from homewizard_cli.models.v2 import BatteryState, DeviceInfoV2, SystemV2

    client = _mock_client()
    client.get_json_v2 = AsyncMock(
        side_effect=[
            DeviceInfoV2(
                product_name="P1 Meter",
                product_type="HWE-P1",
                serial="SERIAL001",
                firmware_version="4.0.0",
                api_version="v2",
            ),
            _MEASUREMENT,
            SystemV2(cloud_enabled=True),
            BatteryState(mode="to_full", permissions=["battery"]),
        ]
    )
    client.get = AsyncMock(return_value='{"state": "ok"}')
    store = _mock_store()
    with (
        patch("homewizard_cli.commands.combined.resolve_client", return_value=client),
        patch(
            "homewizard_cli.commands.combined._setup_store",
            new=AsyncMock(return_value=(store, "SERIAL001")),
        ),
    ):
        result = runner.invoke(app, ["combined", "--db", "x.db"])
        assert result.exit_code == 0, result.output
        store.append.assert_called()
        store.close.assert_called_once()

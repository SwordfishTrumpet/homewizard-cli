"""Integration tests: data/power/combined/dashboard --db writes tagged rows."""

import contextlib
import os
import tempfile
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from homewizard_cli.main import app
from homewizard_cli.models import Measurement
from homewizard_cli.models.v2 import DeviceInfoV2
from homewizard_cli.storage import MeasurementStore

runner = CliRunner()


def _make_mock_v2_client(measurement_data=None):
    """Create a mock v2 client that returns device info + measurement."""
    if measurement_data is None:
        measurement_data = Measurement(
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
    mock_instance = AsyncMock()
    mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
    mock_instance.__aexit__ = AsyncMock(return_value=None)
    # _fetch_device_serial uses get_json_v2("/api", DeviceInfoV2) for v2
    device_info = DeviceInfoV2(
        product_name="P1 Meter",
        product_type="HWE-P1",
        serial="SERIAL001",
        firmware_version="4.0.0",
        api_version="v2",
    )
    mock_instance.get_json_v2 = AsyncMock(side_effect=[device_info, measurement_data])
    return mock_instance


def test_data_db_one_shot_writes_row():
    """data --db should write a single row even in one-shot mode."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.data.resolve_client") as mock_resolve:
            mock_instance = _make_mock_v2_client()
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["data", "--db", db_path, "--format", "json"],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            assert rows[0]["active_power_w"] == 500.0
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_power_db_writes_row():
    """power --db should write a row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.power.resolve_client") as mock_resolve:
            mock_instance = _make_mock_v2_client()
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["power", "--db", db_path, "--format", "json"],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            assert rows[0]["active_power_w"] == 500.0
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_combined_db_writes_row():
    """combined --db should write a row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.combined.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            device_info = DeviceInfoV2(
                product_name="P1 Meter",
                product_type="HWE-P1",
                serial="SERIAL001",
                firmware_version="4.0.0",
                api_version="v2",
            )
            measurement = Measurement(
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
            )
            # combined.py calls: get_json_v2("/api", DeviceInfoV2),
            # get_json_v2("/api/measurement", Measurement),
            # get_json_v2("/api/system", SystemV2), get("/api/state"),
            # get_json_v2("/api/batteries", BatteryState)
            from homewizard_cli.models.v2 import BatteryState, SystemV2

            mock_instance.get_json_v2 = AsyncMock(
                side_effect=[
                    device_info,  # _setup_store reads device info
                    device_info,  # combined reads device info (/api)
                    measurement,  # combined reads measurement
                    SystemV2(),  # combined reads system
                    BatteryState(),  # combined reads batteries
                ]
            )
            mock_instance.get = AsyncMock(return_value='{"power_on": true}')
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["combined", "--db", db_path],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_energy_db_writes_row():
    """energy --db should write a row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.energy.resolve_client") as mock_resolve:
            mock_instance = _make_mock_v2_client()
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["energy", "--db", db_path],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_gas_db_writes_row():
    """gas --db should write a row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.gas.resolve_client") as mock_resolve:
            mock_instance = _make_mock_v2_client()
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["gas", "--db", db_path],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_water_db_writes_row():
    """water --db should write a row."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        with patch("homewizard_cli.commands.water.resolve_client") as mock_resolve:
            measurement = Measurement(
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
                external=[],
            )
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            device_info = DeviceInfoV2(
                product_name="P1 Meter",
                product_type="HWE-P1",
                serial="SERIAL001",
                firmware_version="4.0.0",
                api_version="v2",
            )
            mock_instance.get_json_v2 = AsyncMock(
                side_effect=[device_info, measurement]
            )
            mock_resolve.return_value = mock_instance

            result = runner.invoke(
                app,
                ["water", "--db", db_path],
            )
            assert result.exit_code == 0

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) == 1
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)

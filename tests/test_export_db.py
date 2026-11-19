"""Integration tests: export --db writes tagged rows."""

import asyncio
import contextlib
import os
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from homewizard_cli.commands.export import _export_async
from homewizard_cli.errors import P1Error
from homewizard_cli.main import app
from homewizard_cli.models import Measurement
from homewizard_cli.models.v2 import DeviceInfoV2
from homewizard_cli.storage import MeasurementStore

runner = CliRunner()


def test_export_db_fetches_device_and_writes_rows():
    """export --db should fetch device info and write tagged rows (v2)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        mock_data = Measurement(
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
        device_info = DeviceInfoV2(
            product_name="P1 Meter",
            product_type="HWE-P1",
            serial="TEST001",
            firmware_version="4.0.0",
            api_version="v2",
        )
        with patch("homewizard_cli.commands.export.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            # For _setup_store (v2): get_json_v2("/api", DeviceInfoV2)
            # For export loop: get_json_v2("/api/measurement", Measurement)
            mock_instance.get_json_v2 = AsyncMock(side_effect=[device_info, mock_data])
            mock_resolve.return_value = mock_instance

            runner.invoke(
                app,
                [
                    "export",
                    "--db",
                    db_path,
                    "--format",
                    "json",
                    "--watch",
                    "0.1",
                    "--until",
                    "active_power_w > 0",
                ],
            )
            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) > 0
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_export_db_retain_days_runs():
    """export --db --retain-days should not crash (prune runs every 60 iters)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        mock_data = Measurement(
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
        device_info = DeviceInfoV2(
            product_name="P1 Meter",
            product_type="HWE-P1",
            serial="TEST001",
            firmware_version="4.0.0",
            api_version="v2",
        )
        with patch("homewizard_cli.commands.export.resolve_client") as mock_resolve:
            mock_instance = AsyncMock()
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_instance.get_json_v2 = AsyncMock(side_effect=[device_info, mock_data])
            mock_resolve.return_value = mock_instance

            runner.invoke(
                app,
                [
                    "export",
                    "--db",
                    db_path,
                    "--retain-days",
                    "365",
                    "--format",
                    "json",
                    "--watch",
                    "0.1",
                    "--until",
                    "active_power_w > 0",
                ],
            )

            store = MeasurementStore(db_path)
            rows = store.query()
            assert len(rows) > 0
            store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)


def test_export_retain_days_rejects_non_positive():
    """#16: --retain-days below 1 must be refused before anything is pruned."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    try:
        store = MeasurementStore(db_path)
        store.append({"unique_id": "seed", "active_power_w": 1.0}, "SEED")
        store.close()

        for bad in ("-1", "0"):
            with pytest.raises(P1Error) as excinfo:
                asyncio.run(
                    _export_async(
                        format="json",
                        watch=0.01,
                        file=None,
                        host="127.0.0.1",
                        request_timeout=1.0,
                        db=db_path,
                        retain_days=int(bad),
                    )
                )
            assert excinfo.value.code == 2
            assert "retain-days" in str(excinfo.value)

        store = MeasurementStore(db_path)
        assert store.info()["row_count"] == 1
        store.close()
    finally:
        with contextlib.suppress(OSError):
            os.unlink(db_path)

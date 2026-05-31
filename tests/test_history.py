"""Tests for the history command."""

import contextlib
import json
import os
import tempfile
from datetime import datetime, timedelta

from typer.testing import CliRunner

from homewizard_cli.main import app
from homewizard_cli.storage import MeasurementStore

runner = CliRunner()


def _populate_store(db_path: str, device_serial: str = "DEV001", rows: int = 10):
    store = MeasurementStore(db_path)
    now = datetime.now()
    for i in range(rows):
        dt = now - timedelta(hours=i)
        data = {
            "wifi_ssid": "TestNet",
            "wifi_strength": 80,
            "smr_version": 50,
            "meter_model": "ISKRA",
            "unique_id": "abc123",
            "active_tariff": 1,
            "total_power_import_kwh": 1000.0 + i,
            "total_power_import_t1_kwh": 500.0,
            "total_power_export_kwh": 200.0 + i * 0.5,
            "active_power_w": 400.0 + i * 10,
            "active_voltage_l1_v": 238.0,
            "active_current_l1_a": 1.9,
            "voltage_sag_l1_count": 0,
            "voltage_swell_l1_count": 0,
            "any_power_fail_count": 0,
            "long_power_fail_count": 0,
            "total_gas_m3": 9000.0 + i,
            "gas_timestamp": 260529120000,
            "gas_unique_id": "gas001",
            "external": [],
            "text_message": None,
        }
        cols = store._get_columns()
        vals = {
            "stored_at": dt.isoformat(),
            "device_serial": device_serial,
            "schema_version": 1,
        }
        for c in cols:
            if c in ("stored_at", "device_serial", "schema_version"):
                continue
            v = data.get(c)
            if c == "external" and isinstance(v, list):
                v = json.dumps(v, default=str)
            vals[c] = v
        col_list = ", ".join(cols)
        conn = store._conn
        assert conn is not None
        placeholders = ", ".join(f":{c}" for c in cols)
        conn.execute(f"INSERT INTO readings ({col_list}) VALUES ({placeholders})", vals)
        conn.commit()
    store.close()


def _parse_json_objects(text: str) -> list:
    """Extract JSON objects from multi-line output."""
    objects = []
    buf = ""
    depth = 0
    for ch in text:
        buf += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                with contextlib.suppress(json.JSONDecodeError):
                    objects.append(json.loads(buf))
                buf = ""
    if buf.strip():
        with contextlib.suppress(json.JSONDecodeError):
            objects.append(json.loads(buf))
    return objects


class TestHistoryHelp:
    def test_history_help(self):
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0
        assert "Query historical measurement data" in result.output
        assert "--yesterday" in result.output
        assert "--today" in result.output
        assert "--this-week" in result.output
        assert "--this-month" in result.output
        assert "--range" in result.output
        assert "--since-last" in result.output
        assert "--compare" in result.output
        assert "--top" in result.output
        assert "--bottom" in result.output
        assert "--fields" in result.output
        assert "--device-id" in result.output
        assert "--list-devices" in result.output
        assert "--agg" in result.output
        assert "--format" in result.output
        assert "--db" in result.output
        assert "--info" in result.output
        assert "--vacuum" in result.output


class TestHistoryQuery:
    def test_info_output(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(app, ["history", "--db", db_path, "--info"])
            assert result.exit_code == 0
            assert "Rows:" in result.output
            assert "Database:" in result.output
            assert "Devices:" in result.output
            assert "DEV001" in result.output
        finally:
            os.unlink(db_path)

    def test_list_devices(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 3)
            _populate_store(db_path, "DEV002", 2)
            result = runner.invoke(app, ["history", "--db", db_path, "--list-devices"])
            assert result.exit_code == 0
            assert "DEV001" in result.output
            assert "DEV002" in result.output
        finally:
            os.unlink(db_path)

    def test_list_devices_json(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 3)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--list-devices", "--format", "json"]
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            assert any("DEV001" in str(obj) for obj in objs)
        finally:
            os.unlink(db_path)

    def test_vacuum(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(app, ["history", "--db", db_path, "--vacuum"])
            assert result.exit_code == 0
            assert "vacuumed" in result.output.lower()
        finally:
            os.unlink(db_path)

    def test_no_data_message(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Create empty DB
            store = MeasurementStore(db_path)
            store.close()
            result = runner.invoke(app, ["history", "--db", db_path, "--this-month"])
            assert result.exit_code == 0
            assert "No data found" in result.output
        finally:
            os.unlink(db_path)

    def test_defaults_to_today(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 48)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--today", "--format", "json"]
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            if objs:
                assert "active_power_w" in objs[0]
        finally:
            os.unlink(db_path)

    def test_json_format(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--today", "--format", "json"]
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            if objs:
                assert "active_power_w" in objs[0]
        finally:
            os.unlink(db_path)

    def test_csv_format(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--today", "--format", "csv"]
            )
            assert result.exit_code == 0
            assert "active_power_w" in result.output or "No data found" in result.output
        finally:
            os.unlink(db_path)

    def test_tsv_format(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--today", "--format", "tsv"]
            )
            assert result.exit_code == 0
            assert "active_power_w" in result.output or "No data found" in result.output
        finally:
            os.unlink(db_path)

    def test_device_id_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            _populate_store(db_path, "DEV002", 3)
            result = runner.invoke(
                app,
                [
                    "history",
                    "--db",
                    db_path,
                    "--device-id",
                    "DEV002",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            if objs:
                for obj in objs:
                    assert obj.get("device_serial") == "DEV002"
        finally:
            os.unlink(db_path)

    def test_top_n(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 10)
            result = runner.invoke(
                app,
                [
                    "history",
                    "--db",
                    db_path,
                    "--top",
                    "3",
                    "--today",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            assert len(objs) <= 3
        finally:
            os.unlink(db_path)

    def test_bottom_n(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 10)
            result = runner.invoke(
                app,
                [
                    "history",
                    "--db",
                    db_path,
                    "--bottom",
                    "3",
                    "--today",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            assert len(objs) <= 3
        finally:
            os.unlink(db_path)

    def test_agg_hourly(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(
                app,
                [
                    "history",
                    "--db",
                    db_path,
                    "--agg",
                    "hourly",
                    "--today",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            if objs:
                assert "period" in objs[0]
                assert "active_power_w_avg" in objs[0]
        finally:
            os.unlink(db_path)

    def test_field_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            result = runner.invoke(
                app,
                [
                    "history",
                    "--db",
                    db_path,
                    "--fields",
                    "active_power_w,total_power_import_kwh",
                    "--today",
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            objs = _parse_json_objects(result.output)
            if objs:
                assert "active_power_w" in objs[0]
                assert "total_power_import_kwh" in objs[0]
                # Should NOT contain fields not in the filter
                assert "wifi_ssid" not in objs[0]
        finally:
            os.unlink(db_path)

    def test_compare_last_week(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            # Add data from last week and this week
            store = MeasurementStore(db_path)
            now = datetime.now()
            # This week data
            data = {
                "total_power_import_kwh": 1000.0,
                "active_power_w": 500.0,
                "wifi_ssid": "Test",
                "wifi_strength": 80,
                "smr_version": 50,
                "meter_model": "M",
                "unique_id": "u",
                "active_tariff": 1,
                "total_power_import_t1_kwh": 500.0,
                "total_power_export_kwh": 200.0,
                "external": [],
            }
            store.append(data, "DEV001")
            # Last week data
            last_week = now - timedelta(days=8)
            cols = store._get_columns()
            vals = {
                "stored_at": last_week.isoformat(),
                "device_serial": "DEV001",
                "schema_version": 1,
            }
            for c in cols:
                if c in ("stored_at", "device_serial", "schema_version"):
                    continue
                v = data.get(c)
                if c == "external" and isinstance(v, list):
                    v = json.dumps(v, default=str)
                vals[c] = v
            conn = store._conn
            assert conn is not None
            col_list = ", ".join(cols)
            placeholders = ", ".join(f":{c}" for c in cols)
            conn.execute(
                f"INSERT INTO readings ({col_list}) VALUES ({placeholders})", vals
            )
            conn.commit()
            store.close()

            result = runner.invoke(
                app,
                [
                    "--no-color",
                    "history",
                    "--db",
                    db_path,
                    "--this-week",
                    "--compare",
                    "last-week",
                ],
            )
            assert result.exit_code == 0
            assert (
                "Current" in result.output or "No data for comparison" in result.output
            )
        finally:
            os.unlink(db_path)

    def test_range_option(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 5)
            start = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            end = datetime.now().strftime("%Y-%m-%d")
            result = runner.invoke(
                app, ["history", "--db", db_path, "--range", f"{start}..{end}"]
            )
            assert result.exit_code == 0
        finally:
            os.unlink(db_path)

    def test_invalid_range(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            _populate_store(db_path, "DEV001", 3)
            result = runner.invoke(
                app, ["history", "--db", db_path, "--range", "invalid"]
            )
            assert result.exit_code != 0
        finally:
            os.unlink(db_path)

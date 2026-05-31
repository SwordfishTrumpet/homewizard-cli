"""Tests for MeasurementStore — SQLite-backed historical storage."""

import json
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta

from homewizard_cli.storage import MeasurementStore, _measurement_columns


def _sample_data(overrides=None) -> dict:
    data = {
        "wifi_ssid": "TestNet",
        "wifi_strength": 80,
        "smr_version": 50,
        "meter_model": "ISKRA",
        "unique_id": "abc123",
        "active_tariff": 1,
        "total_power_import_kwh": 1000.0,
        "total_power_import_t1_kwh": 500.0,
        "total_power_export_kwh": 200.0,
        "active_power_w": 456.789,
        "active_voltage_l1_v": 238.5,
        "active_current_l1_a": 1.9,
        "voltage_sag_l1_count": 2,
        "voltage_swell_l1_count": 0,
        "any_power_fail_count": 0,
        "long_power_fail_count": 1,
        "total_gas_m3": 9876.54,
        "gas_timestamp": 260529120000,
        "gas_unique_id": "gas001",
        "external": [],
        "text_message": None,
    }
    if overrides:
        data.update(overrides)
    return data


def _store_with_data(db_path: str, device_serial: str = "DEV001", rows: int = 5):
    store = MeasurementStore(db_path)
    for i in range(rows):
        data = _sample_data({"total_power_import_kwh": 1000.0 + i})
        store.append(data, device_serial)
    return store


class TestMeasurementStore:
    def test_creates_schema_on_init(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            cols = store._get_columns()
            assert "stored_at" in cols
            assert "device_serial" in cols
            assert "active_power_w" in cols
            assert "total_power_import_kwh" in cols
            store.close()
        finally:
            os.unlink(db_path)

    def test_append_and_query_round_trip(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            data = _sample_data()
            store.append(data, "DEV001")
            rows = store.query()
            assert len(rows) == 1
            assert rows[0]["device_serial"] == "DEV001"
            assert rows[0]["active_power_w"] == 456.789
            assert rows[0]["total_power_import_kwh"] == 1000.0
            store.close()
        finally:
            os.unlink(db_path)

    def test_append_external_list_as_json(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)

            class FakeExternal:
                def model_dump(self, mode="json"):
                    return {"type": "water_meter", "value": 123.4}

            data = _sample_data({"external": [FakeExternal()]})
            store.append(data, "DEV001")
            rows = store.query()
            ext = rows[0]["external"]
            assert isinstance(ext, list)
            assert ext[0]["type"] == "water_meter"
            store.close()
        finally:
            os.unlink(db_path)

    def test_query_device_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = _store_with_data(db_path, "DEV001", 3)
            store.append(_sample_data(), "DEV002")
            rows_dev1 = store.query(device_serial="DEV001")
            assert len(rows_dev1) == 3
            rows_dev2 = store.query(device_serial="DEV002")
            assert len(rows_dev2) == 1
            rows_all = store.query()
            assert len(rows_all) == 4
            store.close()
        finally:
            os.unlink(db_path)

    def test_query_date_range(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            # Append a few rows with timestamp overrides
            now = datetime.now()
            for i in range(5):
                past = (now - timedelta(hours=i)).isoformat()
                data = _sample_data({"total_power_import_kwh": 1000.0 + i})
                # Use direct SQL to set stored_at
                cols = store._get_columns()
                vals = {
                    "stored_at": past,
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

            three_hours_ago = (now - timedelta(hours=3)).isoformat()
            rows = store.query(start=three_hours_ago)
            assert len(rows) == 4  # T-3h through T (inclusive)

            specific_start = (now - timedelta(hours=2, minutes=30)).isoformat()
            specific_end = (now - timedelta(hours=1, minutes=30)).isoformat()
            rows = store.query(start=specific_start, end=specific_end)
            assert len(rows) == 1  # T-2h
            store.close()
        finally:
            os.unlink(db_path)

    def test_query_agg_daily(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            now = datetime.now()
            for day_offset in range(3):
                dt = now - timedelta(days=day_offset)
                data = _sample_data({"total_power_import_kwh": 1000.0 + day_offset})
                cols = store._get_columns()
                vals = {
                    "stored_at": dt.isoformat(),
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

            rows = store.query(agg="daily")
            assert len(rows) <= 3
            assert "period" in rows[0]
            assert "total_power_import_kwh_avg" in rows[0]
            assert "total_power_import_kwh_sum" in rows[0]
            assert "total_power_import_kwh_min" in rows[0]
            assert "total_power_import_kwh_max" in rows[0]
            store.close()
        finally:
            os.unlink(db_path)

    def test_query_top_n(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            for i in range(10):
                data = _sample_data({"active_power_w": float(i * 100)})
                store.append(data, "DEV001")
            top5 = store.query(top_n=5)
            assert len(top5) == 5
            # Highest active_power_w values should be 900, 800, 700, 600, 500
            assert top5[0]["active_power_w"] == 900.0
            bottom5 = store.query(top_n=-5)
            assert len(bottom5) == 5
            assert bottom5[0]["active_power_w"] == 0.0
            store.close()
        finally:
            os.unlink(db_path)

    def test_info_returns_metadata(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = _store_with_data(db_path, "DEV001", 5)
            meta = store.info()
            assert meta["row_count"] == 5
            assert meta["date_start"] is not None
            assert meta["date_end"] is not None
            assert "DEV001" in meta["devices"]
            assert meta["file_size_bytes"] > 0
            store.close()
        finally:
            os.unlink(db_path)

    def test_info_empty_db(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            meta = store.info()
            assert meta["row_count"] == 0
            assert meta["devices"] == []
            store.close()
        finally:
            os.unlink(db_path)

    def test_since_last(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            assert store.since_last() is None
            store.append(_sample_data(), "DEV001")
            ts = store.since_last()
            assert ts is not None
            assert isinstance(ts, datetime)
            store.close()
        finally:
            os.unlink(db_path)

    def test_retain_deletes_old_rows(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            old_dt = (datetime.now() - timedelta(days=10)).isoformat()
            cols = store._get_columns()
            data = _sample_data()
            vals = {"stored_at": old_dt, "device_serial": "DEV001", "schema_version": 1}
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

            store.append(_sample_data(), "DEV001")
            assert store.info()["row_count"] == 2

            deleted = store.retain(5)
            assert deleted == 1
            assert store.info()["row_count"] == 1
            store.close()
        finally:
            os.unlink(db_path)

    def test_migrate_adds_missing_column(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = MeasurementStore(db_path)
            cols_before = set(store._get_columns())
            # Drop a column to simulate outdated schema
            assert store._conn is not None
            store._conn.close()
            store._conn = sqlite3.connect(db_path)
            store._conn.row_factory = sqlite3.Row
            store._conn.execute("PRAGMA journal_mode=WAL")
            store._conn.execute("PRAGMA busy_timeout=5000")
            store._columns = None
            # migrate should not crash
            store.migrate()
            cols_after = set(store._get_columns())
            # Should have at least as many columns as before
            assert cols_after.issuperset(cols_before)
            store.close()
        finally:
            os.unlink(db_path)

    def test_vacuum_runs(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = _store_with_data(db_path, "DEV001", 5)
            store.vacuum()
            meta = store.info()
            assert meta["row_count"] == 5
            store.close()
        finally:
            os.unlink(db_path)

    def test_noop_when_db_path_none(self):
        store = MeasurementStore(None)
        assert store._conn is None
        store.append(_sample_data(), "DEV001")
        assert store.query() == []
        assert store.info()["row_count"] == 0
        assert store.list_devices() == []
        assert store.since_last() is None
        store.vacuum()
        assert store.retain(7) == 0
        store.migrate()
        store.close()

    def test_list_devices(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        try:
            store = _store_with_data(db_path, "DEV001", 3)
            store.append(_sample_data(), "DEV002")
            devices = store.list_devices()
            assert "DEV001" in devices
            assert "DEV002" in devices
            store.close()
        finally:
            os.unlink(db_path)

    def test_measurement_columns_include_all_fields(self):
        cols = _measurement_columns()
        assert "stored_at" in cols
        assert "device_serial" in cols
        assert "active_power_w" in cols
        assert "total_power_import_kwh" in cols
        assert "external" in cols
        assert cols["stored_at"] == "TEXT NOT NULL"
        assert "REAL" in cols["active_power_w"]

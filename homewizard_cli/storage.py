"""SQLite-backed measurement storage for homewizard-cli."""

import contextlib
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

from .models import Measurement
from .util import _dumps_json, _loads_json


def _sql_type(annotation: type | None) -> str:
    if annotation is None:
        return "TEXT"
    origin = get_origin(annotation)
    if origin is Union or origin is UnionType:
        args = get_args(annotation)
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _sql_type(non_none[0])
        return "TEXT"
    if annotation is int:
        return "INTEGER"
    if annotation is float:
        return "REAL"
    return "TEXT"


def _measurement_columns() -> dict[str, str]:
    """Map Measurement field names to SQL column types."""
    cols: dict[str, str] = {
        "stored_at": "TEXT NOT NULL",
        "device_serial": "TEXT NOT NULL",
        "schema_version": "INTEGER DEFAULT 1",
    }
    for name, field in Measurement.model_fields.items():
        if name == "external":
            cols[name] = "TEXT"
            continue
        cols[name] = _sql_type(field.annotation)
    return cols


_AGG_INTERVALS = {
    "hourly": "%Y-%m-%dT%H",
    "daily": "%Y-%m-%d",
    "weekly": "%Y-%W",
    "monthly": "%Y-%m",
}


def _parse_datetime(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class MeasurementStore:
    """SQLite-backed store for energy measurements."""

    def __init__(self, db_path: str | None) -> None:
        self.db_path = db_path
        if db_path is None:
            self._conn = None
            return
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()
        self._columns: list[str] | None = None

    def _init_schema(self) -> None:
        if self._conn is None:
            return
        cols = _measurement_columns()
        col_defs = ", ".join(f"{name} {typ}" for name, typ in cols.items())
        self._conn.execute(f"CREATE TABLE IF NOT EXISTS readings ({col_defs})")
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_serial_stored "
            "ON readings(device_serial, stored_at)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_stored ON readings(stored_at)"
        )
        self._conn.commit()

    def _get_columns(self) -> list[str]:
        if self._conn is None:
            return []
        if self._columns is not None:
            return self._columns
        cursor = self._conn.execute("PRAGMA table_info(readings)")
        self._columns = [row[1] for row in cursor.fetchall()]
        return self._columns

    def append(self, data: dict, device_serial: str) -> None:
        if self._conn is None:
            return
        now = datetime.now().isoformat()
        cols = self._get_columns()
        values: dict[str, Any] = {
            "stored_at": now,
            "device_serial": device_serial,
            "schema_version": 1,
        }
        for col in cols:
            if col in ("stored_at", "device_serial", "schema_version"):
                continue
            v = data.get(col)
            if col == "external" and isinstance(v, list):
                external_list = []
                for item in v:
                    if hasattr(item, "model_dump"):
                        external_list.append(item.model_dump(mode="json"))
                    elif isinstance(item, dict):
                        external_list.append(item)
                    else:
                        external_list.append(str(item))
                v = _dumps_json(external_list)
            values[col] = v
        col_list = ", ".join(cols)
        placeholders = ", ".join(f":{c}" for c in cols)
        self._conn.execute(
            f"INSERT INTO readings ({col_list}) VALUES ({placeholders})",  # nosec: col_list from PRAGMA
            values,
        )
        self._conn.commit()

    def query(
        self,
        *,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        fields: list[str] | None = None,
        agg: str | None = None,
        device_serial: str | None = None,
        top_n: int | None = None,
    ) -> list[dict]:
        if self._conn is None:
            return []
        if fields:
            select_cols = [f for f in fields if f in self._get_columns()]
        else:
            select_cols = [c for c in self._get_columns() if c != "schema_version"]

        where_clauses: list[str] = []
        params: dict[str, Any] = {}
        start_s = _parse_datetime(start)
        end_s = _parse_datetime(end)
        if start_s:
            where_clauses.append("stored_at >= :start")
            params["start"] = start_s
        if end_s:
            where_clauses.append("stored_at <= :end")
            params["end"] = end_s
        if device_serial:
            where_clauses.append("device_serial = :device_serial")
            params["device_serial"] = device_serial

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        order_clause = ""
        limit_clause = ""
        if top_n is not None:
            field_for_rank = (
                select_cols[-1]
                if len(select_cols) > 1 and fields
                else (fields[0] if fields else "stored_at")
            )
            known_cols = self._get_columns()
            if field_for_rank not in known_cols:
                field_for_rank = "stored_at"
            if field_for_rank in ("stored_at", "device_serial"):
                field_for_rank = select_cols[0] if select_cols else "stored_at"
            order_clause = (
                f"ORDER BY {field_for_rank} DESC"
                if top_n > 0
                else f"ORDER BY {field_for_rank} ASC"
            )
            limit_clause = f"LIMIT {abs(top_n)}"

        if agg and agg in _AGG_INTERVALS:
            period_fmt = _AGG_INTERVALS[agg]
            numeric_cols = []
            for c in select_cols:
                if c in ("stored_at", "device_serial", "schema_version"):
                    continue
                numeric_cols.append(c)
            if not numeric_cols:
                numeric_cols = [
                    c
                    for c in self._get_columns()
                    if c
                    not in (
                        "stored_at",
                        "device_serial",
                        "schema_version",
                        "wifi_ssid",
                        "meter_model",
                        "unique_id",
                        "gas_unique_id",
                        "text_message",
                        "external",
                    )
                ]

            non_agg_cols = []
            for c in select_cols:
                if c in numeric_cols:
                    non_agg_cols.append(c)

            agg_exprs: list[str] = []
            for c in non_agg_cols:
                agg_exprs.append(f"AVG({c}) AS {c}_avg")
                agg_exprs.append(f"MIN({c}) AS {c}_min")
                agg_exprs.append(f"MAX({c}) AS {c}_max")
                agg_exprs.append(f"SUM({c}) AS {c}_sum")

            sql = (
                f"SELECT strftime('{period_fmt}', stored_at) AS period, "  # nosec: cols from model fields
                f"{', '.join(agg_exprs)} "
                f"FROM readings WHERE {where_sql} "
                f"GROUP BY period ORDER BY period"
            )
        else:
            select_sql = ", ".join(select_cols) if select_cols else "*"
            sql = (
                f"SELECT {select_sql} FROM readings "  # nosec: cols from model schema
                f"WHERE {where_sql} {order_clause} {limit_clause}"
            )

        cursor = self._conn.execute(sql, params)
        rows = cursor.fetchall()
        result: list[dict] = []
        for row in rows:
            d = dict(row)
            if "external" in d and isinstance(d["external"], str):
                with contextlib.suppress(Exception):
                    d["external"] = _loads_json(d["external"])
            result.append(d)
        return result

    def info(self) -> dict:
        if self._conn is None:
            return {"row_count": 0, "file_size_bytes": 0}
        cursor = self._conn.execute("SELECT COUNT(*) AS cnt FROM readings")
        row_count = cursor.fetchone()["cnt"]
        cursor = self._conn.execute(
            "SELECT MIN(stored_at) AS date_start, MAX(stored_at) AS date_end "
            "FROM readings"
        )
        row = cursor.fetchone()
        date_start = row["date_start"] if row else None
        date_end = row["date_end"] if row else None
        devices = self.list_devices()
        # Estimate completeness (assumes 60s interval)
        completeness_pct = 0.0
        if date_start and date_end and row_count > 0:
            try:
                start_dt = datetime.fromisoformat(date_start)
                end_dt = datetime.fromisoformat(date_end)
                expected_seconds = (end_dt - start_dt).total_seconds()
                expected = max(1, expected_seconds / 60)
                completeness_pct = min(100.0, round(row_count / expected * 100, 1))
            except (ValueError, TypeError):
                pass
        file_size = 0
        if self.db_path:
            with contextlib.suppress(OSError):
                file_size = Path(self.db_path).stat().st_size
        return {
            "row_count": row_count,
            "date_start": date_start,
            "date_end": date_end,
            "devices": devices,
            "completeness_pct": completeness_pct,
            "file_size_bytes": file_size,
        }

    def list_devices(self) -> list[str]:
        if self._conn is None:
            return []
        cursor = self._conn.execute(
            "SELECT DISTINCT device_serial FROM readings ORDER BY device_serial"
        )
        return [row[0] for row in cursor.fetchall()]

    def since_last(self) -> datetime | None:
        if self._conn is None:
            return None
        cursor = self._conn.execute("SELECT MAX(stored_at) AS ts FROM readings")
        row = cursor.fetchone()
        ts = row["ts"] if row else None
        if ts:
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                pass
        return None

    def vacuum(self) -> None:
        if self._conn is None:
            return
        self._conn.execute("VACUUM")

    def retain(self, days: int) -> int:
        if self._conn is None:
            return 0
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM readings WHERE stored_at < :cutoff",
            {"cutoff": cutoff},
        )
        self._conn.commit()
        return cursor.rowcount

    def migrate(self) -> None:
        if self._conn is None:
            return
        existing = set(self._get_columns())
        for name, sql_type in _measurement_columns().items():
            if name not in existing:
                self._conn.execute(f"ALTER TABLE readings ADD COLUMN {name} {sql_type}")
        self._columns = None
        self._conn.commit()

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


async def _setup_store(
    db: str | None,
    api_version: str,
    client: Any,
) -> tuple[MeasurementStore | None, str | None]:
    """Open SQLite store and fetch device serial.

    Returns (store, serial). Both are None if db is None.
    The *client* must be inside an ``async with`` block.
    """
    if not db:
        return None, None
    store = MeasurementStore(db)
    store.migrate()
    serial = await _fetch_device_serial(client, api_version)
    return store, serial


async def _fetch_device_serial(client: Any, api_version: str) -> str | None:
    try:
        if api_version == "v2":
            from .models.v2 import DeviceInfoV2

            info = await client.get_json_v2("/api", DeviceInfoV2)
            return info.serial or None
        else:
            text = await client.get("/api/")
            raw = _loads_json(text)
            return raw.get("serial") or None
    except Exception:
        return None

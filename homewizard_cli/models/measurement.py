"""Unified Measurement model that deserializes from both v1 and v2 JSON."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from homewizard_cli.util import _iso_to_compact_timestamp

_V2_MAPPING = {
    "protocol_version": "smr_version",
    "energy_import_kwh": "total_power_import_kwh",
    "energy_import_t1_kwh": "total_power_import_t1_kwh",
    "energy_import_t2_kwh": "total_power_import_t2_kwh",
    "energy_import_t3_kwh": "total_power_import_t3_kwh",
    "energy_import_t4_kwh": "total_power_import_t4_kwh",
    "energy_export_kwh": "total_power_export_kwh",
    "energy_export_t1_kwh": "total_power_export_t1_kwh",
    "energy_export_t2_kwh": "total_power_export_t2_kwh",
    "energy_export_t3_kwh": "total_power_export_t3_kwh",
    "energy_export_t4_kwh": "total_power_export_t4_kwh",
    "power_w": "active_power_w",
    "power_l1_w": "active_power_l1_w",
    "power_l2_w": "active_power_l2_w",
    "power_l3_w": "active_power_l3_w",
    "voltage_l1_v": "active_voltage_l1_v",
    "voltage_l2_v": "active_voltage_l2_v",
    "voltage_l3_v": "active_voltage_l3_v",
    "voltage_v": "active_voltage_l1_v",
    "current_a": "active_current_a",
    "current_l1_a": "active_current_l1_a",
    "current_l2_a": "active_current_l2_a",
    "current_l3_a": "active_current_l3_a",
    "frequency_hz": "active_frequency_hz",
    "average_power_15m_w": "active_power_average_w",
    "monthly_power_peak_w": "monthly_power_peak_w",
    "tariff": "active_tariff",
}

_V2_DETECT_KEYS = frozenset({"power_w", "energy_import_kwh", "protocol_version", "tariff"})


class ExternalDevice(BaseModel):
    """External sub-meter (gas, water, heat)."""

    unique_id: str
    type: str
    timestamp: int
    value: float
    unit: str


class Measurement(BaseModel):
    """Full measurement data — deserializes from v1 or v2 API responses.

    Uses v1 canonical field names so all format writers work without changes.
    A ``model_validator(mode="before")`` maps v2 field names automatically.
    """

    # Connection & Metadata
    wifi_ssid: str = ""
    wifi_strength: int = 0
    smr_version: int = 0
    meter_model: str = ""
    unique_id: str = ""
    active_tariff: int = 0

    # Electricity - Totals
    total_power_import_kwh: float = 0.0
    total_power_import_t1_kwh: float = 0.0
    total_power_import_t2_kwh: float = 0.0
    total_power_import_t3_kwh: float | None = None
    total_power_import_t4_kwh: float | None = None
    total_power_export_kwh: float = 0.0
    total_power_export_t1_kwh: float = 0.0
    total_power_export_t2_kwh: float = 0.0
    total_power_export_t3_kwh: float | None = None
    total_power_export_t4_kwh: float | None = None

    # Electricity - Real-time
    active_power_w: float = 0.0
    active_power_l1_w: float | None = None
    active_power_l2_w: float | None = None
    active_power_l3_w: float | None = None
    active_voltage_l1_v: float | None = None
    active_voltage_l2_v: float | None = None
    active_voltage_l3_v: float | None = None
    active_current_a: float | None = None
    active_current_l1_a: float | None = None
    active_current_l2_a: float | None = None
    active_current_l3_a: float | None = None
    active_frequency_hz: float | None = None
    active_power_average_w: float | None = None
    monthly_power_peak_w: float | None = None
    monthly_power_peak_timestamp: int | None = None

    # Power Quality
    voltage_sag_l1_count: int | None = None
    voltage_sag_l2_count: int | None = None
    voltage_sag_l3_count: int | None = None
    voltage_swell_l1_count: int | None = None
    voltage_swell_l2_count: int | None = None
    voltage_swell_l3_count: int | None = None
    any_power_fail_count: int | None = None
    long_power_fail_count: int | None = None

    # Gas Meter
    total_gas_m3: float | None = None
    gas_timestamp: int | None = None
    gas_unique_id: str | None = None

    # Text Message
    text_message: str | None = None

    # External Devices
    external: list[ExternalDevice] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _map_v2_fields(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if not _V2_DETECT_KEYS.intersection(data):
            return data
        for v2_name, v1_name in _V2_MAPPING.items():
            if v2_name in data and v1_name not in data:
                v = data.pop(v2_name)
                if v is not None:
                    data[v1_name] = v
        for ts_key in ("gas_timestamp", "monthly_power_peak_timestamp"):
            if ts_key in data and isinstance(data[ts_key], str):
                data[ts_key] = _iso_to_compact_timestamp(data[ts_key])
        if "external" in data and isinstance(data["external"], list):
            for item in data["external"]:
                if isinstance(item, dict) and isinstance(item.get("timestamp"), str):
                    item["timestamp"] = (
                        _iso_to_compact_timestamp(item["timestamp"]) or 0
                    )
        return data

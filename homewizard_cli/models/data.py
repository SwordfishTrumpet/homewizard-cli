"""Pydantic models for /api/v1/data response."""

from pydantic import BaseModel, Field


class ExternalDevice(BaseModel):
    """External sub-meter (gas, water, heat)."""

    unique_id: str
    type: str
    timestamp: int
    value: float
    unit: str


class DataResponse(BaseModel):
    """Full data response from /api/v1/data."""

    # Connection & Metadata
    wifi_ssid: str
    wifi_strength: int
    smr_version: int
    meter_model: str
    unique_id: str
    active_tariff: int

    # Electricity - Totals
    total_power_import_kwh: float
    total_power_import_t1_kwh: float
    total_power_import_t2_kwh: float
    total_power_import_t3_kwh: float | None = None
    total_power_import_t4_kwh: float | None = None
    total_power_export_kwh: float
    total_power_export_t1_kwh: float
    total_power_export_t2_kwh: float
    total_power_export_t3_kwh: float | None = None
    total_power_export_t4_kwh: float | None = None

    # Electricity - Real-time
    active_power_w: float
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

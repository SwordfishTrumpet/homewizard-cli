"""Pydantic models for HomeWizard API v2 responses."""

from pydantic import BaseModel, Field


class V2ExternalDevice(BaseModel):
    """External sub-meter in v2 format."""

    unique_id: str
    type: str
    timestamp: str
    value: float
    unit: str


class MeasurementV2(BaseModel):
    """Measurement from /api/measurement (v2 field names)."""

    protocol_version: int | None = None
    meter_model: str | None = None
    unique_id: str | None = None
    tariff: int | None = None
    timestamp: str | None = None

    energy_import_kwh: float | None = None
    energy_import_t1_kwh: float | None = None
    energy_import_t2_kwh: float | None = None
    energy_import_t3_kwh: float | None = None
    energy_import_t4_kwh: float | None = None
    energy_export_kwh: float | None = None
    energy_export_t1_kwh: float | None = None
    energy_export_t2_kwh: float | None = None
    energy_export_t3_kwh: float | None = None
    energy_export_t4_kwh: float | None = None

    power_w: float | None = None
    power_l1_w: float | None = None
    power_l2_w: float | None = None
    power_l3_w: float | None = None

    voltage_v: float | None = None
    voltage_l1_v: float | None = None
    voltage_l2_v: float | None = None
    voltage_l3_v: float | None = None

    current_a: float | None = None
    current_l1_a: float | None = None
    current_l2_a: float | None = None
    current_l3_a: float | None = None

    frequency_hz: float | None = None

    voltage_sag_l1_count: int | None = None
    voltage_sag_l2_count: int | None = None
    voltage_sag_l3_count: int | None = None
    voltage_swell_l1_count: int | None = None
    voltage_swell_l2_count: int | None = None
    voltage_swell_l3_count: int | None = None
    any_power_fail_count: int | None = None
    long_power_fail_count: int | None = None

    average_power_15m_w: float | None = None
    monthly_power_peak_w: float | None = None
    monthly_power_peak_timestamp: str | None = None

    external: list[V2ExternalDevice] = Field(default_factory=list)

    total_gas_m3: float | None = None
    gas_timestamp: str | None = None
    gas_unique_id: str | None = None


class SystemV2(BaseModel):
    """System settings from /api/system (v2)."""

    cloud_enabled: bool | None = None
    wifi_ssid: str | None = None
    wifi_rssi_db: float | None = None
    uptime_s: int | None = None
    status_led_brightness_pct: int | None = None
    api_v1_enabled: bool | None = None


class DeviceInfoV2(BaseModel):
    """Device info from /api (v2 format)."""

    product_name: str | None = None
    product_type: str | None = None
    serial: str | None = None
    firmware_version: str | None = None
    api_version: str | None = None


class UserInfo(BaseModel):
    """User info from /api/user."""

    name: str | None = None
    token: str | None = None


class BatteryState(BaseModel):
    """Battery state from /api/batteries."""

    mode: str | None = None
    permissions: list[str] = Field(default_factory=list)
    charge_to_full: bool | None = None
    battery_count: int | None = None
    power_w: float | None = None
    target_power_w: float | None = None
    max_consumption_w: float | None = None
    max_production_w: float | None = None


class TelegramV2(BaseModel):
    """Raw DSMR telegram response (v2)."""

    telegram: str


class V2ApiInfo(BaseModel):
    """Response from GET /api (v2 device info)."""

    product_name: str
    product_type: str
    serial: str
    firmware_version: str
    api_version: str


class V2Error(BaseModel):
    """API v2 error response."""

    error: str

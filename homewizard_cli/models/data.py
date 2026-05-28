"""Pydantic models for /api/v1/data response."""

from typing import List, Optional
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
    total_power_export_kwh: float
    total_power_export_t1_kwh: float
    total_power_export_t2_kwh: float

    # Electricity - Real-time
    active_power_w: float
    active_power_l1_w: Optional[float] = None
    active_voltage_l1_v: Optional[float] = None
    active_current_a: Optional[float] = None
    active_current_l1_a: Optional[float] = None

    # Power Quality
    voltage_sag_l1_count: Optional[int] = None
    voltage_swell_l1_count: Optional[int] = None
    any_power_fail_count: Optional[int] = None
    long_power_fail_count: Optional[int] = None

    # Gas Meter
    total_gas_m3: Optional[float] = None
    gas_timestamp: Optional[int] = None
    gas_unique_id: Optional[str] = None

    # External Devices
    external: List[ExternalDevice] = Field(default_factory=list)
